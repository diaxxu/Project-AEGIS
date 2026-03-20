# Upgrade Path

This document covers the natural evolution of the build — in the order most people want to do them. Each upgrade is self-contained. Do them one at a time and test fully before moving to the next.

---

## Upgrade 1 — Add a Camera (FPV / Gimbal)

**Why:** Visual feedback from the escort aircraft. The quad can relay a live view back to your phone.

**Complexity:** Low  
**Cost:** $30–$120  
**Prerequisite:** Stable hover working correctly

### Option A — Simple FPV camera (no gimbal, cheapest)

Attach a small analog or digital FPV camera to the quad. Add a 5.8GHz video transmitter. Use a pair of FPV goggles or a screen receiver on the ground.

```
Recommended stack:
├── RunCam Robin 3 (camera, 4g)         ~$25
├── Happymodel OVX300 VTX               ~$15
└── Budget FPV goggles or monitor       ~$30–$80
```

No code changes needed. This is purely analogue video — it bypasses ArduPilot entirely.

### Option B — Digital camera to phone (best for the AEGIS use case)

Mount a Raspberry Pi Zero 2W with a HQ Camera module on the quad. Stream H.264 video to your phone over the same 4G link the invoke server uses.

```
Additional hardware:
├── Raspberry Pi Zero 2W                ~$15
├── RPi HQ Camera module                ~$25
├── Short USB-C power cable             ~$3
└── 3D printed mount or foam tape
```

The Pi Zero streams video with `rpicam-vid`:
```bash
# On the Pi Zero (on the aircraft):
rpicam-vid -t 0 --inline --listen -o tcp://0.0.0.0:8888

# View on phone browser (add to invoke web page as <video> element):
# http://YOUR-PI-IP:8888
```

This gives you a live view on the same phone page as the INVOKE button.

### Gimbal (optional, stabilised video)

A 2-axis brushless gimbal eliminates jitter from motor vibration and flight movements. The Matek H743-Slim has two dedicated gimbal PWM outputs.

```
Recommended: iFlight GM40 2-axis gimbal   ~$45
Connect to:  FC output channels 9 and 10
ArduPilot:   MNT1_TYPE = 1 (Servo)
             MNT1_PITCH_MIN = -60
             MNT1_PITCH_MAX = 30
```

---

## Upgrade 2 — Obstacle Avoidance

**Why:** Prevents the quad from flying into things when it transits to your location.

**Complexity:** Medium  
**Cost:** $50–$200  
**Prerequisite:** Everything working cleanly without it first

ArduPilot supports rangefinder-based obstacle avoidance natively. No code changes to the invoke server needed — it all happens in the FC.

### Option A — Benewake TF-Mini Plus (~$50)

Single-direction 12m LiDAR. Mount it on the front of the quad facing forward.

```
Wiring (UART):
TF-Mini TX  →  FC UART3 RX
TF-Mini RX  →  FC UART3 TX
TF-Mini 5V  →  5V
TF-Mini GND →  GND

ArduPilot parameters:
SERIAL3_PROTOCOL = 9    (Rangefinder)
SERIAL3_BAUD = 115      (115200)
RNGFND1_TYPE = 20       (Benewake TF-Mini)
RNGFND1_ORIENT = 0      (forward)
RNGFND1_MAX_CM = 1200   (12m max range)
AVOID_ENABLE = 2        (use rangefinder for avoidance)
AVOID_MARGIN = 200      (stop 2m from obstacle)
```

### Option B — 5× TF-Luna sensors ($25 each = ~$125)

Full 360° horizontal coverage. Mount one sensor on each face of the quad (front, back, left, right, down).

```
Each TF-Luna uses I2C. Set unique I2C addresses:
  Front: 0x10  Back: 0x11  Left: 0x12  Right: 0x13  Down: 0x14

ArduPilot supports up to 10 rangefinders simultaneously:
RNGFND1_TYPE through RNGFND5_TYPE = 25 (TF-Luna I2C)
RNGFND1_ADDR through RNGFND5_ADDR = 0x10 through 0x14
```

### Proximity sensor vs. collision avoidance

ArduPilot has two avoidance modes:
- `AVOID_ENABLE = 2` — simple stop-and-hold when obstacle detected
- `AVOID_ENABLE = 3` — full path planning around obstacles (requires more tuning)

Start with mode 2. It stops the quad when an obstacle is closer than `AVOID_MARGIN`. Once that works reliably, experiment with mode 3.

---

## Upgrade 3 — Second Quadcopter

**Why:** Redundancy. Two quads means one can RTL for battery while the other maintains the escort.

**Complexity:** Low (software), Medium (hardware)  
**Cost:** ~$175 (same as first quad)  
**Prerequisite:** First quad working perfectly

### Hardware

Identical to the first quad. Buy a second matched SiK radio pair (set Net ID to 27 to avoid interference with the existing pairs on 25 and 26).

### Software changes

In `ground_station/config.py`:
```python
# Add a third serial port for the second quad
QUAD2_PORT = "/dev/ttyUSB2"
QUAD2_BAUD = 57600
```

In `ground_station/mavlink_bridge.py`:
```python
# Add a third vehicle connection
self.quad2 = connect(QUAD2_PORT, baud=QUAD2_BAUD, wait_ready=True, timeout=CONNECT_TIMEOUT)

# In invoke():
# Send to quad2 with a slight offset from quad1
target_q2 = LocationGlobalRelative(lat + 0.00005, lon - 0.00005, alt)
self.quad2.simple_goto(target_q2)
```

The second quad flies to a position slightly offset from the first (about 5m away) to avoid GPS conflicts causing both to drift into each other.

### Formation keeping

For more precise formation keeping, use ArduCopter's `follow` mode:
```
# On the second quad — set it to follow the first quad's MAVLink ID
FOLL_ENABLE = 1
FOLL_SYSID  = 1     (MAVLink system ID of the first quad)
FOLL_DIST_X = -2    (stay 2m behind)
FOLL_DIST_Y = 0
FOLL_DIST_Z = 0
```

---

## Upgrade 4 — RTK GPS (centimetre precision)

**Why:** Standard M8N GPS is accurate to 3–5m. RTK GPS gets to 1–3cm. The quad holds position within centimetres.

**Complexity:** Medium-High  
**Cost:** $150–$350 for an entry-level RTK system  
**Prerequisite:** Everything else working well

### How RTK works

RTK uses a second GPS receiver (the "base") on the ground, which knows its exact position. It sends correction data to the aircraft GPS ("rover") over a radio link. The rover uses these corrections to reduce its position error from metres to centimetres.

```
[Base station GPS]  ──correction data──►  [Rover GPS on aircraft]
(fixed known position)                    (uses corrections to get cm accuracy)
```

### Recommended entry-level: SparkFun ZED-F9P breakout

```
Ground (base):     SparkFun ZED-F9P       ~$75
Aircraft (rover):  SparkFun ZED-F9P       ~$75
Correction link:   SiK 915MHz radios      ~$30 (third pair, different Net ID)
                   Total:                ~$180
```

The base station sends RTCM3 correction data over the third SiK radio pair. The rover receives it on a spare FC UART.

```
ArduPilot configuration (rover):
GPS_TYPE2  = 5          (NMEA with RTCM injection)
SERIAL4_PROTOCOL = 20   (RTCM3 corrections)
SERIAL4_BAUD = 57       (57600 baud)
```

### Cheaper option: u-blox M8P kit (~$60 total)

Less precise (2–5cm vs 1–2cm) but significantly cheaper. Available as base+rover kits from AliExpress. Confirmed working with ArduPilot.

---

## Upgrade 5 — Cellular Telemetry (remove SiK radios)

**Why:** Unlimited range. No radio frequency licensing concerns. Telemetry wherever there is cell coverage.

**Complexity:** Medium  
**Cost:** $40–$80 per aircraft + SIM card costs  
**Trade-off:** Dependent on cell network. Higher latency than SiK (~100–300ms vs ~20ms). Not suitable as primary link for fast manoeuvres, but fine for autonomous waypoint missions.

### Hardware: SIM7600G-H 4G HAT

```
Per aircraft:
├── SIM7600G-H 4G module      ~$35
└── SIM card (data only)      ~$5–$15/month
```

The SIM7600 connects to the FC UART and appears as a transparent IP link. You configure it to connect to a MQTT broker or direct TCP connection back to the Pi.

### Architecture with cellular telemetry

```
[Aircraft FC]
     │ UART
[SIM7600 4G module]
     │ 4G network
[MQTT broker (cloud or Pi)]
     │
[Raspberry Pi ground station]
```

This completely removes the range limitation of SiK radios. The aircraft can be kilometres away and still receive MAVLink commands.

```
MAVProxy with cellular:
mavproxy.py --master=tcp:BROKER_IP:PORT --baudrate=57600
```

Keep an RC transmitter on the aircraft as backup.

---

## Upgrade Priority Matrix

| Upgrade | Impact | Cost | Difficulty | Do it when... |
|---------|--------|------|-----------|---------------|
| FPV camera | High | Low | Low | You want visual feedback |
| Obstacle avoidance | High | Medium | Medium | Flying near structures |
| Second quad | Medium | Medium | Low | You need redundancy |
| RTK GPS | High | Medium | Medium-High | Precision matters |
| Cellular telemetry | Medium | Medium | Medium | You need long range |
| Gimbal | Medium | Medium | Low | You need stable video |

---

## What NOT to Upgrade (yet)

**Computer vision / AI inference** — Adding a Jetson Nano or Coral TPU is a significant step up in power consumption, weight, heat management, and software complexity. The current architecture with ArduPilot GPS navigation achieves the stated mission goal without it. Add it when you have a specific detection task that GPS navigation cannot solve.

**Fixed-wing to VTOL** — Converting the X8 to a VTOL (tilt-rotor or tail-sitter) is an entirely different build. Keep the X8 as-is until you are very comfortable with fixed-wing flight characteristics.

**Swarm coordination (multi-vehicle follow)** — ArduPilot's swarm support is production-quality for 2–4 vehicles. But swarm behaviour requires that each individual vehicle is rock-solid first. Build reliability before complexity.
