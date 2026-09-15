# BLOQ 1 — Project Memory

Running memory for the BLOQ 1 product concept. Append decisions here as they're made.

## What it is

A standalone, hands-free voice device that lets you talk to a Claude Code agent
and gives it full, unrestricted control of the device. Sold as a crowdfunded
hardware product. Beyond the voice-agent core, one box also runs: a personal
cloud/NAS, Pi-hole-style network filtering, and a Minecraft server.

## Hardware

- Board: Orange Pi 4 Pro — Allwinner A733 SoC, 12GB LPDDR5, 3 TOPS NPU.
- CPU: 2x Cortex-A76 + 6x Cortex-A55 @ 2.0GHz, Imagination BXM-4-64 GPU.
- RISC-V E902 co-processor @ 200MHz (single-core, XuanTie RV32E[M]C, MCU-class).
  - REALITY CHECK: the E902 exists for low-power always-on housekeeping (lets the
    main cluster sleep), NOT as an AI-safety enclave. That's our repurposing.
  - Good enough for: heartbeat monitor + hardware kill relay, physically-gated
    mic + privacy LED, simple permission/event logging.
  - NOT good enough for: on-chip ASR/wake-word, running an honeypot/tarpit.
  - On-chip SRAM (192KB + 512KB shared) is chip-wide and volatile. A true
    tamper-evident "black box" needs a dedicated non-volatile chip wired ONLY to
    E902 pins — this is a custom-PCB design decision, NOT true of the stock board.
    Verify against the A733 datasheet before any marketing claim of isolation.

## Product philosophy (KEY DECISION)

- Ship the box MOSTLY EMPTY: OS on flash + the agent + safety basics. Do NOT
  pre-install a pile of programs.
- The magic IS the empty box: "it came with nothing and I spoke my setup into
  existence." Pre-installing defeats the from-the-ground-up agent premise AND
  forces us to explain technical programs to lazy/non-technical buyers.
- The tech stays invisible: buyer says "block ads on my whole house," never sees
  the word "Pi-hole."

## Hosted guides / wiki system (KEY DECISION — save-to-memory request)

- Author canonical, tested build recipes as hosted online guides (a wiki/site),
  written using our own Claude Code instance.
- Every customer's agent is POINTED AT these guides so builds come out
  reproducible instead of improvised — same hardened config every time.
- Customer can literally tell their agent "follow the NAS guide" and it executes.
- Benefits: reproducible builds, one-place updates that all future builds
  inherit, and the guide doubles as an executable support manual.

## NAS strategy

- Competitors (Synology / QNAP / Ugreen) sell a ~€150 computer for €400–600
  diskless. Hardware is cheap; we can match/beat it easily.
- What their price actually buys: polished exclusive OS (Synology DSM / QNAP QTS
  / Ugreen UGOS), no-config remote access via their relay servers, good mobile
  apps, and data-integrity engineering. Software + reliability is the moat, not
  hardware.
- Our stack (open-source, hardware-agnostic — this is why we can undercut):
  - Immich — photos (Google-Photos-class, phone auto-backup, faces). Now genuinely good.
  - Nextcloud / Seafile — file sync.
  - TrueNAS / ZFS or btrfs — storage + integrity layer.
  - Tailscale — remote access without port forwarding or running our own relays.
- The wedge: normal people won't wire these four together and maintain them —
  that misery is exactly what the agent removes.
- Honest ceiling: nobody but Apple can put photos INSIDE the iOS gallery. Best
  anyone (incl. Google Photos) does is a background auto-upload companion app.
  Don't promise a seam we can't deliver.

### NAS protection recipe (KEY — make this a standard hardened guide)

The hard 80% is running unattended for years and surviving a dead disk WITHOUT
losing data. One data-loss incident kills reviews. Standard recipe must include:

- Filesystem with integrity: ZFS or btrfs.
- Snapshots (point-in-time, for "undo"/ransomware recovery).
- Scrubbing (periodic scan to catch silent bit-rot / bit degradation).
- RAID / redundancy that actually rebuilds when a disk dies.
- Disk-failure alerting BEFORE a drive dies (SMART monitoring).
- Tested restores (a backup you haven't restored isn't a backup).

## Networking notes

- Pi-hole = DNS sinkhole, NOT a traffic router. It only answers name lookups;
  actual traffic goes device→server directly. Blocks by refusing/faking the DNS
  answer for blocklisted domains. Cheap + fast because it only handles tiny name
  queries.
- Per-device + time-based rules ("block TikTok on kids' iPads after 9pm") are
  LOCAL config on the box — no router login needed — because the box is the DNS
  answerer.
- Loophole: devices using private DNS / DoH bypass Pi-hole. Closing it requires
  the box to be the GATEWAY and firewall off outbound DNS. Recurring reason to
  favor the "box is the gateway" architecture.
- Port forwarding (needed to expose Minecraft etc.) paths, best→worst:
  1. UPnP / NAT-PMP (`upnpc`) — clean standard protocol, works when UPnP is on.
  2. Box is the gateway — just nftables/iptables, rock solid.
  3. Router with SSH/API (OpenWrt `uci`, Ubiquiti, pfSense) — clean for power users.
  4. Scraping the router admin web page — works but brittle, per-brand, breaks on
     firmware updates. Last-resort fallback, NOT the headline.
- Build the feature on UPnP + box-as-gateway; treat admin-page scraping as fallback.
- Opening ports = internet exposure → this is where the voice kill-switch earns
  its place (same voice that opens a port must slam it shut).

## Trust / safety features (for "AI agent with root" premise)

- Hardware kill relay via E902: heartbeat from agent; miss it or trip a rule →
  E902 cuts network PHY power. Not a software setting the agent can change.
- Physically-gated mic + hardware privacy LED wired to E902 (mic power can't
  reach the agent side until E902 opens the gate; LED is a hardware fact).
- Black box: hash-chained append-only log SCOPED TO permission/capability events
  (not every action — less noise). Readable WITHOUT booting the possibly-infected
  main OS (that's the whole point of it being on a separate chip). Circular buffer
  + periodic hash anchoring to companion app so old detail rolls off but
  tamper-evidence survives.
- Real physical power/kill button (keep it simple — a button that just works).
- Lockdown / honeypot-tarpit: belongs on the MAIN cluster in an isolated VLAN,
  NOT the E902. Established technique (tarpitting/deception), so a nice-to-have,
  not the novel headline.

## Demo-sellable feature shortlist (one-gut-punch-each for crowdfunding video)

1. Empty-box cold start — unbox, plug in, say "set up a Minecraft server," watch
   it build from nothing in ~90s. Sell the emptiness as the headline.
2. Time travel — "put it back how it was" / "go back to this morning." Snapshots,
   never say the word. Kills "what if I break it."
3. Personal software on demand — "make me a shared grocery list app," family gets
   a link in seconds. Creation from nothing.
4. Natural-language network house rules — spoken firewall/DNS, replaces hated
   router admin pages.
5. Self-healing while you sleep + morning report — "your server crashed at 3am, I
   fixed it, nobody noticed." Turns gadget into something you can't give up.
6. (Back-pocket) "Become a copy of that one" — agent re-derives full setup on a
   fresh box. Kills "what if it dies."

## Open risks / honest limits

- E902 storage-isolation claim is a design intention, not confirmed on stock
  board. Verify vs datasheet before marketing.
- Reliably reconfiguring a stranger's unknown router is hard (scraping path).
  Works great on your own known network (demo), unpredictable in the wild.
- Data integrity is the real product, and it's unforgiving. Don't let the fun
  agent features distract from "doesn't eat your data."
