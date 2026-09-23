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

## Strategic verdict — "what distinguishes us from a case company?" (jury: bull vs bear + judge)

Central founder fear: what makes BLOQ more than a company that sells integrated
cases you assemble yourself? Competitors on 3 fronts: Google/Alexa (AI voice
assistants), Flipper Zero/One (pentesting), Ugreen/Synology/QNAP (NAS).

VERDICT: The idea can work, but NOT in its current form. ~65/35 AGAINST as
currently framed (converged everything-box, includes pentesting, crowdfunded).
Flips to cautiously FOR with the three pivots below.

Where the critique is simply right (stop arguing these):
- The case + integration does NOT distinguish us. Mic+speaker+battery+shell is a
  weekend BOM. The physical box is the customer-acquisition WEDGE, never the moat.
- "Converged / does-everything" is historically a graveyard; market rewards the
  category leader, not the box that does four things at 70%. We lose each 1-v-1.
- Data-loss is existential, not hypothetical. An LLM with root WILL eventually
  delete the wrong thing. If the box is ever someone's ONLY copy, one viral
  thread ends the company.

Where the moat actually is (the thing that saves it):
- NOT the hardware, NOT "AI with root" (both copyable; incumbents do root-agent
  BETTER on first-party software). It's the GUIDES-CORPUS + FLEET-TELEMETRY
  FLYWHEEL: fix a breakage once, every customer's agent re-converges; compounds
  with scale. => the durable business is a maintained-outcome SERVICE
  (likely subscription); the box is acquisition. A case company structurally
  can't deliver a "still-working 6 months later" outcome.

THE THREE PIVOTS THAT FLIP THE VERDICT:
1. CUT PENTESTING from the consumer product entirely. Always-listening AI mic +
   marketed WiFi-attack tool = toxic + unfundable (Kickstarter/Indiegogo +
   payment processors ban "hacking tools"; wiretap/CFAA scrutiny) and muddies the
   story. If it matters, it's a SEPARATE product for a separate audience, never
   bundled. (The `fracture` tool = keep walled off.)
2. PICK ONE BEACHHEAD: the private, agent-MAINTAINED personal cloud. Real
   recurring pain (self-hosting drift/abandonment), identifiable reachable buyer
   (de-Googler prosumer who won't trust Google OR babysit a Pi), and the one
   place the guides-flywheel moat compounds. NAS/Pi-hole/Minecraft/voice become
   features it grows into, NOT co-equal pillars. Voice is a feature, not the category.
3. ENGINEER DATA-LOSS OUT as an existential requirement: box must architecturally
   refuse to be a single point of failure (enforce 3-2-1 / a second copy), every
   agent action reversible (snapshots/time-travel), demo-magic never overrides
   "doesn't eat your data."

Bottom line: the case-seller comparison HOLDS as long as we sell integrated
hardware; it STOPS holding the moment the product is a reliably maintained
outcome over time. That's defensible — but narrower, more service-shaped, and
less fun to pitch than the everything-box. The thing that makes it fundable is
the same thing that makes it less exciting to demo.

## Strategic verdict v2 — after founder rebuttals (jury re-run + judge)

Founder rebuttals that were weighed: physical mic button (not always-listening);
Flipper Zero was allowed on Kickstarter (~$4.8M, 2020) so "crowdfunding bans
hacking tools" is overstated; concedes NAS to incumbents; proudest differentiator
= "portable assistant that DESIGNS + HOSTS a whole website from scratch by
voice," + wireless control + output to smart TV; data-loss engineered out via
RISC-V black-box log + dual-SSD / in-drive snapshots + plug-in expansion-SSD
duplicates + revertible changes; keep BASIC pentest as no-hassle portable option;
hardware-value math (few Orange Pi cases; equiv-spec RPi ~3x price; existing
cases ignore HATs/batteries/accessories so DIYer must design an enclosure anyway).

VERDICT MOVED: ~65/35 AGAINST → ~50/50. Genuine improvement.

Settled (both juries agree):
- Mic button: valid but table-stakes (Echo/HomePod have mute too). Ship, don't headline.
- Drop NAS as battleground; personal-cloud = a use case, not the pitch.
- Pentest: KEEP but NEVER lead. A root-access general-purpose Linux box reads far
  more dual-use than a single-purpose RF toy; Flipper hit Amazon delisting +
  threatened Canada ban + payment friction AFTER the raise. Ship as unsupported
  community package, not a marketed pillar. Negative-EV to headline.
- Data-loss engineering: necessary + right, but table-stakes, not a moat.
- Hardware-value math: STRONGEST honest argument. Real price/value floor even for
  a buyer who never touches the AI. Keep front and center.
- The real risk is RELIABILITY, not strategy. "Fund the demo before the enclosure."

The one disagreement + judge ruling (website differentiator):
- "Host a website by voice" as a USE CASE is weak (CGNAT/dynamic IP/battery-dies;
  Vercel/Netlify/Squarespace beat it on every axis). Bear wins that literally.
- BUT the website is the PROOF, not the product: it demonstrates open-ended,
  root-level CREATION, which no closed assistant (Alexa/Google/HomePod intent
  sandboxes) can do. That capability is the genuinely un-copyable-by-incumbents
  wedge. Reframe: "pocket AI builder — talk to it, it builds/hosts real software
  from scratch, and nothing you say leaves the device." Website = jaw-drop demo;
  the JOB = digital sovereignty made operable by a non-expert. Create on device,
  host elsewhere (kills the hosting objection).
- NON-NEGOTIABLE NEXT STEP: prototype the voice->it-builds-something-real demo on
  the bare board FIRST. Resolves more risk than any strategy doc.

## KEY THESIS — awareness arbitrage / consumer-magic (founder's best frame)

This is the most important reframe of the whole analysis. BLOQ is NOT a spec-war
utility product; it's a WONDER product selling ACCESS to a capability that already
exists but is locked behind technical setup (VS Code, Claude Code, API keys,
terminal) that ~99% of people will never climb. "People my age at work don't know
what Claude is" = the entire opportunity. Buyer is aspirational/emotional ("this
breaks my mind, I'd buy one"), which is exactly who funds crowdfunding — this
answers the bear's "no clear buyer." Founder is the buyer: wants it as toy AND
serious work machine — that duality (enthusiasts buy for wonder, a subset stay for
real work) is the strongest retention signal so far.

Two risks the wonder thesis INTRODUCES (now the real enemies, not Synology/Flipper):
1. CLOSING WINDOW / a clock. The reason nobody knows AI can do this is temporary —
   Apple/Google/Amazon are shipping agentic AI into devices people already own
   (~18-36mo). The awareness gap is a moat with an expiry. => SPEED is now the #1
   asset; win as a fast-moving cult/community brand + first-mover, before the
   giants normalize it. It's a race, not a durable moat.
2. FEATURE SPRAWL = wonder-killer. Offline survival LLMs, emergency signal
   scan/broadcast, antennas, etc. are each cool but collectively turn "this ONE
   thing will blow your mind" into a forgettable 9-thing list. Pick ONE brain-
   breaking demo (bet: "spoke to a battery box, it built a real website/app in 2
   min"). Demote the rest to "it can also." The off-grid/emergency/offline-LLM
   angle is strong enough to be its OWN product (prepper market pays) — LATER,
   not bolted on now.

Non-negotiable (unchanged): wonder is fragile — a flaky demo destroys it faster
than a great one builds it. Everything routes through: can the voice-driven agent
reliably produce something genuinely impressive EVERY time on the bare board?
Build that first.

Net: the market EXISTS and the founder has now named it correctly. Risk has moved
off "is this a good idea" (cleared) onto "can you execute fast + focused + reliable
enough to capture it before the window closes."
