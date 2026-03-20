# AEGIS — Autonomous Escort & Guardian Integrated Swarm

> **One tap on your phone. Two drones launch from a base station, fly to your GPS coordinates, and hold position above you — completely autonomously.**

A quadcopter hovers directly overhead as a close escort. A fixed-wing aircraft orbits at wider radius as a surveillance halo. Both return home automatically when battery is low or the link is lost.

**Built with off-the-shelf hardware. No AI chips. No LiDAR. No custom firmware.** Just ArduPilot, a Raspberry Pi, and a Python script under 100 lines.

---

## Table of Contents

- [How It Works](#how-it-works)
- [System Architecture](#system-architecture)
- [Bill of Materials](#bill-of-materials)
- [Step-by-Step Build Guide](#step-by-step-build-guide)
- [Wiring Diagrams](#wiring-diagrams)
- [Ground Station Software](#ground-station-software)
- [ArduPilot Configuration](#ardupilot-configuration)
- [The Invoke App](#the-invoke-app)
- [Failsafes](#failsafes)
- [Flight Operations](#flight-operations)
- [Troubleshooting](#troubleshooting)
- [Safety & Legal](#safety--legal)
- [FAQ](#faq)

---

## How It Works

```
[Your Phone]
     |
     |  HTTP POST /invoke  (your GPS lat/lon/alt)
     |  via 4G / WiFi
     ↓
[Raspberry Pi — Ground Station]
     |              |
     | SiK 915MHz   | SiK 915MHz
     | radio link   | radio link
     ↓              ↓
[Quadcopter]    [Fixed-Wing]
 ArduCopter      ArduPlane
 GUIDED mode     AUTO + LOITER
 → flies to      → orbits your
   your GPS        GPS at 30m
   → hovers
```

1. You tap a button on a web page on your phone
2. The page reads your GPS and sends it to the Raspberry Pi over 4G
3. The Pi pushes MAVLink commands to both aircraft over SiK radio
4. The quadcopter arms, takes off, flies to your coordinate, and hovers
5. The fixed-wing (hand-launched) flies to your coordinate and enters a loiter orbit
6. Both aircraft return home automatically on low battery or lost link

**The aircraft do all navigation themselves using ArduPilot firmware.** You write zero flight code.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     GROUND STATION                       │
│                                                          │
│  ┌─────────────┐    ┌──────────────────────────────┐    │
│  │  4G Dongle  │    │      Raspberry Pi 4           │    │
│  │ Huawei E3372│◄──►│  - Flask invoke server        │    │
│  └─────────────┘    │  - MAVProxy (2 instances)     │    │
│                     │  - DroneKit-Python             │    │
│                     └──────────┬─────────────────────┘   │
│                                │                          │
│                    ┌───────────┴───────────┐             │
│                    │                       │             │
│             ┌──────┴──────┐         ┌──────┴──────┐      │
│             │ SiK Radio   │         │ SiK Radio   │      │
│             │ (USB-UART)  │         │ (USB-UART)  │      │
│             │ /dev/ttyUSB0│         │ /dev/ttyUSB1│      │
│             └──────┬──────┘         └──────┬──────┘      │
└────────────────────┼───────────────────────┼─────────────┘
                     │ 915 MHz               │ 915 MHz
                     │ SiK Radio Link        │ SiK Radio Link
          ┌──────────┼────────────┐          │
          │          ▼            │          ▼
          │   ┌─────────────┐    │   ┌─────────────┐
          │   │  Matek H743 │    │   │  Matek H743 │
          │   │    -Slim    │    │   │    -Wing    │
          │   │  ArduCopter │    │   │  ArduPlane  │
          │   │  GUIDED mode│    │   │  AUTO mode  │
          │   └──────┬──────┘    │   └──────┬──────┘
          │          │           │          │
          │   ┌──────┴──────┐    │   ┌──────┴──────┐
          │   │  M8N GPS    │    │   │  M8N GPS    │
          │   │  + Compass  │    │   │  + Compass  │
          │   └─────────────┘    │   └─────────────┘
          │                      │
          │     QUADCOPTER       │      FIXED-WING
          └──────────────────────┘   (SkyWalker X8)
```

---

## Bill of Materials

Total estimated cost: **$450 – $520 USD**

### Ground Station

| Part | Purpose | Where to Buy | Est. Cost |
|------|---------|-------------|-----------|
| Raspberry Pi 4 (2GB) | Central relay, runs Flask + MAVProxy | RPi / AliExpress | ~$40 |
| USB 4G dongle (Huawei E3372) | Internet uplink for invoke command | Amazon | ~$30 |
| SiK 915MHz telemetry radio ×2 (ground side) | MAVLink link to quad + FW | AliExpress | ~$15 ea. |
| USB power bank (10,000 mAh) or 5V BEC | Powers Pi in the field | Any | ~$10 |
| Weatherproof project box | Houses ground station | Amazon | ~$8 |
| **Ground station subtotal** | | | **~$118** |

> **Note:** Use 433 MHz SiK radios if you are in Europe/UK. 915 MHz is for North America. Check your local regulations.

### Quadcopter

| Part | Purpose | Where to Buy | Est. Cost |
|------|---------|-------------|-----------|
| Matek H743-Slim v3 | Flight controller (STM32H7) | Matek / GetFPV | ~$45 |
| M8N GPS module (with compass) | GPS positioning | AliExpress | ~$18 |
| SiK 915MHz telemetry radio (air side) | MAVLink link to ground | AliExpress | ~$15 |
| F450 frame clone | Chassis + arms | AliExpress | ~$15 |
| 4× 2212 920KV brushless motors | Propulsion | AliExpress | ~$20 |
| 4-in-1 30A ESC (BLHeli_S) | Motor control | AliExpress | ~$20 |
| 4× 9045 propellers (2× CW, 2× CCW) | Thrust | AliExpress | ~$5 |
| 3S 2200 mAh LiPo battery | Power | Any hobby shop | ~$20 |
| XT60 connector + power wiring | Power distribution | Any | ~$5 |
| RC receiver (FlySky FS-iA6B or similar) | Manual override | AliExpress | ~$12 |
| **Quadcopter subtotal** | | | **~$175** |

> **RC transmitter and receiver are mandatory.** Never fly autonomous without a manual override capability. A FlySky FS-i6 transmitter (~$35) works well.

### Fixed-Wing

| Part | Purpose | Where to Buy | Est. Cost |
|------|---------|-------------|-----------|
| Matek H743-Wing v2 | Flight controller (STM32H7) | Matek / GetFPV | ~$55 |
| M8N GPS module (with compass) | GPS positioning | AliExpress | ~$18 |
| SiK 915MHz telemetry radio (air side) | MAVLink link to ground | AliExpress | ~$15 |
| SkyWalker X8 flying wing (1880mm) | Airframe | AliExpress / HobbyKing | ~$50 |
| 1400KV brushless motor (pusher) | Propulsion | AliExpress | ~$15 |
| 30A ESC | Motor control | AliExpress | ~$10 |
| 2× 9g servos | Elevon control | AliExpress | ~$6 |
| 10×4.7 propeller (pusher) | Thrust | Any | ~$5 |
| 3S 4000 mAh LiPo battery | Power (40–50 min endurance) | Any hobby shop | ~$25 |
| RC receiver | Manual override | AliExpress | ~$12 |
| **Fixed-wing subtotal** | | | **~$211** |

### Tools Required

| Tool | Purpose |
|------|---------|
| Soldering iron + solder | ESC/motor/power wiring |
| Multimeter | Voltage checks, continuity |
| Laptop with Windows/Mac/Linux | Mission Planner / QGroundControl |
| LiPo charger (balance charger) | Charging batteries |
| RC transmitter (FlySky FS-i6 or similar) | Manual override during flight |
| Zip ties, heat shrink tubing, double-sided tape | Assembly |
| Phillips and hex screwdrivers | Frame assembly |

---

## Step-by-Step Build Guide

### Phase 1: Flash Firmware

#### Step 1 — Flash ArduCopter onto the quad FC

1. Connect the **Matek H743-Slim** to your laptop via USB-C
2. Download and open [Mission Planner](https://ardupilot.org/planner/docs/mission-planner-installation.html)
3. Go to **Setup → Install Firmware**
4. Select **ArduCopter** → **Quad**
5. Click Install and wait for completion
6. The FC will reboot automatically

#### Step 2 — Flash ArduPlane onto the fixed-wing FC

1. Connect the **Matek H743-Wing** via USB-C
2. In Mission Planner → **Setup → Install Firmware**
3. Select **ArduPlane** → **Flying Wing**
4. Click Install

---

### Phase 2: Calibrate Both Aircraft

Run these calibrations in Mission Planner **Setup → Mandatory Hardware** for each aircraft.

#### Step 3 — Accelerometer Calibration (both aircraft)

1. Click **Accel Calibration**
2. Follow the prompts — place the aircraft flat, on each side, nose-up, nose-down, on its back
3. Click **Done** when complete
4. The FC now knows which way is level

#### Step 4 — Compass Calibration (both aircraft)

1. Click **Compass**
2. Click **Start** on the onboard compass
3. Slowly rotate the aircraft through all orientations (think: every face of a cube pointing down)
4. Stop when the progress bar fills and the calibration accepts
5. Write the offsets

#### Step 5 — Radio Calibration (both aircraft)

1. Connect your RC receiver to the FC
2. Click **Radio Calibration**
3. Move all sticks and switches to their extremes
4. Click **Click when Done**

#### Step 6 — Check Servo Directions (fixed-wing only)

1. In Mission Planner → **Setup → Mandatory Hardware → Servo Output**
2. Tilt the nose up → the elevons should deflect **down** (corrective)
3. Tilt nose left → the elevons should correct **right**
4. If reversed, check the **REV** box for that servo channel

---

### Phase 3: Configure Parameters

In Mission Planner → **Config → Full Parameter List**, set these values. Use the search box to find each one.

#### Step 7 — Quadcopter parameters

```
ARMING_CHECK    = 1        (all pre-arm checks enabled)
FS_GCS_ENABLE   = 1        (lost link failsafe ON)
FS_GCS_TIMEOUT  = 5        (5 second timeout before RTL)
RTL_ALT         = 3000     (return at 30m altitude)
BATT_LOW_VOLT   = 10.5     (3S low voltage = 3.5V/cell)
BATT_LOW_ACTION = 2        (RTL on low battery)
BATT_CRT_VOLT   = 9.9      (3S critical = 3.3V/cell)
BATT_CRT_ACTION = 2        (RTL on critical)
WPNAV_SPEED     = 500      (5 m/s transit speed — safe for first flights)
GUID_OPTIONS    = 0        (standard GUIDED mode)
SERIAL2_PROTOCOL= 2        (MAVLink2 on UART2 — for SiK radio)
SERIAL2_BAUD    = 57       (57600 baud)
```

#### Step 8 — Fixed-wing parameters

```
ARMING_CHECK    = 1
FS_GCS_ENABLE   = 1
FS_GCS_TIMEOUT  = 5
RTL_ALTITUDE    = 5000     (return at 50m — needs clearance)
BATT_LOW_VOLT   = 10.5
BATT_LOW_ACTION = 2
WP_LOITER_RAD   = 50       (50m loiter orbit radius)
LOITER_RADIUS   = 50
CRUISE_SPEED    = 14       (14 m/s cruise — good for SkyWalker X8)
AIRSPEED_MIN    = 10       (stall prevention)
SERIAL2_PROTOCOL= 2
SERIAL2_BAUD    = 57
ELEVON_OUTPUT   = 4        (elevon mixing for flying wing)
```

---

### Phase 4: Wire the SiK Radios to the Flight Controllers

#### Step 9 — SiK radio wiring (same for both aircraft)

The SiK radio has a 6-pin JST connector. Wire it to a spare UART on the FC:

```
SiK Radio Pin  →  Matek FC Pin
─────────────────────────────
GND            →  GND
5V             →  5V
TX             →  RX (of UART2)
RX             →  TX (of UART2)
CTS            →  (leave unconnected)
RTS            →  (leave unconnected)
```

> **Always cross TX→RX and RX→TX.** TX of the radio goes to RX of the FC, and vice versa.

#### Step 10 — Pair the radios in Mission Planner

1. Plug one ground-side SiK radio into your laptop via USB
2. In Mission Planner → **Setup → Optional Hardware → SiK Radio**
3. Click **Load Settings**
4. Confirm Net ID on the ground radio matches the air radio (default is 25)
5. Set Net ID to **25** for the quad pair and **26** for the fixed-wing pair (so they don't interfere)
6. Click **Save Settings** on both radios in each pair
7. The RSSI LED should go solid green when the air radio is powered and in range

---

### Phase 5: Set Up the Raspberry Pi Ground Station

#### Step 11 — Flash Raspberry Pi OS

1. Download [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Choose: **Raspberry Pi OS Lite (64-bit)**
3. Click the ⚙️ settings icon → enable SSH, set a hostname (e.g. `aegis-base`), set your WiFi credentials
4. Flash to a microSD card (16GB minimum)
5. Insert into Pi and power up

#### Step 12 — First boot and SSH

```bash
# From your laptop (same WiFi network)
ssh pi@aegis-base.local

# Or use the IP address shown on your router
ssh pi@192.168.x.x
```

#### Step 13 — Install dependencies

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-dev screen -y
pip3 install dronekit flask requests
```

#### Step 14 — Connect the 4G dongle

1. Plug in the Huawei E3372 via USB
2. Run `ip a` — a new interface should appear (`usb0` or `eth1`)
3. Test connectivity: `curl ifconfig.me` — you should see a public IP
4. Install DuckDNS for a stable hostname (see [duckdns.org](https://www.duckdns.org)):

```bash
# Create update script
mkdir duckdns && cd duckdns
echo 'echo url="https://www.duckdns.org/update?domains=YOUR_DOMAIN&token=YOUR_TOKEN&ip=" | curl -k -o ~/duckdns/duck.log -K -' > duck.sh
chmod +x duck.sh

# Add to crontab (update every 5 minutes)
crontab -e
# Add this line:
*/5 * * * * ~/duckdns/duck.sh >/dev/null 2>&1
```

#### Step 15 — Connect the SiK radios to the Pi

```bash
# Plug in both USB SiK ground radios
# Check they appear
ls /dev/ttyUSB*
# Should show: /dev/ttyUSB0  /dev/ttyUSB1

# Find out which is which (power up one aircraft at a time to confirm)
# Quad radio   → /dev/ttyUSB0
# FW radio     → /dev/ttyUSB1
```

#### Step 16 — Deploy the ground station code

```bash
# Clone or copy the ground_station folder to the Pi
cd ~
git clone https://github.com/YOUR_USERNAME/aegis.git
cd aegis/ground_station

# Or manually copy the files from this repo
```

#### Step 17 — Run the invoke server

```bash
python3 invoke_server.py

# You should see:
# [AEGIS] Connecting to quad on /dev/ttyUSB0...
# [AEGIS] Connecting to fixed-wing on /dev/ttyUSB1...
# [AEGIS] Both vehicles connected.
# [AEGIS] Invoke server running on port 5000
```

#### Step 18 — Set the server to auto-start on boot

```bash
sudo cp aegis/scripts/aegis.service /etc/systemd/system/
sudo systemctl enable aegis
sudo systemctl start aegis
```

---

### Phase 6: Assemble the Quadcopter

#### Step 19 — Frame assembly

1. Assemble the F450 frame per its instructions (4 arms onto center plate)
2. Mount the 4-in-1 ESC in the center, secure with double-sided tape + zip ties
3. Mount motors on arm tips — CW motors on front-left + rear-right, CCW on front-right + rear-left
4. Route motor wires down through the arms

#### Step 20 — Solder motor connections

Wire each motor to the ESC. Motor rotation direction is set in the ESC configuration, but follow this layout:

```
        Front
    CW        CCW
(Motor 1)  (Motor 2)
    ●          ●
    |          |
    |  F450    |
    |          |
    ●          ●
(Motor 3)  (Motor 4)
   CCW        CW
        Rear
```

If a motor spins the wrong direction after flashing, swap any two of its three wires.

#### Step 21 — Mount the flight controller

1. Use the foam anti-vibration pads that come with the Matek H743
2. Mount FC in the center, **arrow pointing forward**
3. Connect ESC signal wires to FC motor outputs 1–4
4. Connect the ESC's 5V BEC output to the FC's 5V power input

#### Step 22 — Mount GPS mast and module

1. Attach the GPS mast to the top plate (keeps GPS away from motor interference)
2. Connect M8N GPS to FC: `GPS1` UART for serial data, `I2C1` for compass
3. Arrow on the GPS module must point forward (same as FC)

#### Step 23 — Mount telemetry radio and receiver

1. Mount SiK radio and RC receiver on top plate or side arm
2. Wire SiK radio to FC UART2 (see Step 9 wiring)
3. Wire RC receiver to FC SBUS or PPM input
4. Secure all wires with zip ties — nothing loose near props

---

### Phase 7: Assemble the Fixed-Wing

#### Step 24 — SkyWalker X8 assembly

1. Follow the X8 manual for basic airframe assembly (it comes mostly pre-built)
2. Install the pusher motor at the rear, prop facing backward
3. Install both servos in the elevon servo pockets
4. Connect servo horns and pusher rods per the X8 guide

#### Step 25 — Install the flight controller

1. Mount Matek H743-Wing in the fuselage bay
2. Arrow pointing toward the nose
3. Use foam pads for vibration isolation

#### Step 26 — Connect servos and motor

```
Matek H743-Wing output mapping:
├── Output 1  → Left elevon servo
├── Output 2  → Right elevon servo
└── Output 3  → ESC (throttle)
```

#### Step 27 — Mount GPS and radio

- GPS mast on top of fuselage, arrow forward
- SiK radio mounted inside fuselage or on top (clear line of sight to ground)
- RC receiver inside fuselage

---

## Ground Station Software

See the [`ground_station/`](ground_station/) folder for all code.

### File structure

```
ground_station/
├── invoke_server.py      # Main Flask server — this is what you run
├── mavlink_bridge.py     # DroneKit vehicle management
├── config.py             # All configurable settings in one place
├── requirements.txt      # Python dependencies
└── web/
    └── index.html        # The phone invoke webpage
```

### How to configure

Edit [`ground_station/config.py`](ground_station/config.py):

```python
# Serial ports for the two SiK radios
QUAD_PORT   = "/dev/ttyUSB0"
FW_PORT     = "/dev/ttyUSB1"
BAUD_RATE   = 57600

# Default escort altitude in metres above launch point
QUAD_ALT    = 15   # quad hovers at 15m above you
FW_ALT      = 30   # fixed-wing orbits at 30m above you
FW_RADIUS   = 50   # fixed-wing loiter orbit radius in metres

# Network
SERVER_PORT = 5000
```

---

## ArduPilot Configuration

### Quick reference — all parameters in one place

See [`firmware/quad/params.param`](firmware/quad/params.param) and [`firmware/fixedwing/params.param`](firmware/fixedwing/params.param) for complete parameter files you can load directly in Mission Planner.

**To load a .param file:**
Mission Planner → Config → Full Parameter List → Load from file

### Flight modes setup

Configure your RC transmitter's flight mode switch (usually channel 5) to give you manual override in all situations:

**Quadcopter flight modes:**
```
Position 1 (switch up):    STABILIZE   ← manual, no GPS
Position 2 (switch mid):   LOITER      ← GPS hold, manual control
Position 3 (switch down):  RTL         ← return to launch
```

**Fixed-wing flight modes:**
```
Position 1 (switch up):    MANUAL      ← full manual
Position 2 (switch mid):   FBWA        ← stabilised manual
Position 3 (switch down):  AUTO        ← follows mission (invoke mode)
```

---

## The Invoke App

The web interface lives at [`ground_station/web/index.html`](ground_station/web/index.html).

Access it from your phone at:
```
http://YOUR-DUCKDNS-DOMAIN.duckdns.org:5000
```

It does three things:
1. Requests your phone's GPS location (you must grant permission)
2. Shows your current coordinates so you can confirm they are correct
3. Sends an HTTP POST to `/invoke` with your coordinates when you tap the button

### Manual invoke (curl)

You can also invoke from a terminal:
```bash
curl -X POST http://YOUR-PI-IP:5000/invoke \
  -H "Content-Type: application/json" \
  -d '{"lat": 33.5731, "lon": -7.5898, "alt": 15}'
```

---

## Failsafes

These are all configured in ArduPilot firmware — no code required.

| Scenario | What happens | Parameter |
|---------|-------------|-----------|
| SiK radio link lost for 5 seconds | Both aircraft RTL | `FS_GCS_ENABLE=1`, `FS_GCS_TIMEOUT=5` |
| Battery below 10.5V (3S) | RTL | `BATT_LOW_VOLT=10.5`, `BATT_LOW_ACTION=2` |
| Battery below 9.9V (3S critical) | Immediate RTL | `BATT_CRT_VOLT=9.9`, `BATT_CRT_ACTION=2` |
| RC transmitter signal lost | RTL | `FS_THR_ENABLE=1` |
| RC switch to RTL position | RTL | Manual — flight mode switch |
| GPS accuracy drops below threshold | Loiter in place | Built into ArduPilot |

---

## Flight Operations

### Pre-flight checklist (run every flight)

```
□ Both LiPo batteries charged to storage voltage or full charge
□ Both aircraft powered on, SiK radio LEDs solid
□ Mission Planner / QGroundControl showing both vehicles with GPS fix
□ GPS fix: 3D fix, 8+ satellites on each aircraft
□ Battery voltage healthy on both aircraft
□ No red warnings in Mission Planner HUD
□ RC transmitter on, bound to both receivers
□ Invoke server running on Pi (check with: systemctl status aegis)
□ Pi has 4G internet connection (check with: curl ifconfig.me)
□ No people or obstructions in the flight path
□ Wind under 20 km/h (Beaufort 4 or below)
```

### Invoke procedure

1. Walk to the location where you want the escort
2. Open the invoke web page on your phone
3. Wait for GPS accuracy to show < 5m
4. Hand-launch the fixed-wing (firm level throw into the wind)
5. Tap **INVOKE**
6. The quad will arm and take off automatically
7. The fixed-wing will transition to AUTO mode in flight

### Landing procedure

**Normal (battery-triggered):**
Both aircraft RTL automatically. The quad will land at the home point. Fly the fixed-wing down manually using your RC transmitter once it is loitering over home.

**Manual RTL:**
- QGroundControl: tap aircraft → Change Mode → RTL
- RC transmitter: flip flight mode switch to RTL position

### Post-flight

```
□ Power down both aircraft immediately after landing
□ Disconnect LiPo batteries
□ Check props for damage
□ Check all wiring is still secure
□ Charge batteries to storage voltage if not flying within 48 hours
□ Review logs in Mission Planner (Ctrl+F → Flight Data) for any anomalies
```

---

## Troubleshooting

### "Drone won't arm"

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Red LED flashing fast | Pre-arm check failed | Check Mission Planner messages tab for which check failed |
| "GPS: Need 3D Fix" | Not enough satellites | Wait 90 seconds in open sky |
| "Compass not calibrated" | Skipped compass cal | Run compass calibration |
| "Compass variance" | Interference | Move away from metal objects, recalibrate |
| "EKF variance" | Vibration or bad IMU | Check FC mounting foam pads |

### "SiK radio won't connect"

1. Check both radios show solid green LED (paired and connected)
2. Confirm baud rate matches on both ends: `SERIAL2_BAUD = 57` on FC, 57600 in MAVProxy
3. Check TX/RX are crossed correctly in wiring
4. Try a different USB port on the Pi
5. Run `mavproxy.py --master=/dev/ttyUSB0 --baudrate=57600` directly to see raw connection

### "Quad drifts in hover"

1. Recalibrate compass in the actual flying location (metal in buildings affects compass)
2. Check GPS has 3D fix and 8+ satellites before invoking
3. Reduce `WPNAV_SPEED` to 300 (3 m/s) for calmer position hold
4. Check props are balanced and tight

### "Fixed-wing won't hold orbit"

1. Confirm `WP_LOITER_RAD = 50` is set
2. Check GPS has good fix
3. Increase `LOITER_RADIUS` if orbit is too tight for current wind
4. Ensure airspeed is above `AIRSPEED_MIN` — check Mission Planner HUD

### "Invoke command not reaching Pi"

1. Check the Pi has 4G internet: `curl ifconfig.me`
2. Check DuckDNS is updating: check the duck.log file
3. Check Flask server is running: `systemctl status aegis`
4. Check firewall: `sudo ufw allow 5000`
5. Try invoke from within your local network first to isolate 4G vs server issue

### "DroneKit says 'vehicle not responding'"

1. Power cycle both the aircraft and SiK radio
2. Wait 10 seconds for ArduPilot to fully boot
3. Check `/dev/ttyUSB0` and `/dev/ttyUSB1` are not swapped — power up aircraft one at a time to confirm which is which
4. Check `SERIAL2_PROTOCOL = 2` is set on the FC

---

## Safety & Legal

### Before you fly — read this

- **NEVER fly over people.** This system has no collision avoidance.
- **ALWAYS have RC transmitter in hand** and be ready to take manual control.
- **ALWAYS fly in VLOS** (visual line of sight) — keep both aircraft visible at all times.
- **Check local regulations.** In most countries you need to register your drones and follow rules about altitude, restricted areas, and proximity to airports.
- **Never fly near airports, hospitals, or emergency scenes.**
- **Never fly in rain or wind above Beaufort 4 (~20 km/h).**
- **Test all failsafes on the bench** before the first flight — cut the radio link deliberately and confirm RTL triggers.

### Country-specific resources

| Country | Registration / Rules |
|---------|---------------------|
| USA | [FAA DroneZone](https://faadronezone.faa.gov/) — register if over 250g |
| UK | [CAA Register](https://register-drones.caa.co.uk/) — required |
| EU | [EASA](https://www.easa.europa.eu/en/domains/drones) — required |
| Morocco 🇲🇦 | [ANAC](https://www.anac.gov.ma) — registration required |
| Canada | [Transport Canada](https://tc.canada.ca/en/aviation/drone-safety) |

### This project is for educational purposes

This repository is a technical reference for building autonomous UAV systems. You are responsible for ensuring your build complies with all local laws and that you operate safely.

---

## FAQ

**Q: Can I use WiFi instead of SiK radio to talk to the drones?**
A: You can for short range testing, but SiK at 915 MHz has dramatically better range and penetration than 2.4 GHz WiFi. At 200m with obstacles, WiFi becomes unreliable. SiK will still work reliably at 1km.

**Q: Can I use Bluetooth?**
A: No. Bluetooth max range is 30–100m in open air. Useless for this application.

**Q: Do I need a Jetson or any AI computer?**
A: No. ArduPilot on the STM32H7 handles all navigation. The Raspberry Pi only relays commands — a Pi Zero 2W would work for the server, though Pi 4 gives more headroom.

**Q: Can I add obstacle avoidance later?**
A: Yes. ArduPilot supports rangefinder-based obstacle avoidance. You can add a cheap ultrasonic sensor for basic avoidance, or a Benewake TF-Mini LiDAR (~$50) for better coverage, without changing any of this architecture.

**Q: Can I add more drones?**
A: Yes. Add another SiK radio pair and another vehicle connection in `config.py`. The invoke server is designed to support N vehicles.

**Q: What range does this system have?**
A: SiK radio range: 1–2 km. 4G range: unlimited (wherever there is cell coverage). The practical limit is VLOS — you need to see the aircraft, which is roughly 500m in good conditions.

**Q: What if my phone GPS is inaccurate?**
A: Phone GPS accuracy is typically 3–5m outdoors. That is sufficient for this use case. If you need better accuracy, you can use a dedicated GPS receiver paired to your phone via Bluetooth.

**Q: Can the fixed-wing auto-land?**
A: ArduPlane supports automatic landing (LAND waypoint) but it requires careful configuration of the glide slope, flare altitude, and approach path. For a first build, manual landing using the RC transmitter is strongly recommended.

---

## Contributing

Pull requests are welcome. If you build this, please open an issue with photos and any modifications you made — it helps everyone.

## License

MIT License — see [LICENSE](LICENSE). Build freely, fly responsibly.

---

*Built with ArduPilot, DroneKit, Flask, and a lot of LiPo batteries.*
