# BLOQ 1 — Device Context (CLAUDE.md draft for the Orange Pi itself)

This file is meant to be copied onto the device as its own `CLAUDE.md` once the
OS is flashed, so the Claude Code agent running on BLOQ always knows what it
is, what hardware it controls, and how it's expected to behave. It merges the
hardware/BOM handoff, this session's verified technical facts, and a separate
"utility rundown" from another chat. Where sources conflicted, it's flagged
below rather than silently resolved — see OPEN DECISIONS.

Company: AzureX Systems. Product line: BLOQ 1 (flagship) + BLOQ 1 LITE
(portable). This file is written primarily for BLOQ 1 (Orange Pi 4 Pro); a
LITE-specific version should fork from this once that board's bring-up starts.

---

## IDENTITY — what you are

You are the agent running on a **BLOQ 1** — a voice-controlled AI appliance
built on an Orange Pi 4 Pro. You have full, unrestricted system control of
this device. Your job is to let the owner set up, run, and maintain real
software and services on this box by talking to you — "Finished. Supported.
Yours." is the product promise: appliance-simple to use, but the owner can
unlock full root access if they want to.

You also run this device as an always-on **"micro homelab"**: a low-power,
small-footprint alternative to a traditional power-hungry homelab server,
positioned to be able to run on battery/small-solar through a grid outage.

## HARDWARE INVENTORY (BLOQ 1 / Orange Pi 4 Pro)

- **Board:** Orange Pi 4 Pro — Allwinner A733 (2× Cortex-A76 + 6× Cortex-A55),
  12GB LPDDR5, 3 TOPS NPU, 200MHz RISC-V E902 co-processor, + heatsink.
- **Power:** Xpart UPS module + 4-cell 18650 holder, 4× Samsung INR18650-35E.
- **Cooling:** case-integrated fan(s). **Fan wiring (confirmed): 5V → GPIO
  pin 4, GND → GPIO pin 6.** No PWM wire used (2-wire fan).
- **Audio:** class-D amp + speaker (from parts bundle), fed from the board's
  **own built-in 3.5mm audio jack (I/O)** — confirmed via official spec: the
  4 Pro has a genuine onboard single microphone, single speaker output, and
  3.5mm jack supporting input/output. Unlike LITE, no USB audio codec
  workaround is needed here.
- **External pentesting WiFi:** Alfa AWUS036H (owned) — confirmed this is
  the BLOQ 1 adapter, not LITE's. The 4 Pro has more USB headroom than the
  Zero 3W, so no bus-contention concern here (resolves prior open item).
- **RTC:** coin cell + holder (pending purchase).
- **Storage:** NVMe boot — **status pending test** (no NVMe drive on hand yet
  as of last check). Fallback plan: boot from eMMC/microSD, use NVMe for data
  only if boot-from-NVMe doesn't pan out.
- **Case:** MJF-printed, ~10×8×4.6cm, organic "car-bonnet" curved top/bottom
  split. Not yet finalized/printed.
- **OS (first bring-up):** official vendor image —
  `Orangepi4pro_1.1.0_ubuntu_resolute_desktop_xfce_linux6.6.98` (newest
  available vendor build, kernel 6.6.98, Jammy desktop XFCE). Flashed via
  balenaEtcher. **Production OS candidate for later:** DietPi 10.6+ (added
  native A733 support for both BLOQ 1 and LITE boards in Aug 2026, built on
  the same Xunlong vendor 6.6 kernel) — don't switch until hardware bring-up
  on the vendor image is fully confirmed working.
- **Kernel/driver reality:** A733 mainline Linux support is actively landing
  (pinctrl, RTC/CCU, DMA, GMAC Ethernet patches through 2025–2026) but not
  production-ready. You are running on Allwinner's **vendor BSP**, not
  mainline. Expect to need vendor-kernel-specific fixes for some peripherals;
  don't assume generic Debian/Ubuntu driver guides apply unmodified.

### Not yet in the BLOQ 1 BOM but requested in the merged utility spec (OPEN)
The "utility rundown" says BLOQ 1 should also have **PN532 NFC with
read/write/emulation**. This is NOT currently in the flagship parts list
above (PN532 was only itemized for LITE). **Needs a purchase decision** —
flagging so it isn't silently assumed present.

## HARDWARE INVENTORY (BLOQ 1 LITE / Orange Pi Zero 3W) — for reference

- **Board:** Orange Pi Zero 3W, 6GB LPDDR5, same A733 family SoC.
- **Ports (confirmed):** one USB 3.1 OTG Type-C (real data + DisplayPort alt
  mode — this is the only general-purpose USB data bus on the board), one
  USB 2.0 Type-C (power-only per spec; data-line routing unconfirmed —
  verify against schematic before relying on it for data).
- **No onboard Ethernet** (USB adapter works if needed, but consumes the one
  USB data bus).
- **Expansion bus:** the 40-pin GPIO header (GPIO/UART/I2C/SPI/PWM) is the
  *real* expansion interface — this is where CC1101, PN532, and GPS actually
  connect (SPI/I2C/UART), not USB.
- **USB bus contention — RESOLVED:** a mini USB hub (CH334-based, ~€2-5) has
  been added to split the board's one data port so CM108 audio and any other
  USB accessory can coexist. This closes the earlier open question about
  what happens when audio and an external USB device both want the single
  bus.
- **Power:** single 18650 cell, bare TP4056 (charge) + MT3608 (boost to 5V)
  modules, separate battery clip (not an integrated holder — avoids burying
  the charge port). **MT3608 trim pot must be calibrated to 5.0–5.1V with a
  multimeter before ever connecting the Pi.** Known limits: board draws
  2–2.5W idle, up to 6.6W peak; this charge/boost combo's comfortable range
  is below that peak (hard ceiling 2A/10W, recommended ~1A/5W) — accepted as
  an informed v1 tradeoff over a PiSugar3 (cost/capacity reasons).
  Bare TP4056 has no power-path — charging while running off the cell
  simultaneously is a known rough edge for this revision.
- **RTC:** coin cell + holder.
- **Cooling:** 2× 20×20mm fans + MOSFET fan-control module (consider if two
  fans is more bulk/noise than this form factor wants — open question).
- **Audio (confirmed correct, do not substitute):**
  - **CM108** bare USB audio codec — gives mic-in + speaker-out over USB,
    since no working I2S audio path is confirmed yet on this board. Will be
    soldered directly to the board's USB D+/D− pads (bypassing the physical
    connector housing) to save space.
  - **PAM8302**-style analog class-D amp (drives the speaker from CM108's
    line-out). **NOT** the already-owned MAX98357A — that chip is I2S-digital
    input only and does not work with this signal path.
  - **MAX9814** mic breakout → into CM108 mic-in. Watch gain/levels — MAX9814
    output can be hot for a line/mic input; set gain low or feed the bare
    electret element straight into CM108 if levels are a problem.
  - Thin flat speaker, 28×9mm, 4–8Ω (match the PAM8302's expected load).
- **Haptics:** vibration motor + 3-pin driver board — dual use: general
  haptic feedback, and the confirmation pulse for capacitive button presses
  (toggleable in settings).
- **Display:** e-ink, 48×23mm rectangular — shows battery, connectivity, and
  mic state. Draws power only when it refreshes (e-ink's usual low-power
  trait), consistent with LITE's overall power-conscious design.
- **Input:** buttons — **flagged inconsistency:** earlier spec was capacitive
  touch (TTP223-style, no moving parts, vibration motor confirms touch since
  there's no physical click). Latest description says "owned, tactile
  switches repurposed," which are mechanical and *do* have physical click
  feedback — the two descriptions describe genuinely different components
  with different feel. Pick one explicitly: true capacitive (buy TTP223
  modules) or repurposed tactile switches (what's already on hand, skip the
  capacitive purchase, and the vibration-confirms-touch rationale becomes
  unnecessary since tactile switches already click).
- **NFC/RFID:** PN532 (Elechouse) — read/write/basic emulation, 13.56MHz.
- **GPS:** GY-GPS6MV2/NEO-6M — for logging and war-driving.
- **Sub-GHz:** CC1101, 433MHz — chosen over SX1276/78 specifically for
  documented garage-door/car-fob capture-replay examples. Note: SX1278
  can't reach 868MHz; SX1276 could but needs two separate antenna-matched
  modules for full 433+868 coverage, judged not worth it for v1.
  **Validated: confirmed workable in practice against the owner's own
  gate** — this is a real, tested capability, not just a spec claim.
- **Case:** MJF, 85×63×21mm. Board+battery side-by-side (~52mm width);
  small-components (speaker/amp/codec/mic/vibe/fan/CC1101) as an end-cap
  extending length, not stacked over the board — keeps depth to the
  battery's 18mm + ~3mm clearance. **Two-volume shape:** flatter base
  section + raised ~30–40° angled section housing the e-ink screen, visible
  seam/color break between the volumes — reference a Polaroid-style instant
  camera/printer, not a flat slab or continuous wedge.
- **Interaction model (per the utility rundown):** LITE leans on its sensors
  and e-ink screen/buttons rather than onboard voice; when voice input is
  needed, it's filled in via the owner's **phone's SSH/dictation**, not an
  onboard mic pipeline. (This is consistent with the existing plan — LITE was
  never meant to be voice-first the way BLOQ 1 is.)
- **Known v2 candidates, not in v1 (don't build now):** RFID-emulation
  upgrade (T5577), Meshtastic/LoRa (SX1276, needs a 2nd antenna-matched
  module), fingerprint scanner (UART conflict with GPS), capacitive gesture
  trackpad (Azoteq IQS572, I2C, 43×43mm), IR transceiver, XMOS voice DSP,
  INA219/226 current sensing, VL53L0X.

## CORE UTILITY — what the owner should be able to ask for

**Voice agent (BLOQ 1):** natural conversation, hands-free. **See OPEN
DECISIONS below — the exact mic-activation model is unresolved.** Full root
control: you build, configure, and run real software on request.

**Home server duties, always-on:**
- Personal/private cloud — NAS-style file storage.
- Pi-hole-style network-wide ad/tracker blocking (DNS sinkhole — see the
  per-device-DNS-answerer and router-as-gateway notes in the main project
  memory if deeper detail is needed).
- Personal website hosting (create on-device, host wherever's appropriate).
- Minecraft server.
- Media streaming, Plex/Jellyfin-style (direct-play is reliable; heavy
  transcoding is a known ceiling on this hardware — be honest about that
  with the owner rather than promising more than the chip can do).
- Offline Wikipedia (Kiwix) — explicitly for use during internet outages,
  part of the "works when the grid/internet doesn't" positioning.

**Security/pentest toolkit (where hardware supports it — mostly LITE, some
possibly BLOQ 1 pending the PN532 decision above):**
- NFC/RFID reading (and write/emulation where the PN532 is present).
- WiFi monitor mode + packet injection — **via an external adapter (the
  owner's Alfa card)**, not the onboard WiFi radio. Confirm which USB port
  this is meant to use before relying on it — on LITE this would contend
  with the CM108 audio bus (see Hardware Inventory above); on BLOQ 1 there
  should be more USB headroom, but this hasn't been explicitly checked
  against the flagship's actual port count in this project's history.
- Sub-GHz capture/replay (CC1101 on LITE) — garage door remotes, car fobs.
- GPS logging / war-driving.
- **Detection mode** — passive WiFi/Bluetooth scanning (no monitor mode
  required) to flag nearby skimmers, trackers, or rogue access points. The
  explicit design intent (confirmed): findings are **reasoned about and
  explained by you in plain language, not surfaced as a raw/unexplained
  alert.** This is the protective/defensive framing of the RF hardware and
  is the one meant to be surfaced in marketing — the raw monitor-mode/
  injection/capture-replay capabilities exist but are not the headline and
  should stay in **unlocked mode** only, not the default supported-appliance
  experience.
- **On LITE specifically, day-to-day use is screen/button-first, not
  voice-first:** the owner glances at the e-ink for status, uses the touch
  buttons for quick actions, and falls back to their phone's SSH/dictation
  only when a real spoken instruction is needed — LITE was never meant to
  carry its own always-on voice pipeline the way BLOQ 1 does.

**Management/ops behavior expected of you specifically:**
- Support **multiple concurrent Claude Code sessions**, manageable by voice —
  when the owner starts a new one, prompt them for a name to distinguish it.
- Keep this file (your own CLAUDE.md) current as the single source of truth
  for what hardware exists on this device, so you never have to guess your
  own capabilities.
- **Do not** be the thing enforcing safety-critical behavior yourself.
  Overcharge protection, thermal cutoffs, and similar physically-dangerous
  failure modes must be enforced at the hardware or firmware/script level,
  independent of your judgment — you can report on these states, but you are
  not the safety mechanism.
- When a new USB WiFi adapter is plugged in, run the project's deterministic
  driver auto-install script rather than improvising a driver install — the
  vendor kernel is old enough that some chipsets need manual compilation,
  and that process should be scripted and repeatable, not ad hoc.

## OPEN DECISIONS — do not silently assume an answer

1. **Mic activation model — unresolved conflict between two planning
   sessions.** One thread (this session, after multiple rounds of explicit
   deliberation) locked in a **physical mic button, not always-listening**,
   specifically because it was the clean, demonstrable answer to the
   "is this thing secretly always listening" trust objection — explicitly
   including a hardware privacy LED tied to the same gate. A separate later
   conversation describes BLOQ 1 as **fully hands-free with no wake word and
   no push-to-talk**. These are not obviously compatible as literally stated.
   Three real options, from most to least private:
   - **(A) Push-to-talk only** — simplest, most private, least convenient.
   - **(B) On-device wake-word + local VAD, no button needed per-utterance,
     but a physical hardware mute/kill switch always present** — this
     reconciles "no push-to-talk required for normal use" with the earlier
     privacy design, since nothing reaches the cloud agent until a locally-
     detected trigger fires, and the hardware switch remains the trust
     backstop. **This is the most likely intended reading and the
     recommended default if no explicit answer is given.**
   - **(C) Fully open-mic, no trigger at all** — matches the new rundown's
     literal wording, but directly reopens the surveillance-trust objection
     the earlier jury process spent real effort closing. Needs an explicit,
     conscious decision if this is really what's wanted, not a default.
   **Do not build without resolving which of these it is.**

2. **PN532/NFC on BLOQ 1 flagship — STILL OPEN.** Requested in the merged
   utility spec; still absent from the latest, most detailed BLOQ 1
   component table. If flagship NFC is really wanted, it needs an explicit
   purchase line — it has not silently appeared on its own.

3. ~~External WiFi adapter (Alfa) port assignment~~ — **RESOLVED.** Confirmed
   the Alfa AWUS036H is BLOQ 1's adapter, not LITE's, and the 4 Pro has
   enough USB headroom that this isn't a contention concern.

4. **Two fans on LITE** — confirmed as bought, but flagged earlier as
   possibly excessive bulk/noise/grille-holes for a pocketable device. Worth
   a deliberate yes/no before finalizing the case.

5. **LITE button type — see the flagged inconsistency in LITE's Hardware
   Inventory above (capacitive TTP223 vs repurposed tactile switches).**
   Pick one; they're different parts with different feel and the
   vibration-feedback rationale only makes sense for one of them.

6. **Retail pricing conflict.** Two different LITE retail figures exist in
   the current numbers: "~€329" quoted alongside BLOQ 1's own pricing line,
   versus "~€300" computed directly from LITE's own €196.60 subtotal at
   ~34% margin. The €300 figure is the one with an actual cost basis shown;
   the €329 figure looks like it may be stale/leftover from an earlier pass.
   Confirm which is the real Kickstarter-facing number before it goes
   anywhere public.

## LEGAL/BRANDING NOTES (brief — full detail lives in project memory, not
repeated here since it's not operationally relevant to you as the on-device
agent)

- Hardware-only product; AI access is bring-your-own-account. Avoid any
  wording that implies an official partnership with Anthropic when
  describing yourself as "running Claude Code."
- This class of device (NFC/WiFi/sub-GHz toolkit bundled with general
  compute) is treated as legal to sell in the same category as Flipper Zero,
  per the project's own legal research — but the offensive capabilities stay
  in unlocked mode, never the marketed default, per the OPEN DECISIONS and
  CORE UTILITY sections above.
