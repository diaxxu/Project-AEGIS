# ArduPilot SITL Guide

Software-In-The-Loop simulation lets you run a complete virtual version of your aircraft on your laptop — with physics, GPS, wind, and all ArduPilot flight modes — before touching a single real component.

**Use this to:**
- Test the invoke server against real ArduPilot (not just mocks)
- Practice mission planning and verify loiter orbit behaviour
- Test failsafes by simulating link loss and low battery
- Learn how the flight modes behave without any crash risk

---

## What SITL Is

ArduPilot ships with a built-in flight simulator. When you run SITL:
- A virtual STM32H7 runs the full ArduPilot firmware in a process on your laptop
- A physics engine simulates the aircraft's movement and sensor readings
- It speaks the same MAVLink protocol as a real aircraft
- Mission Planner, QGroundControl, and your invoke server all connect to it as if it were real hardware

You can run two SITL instances simultaneously — one for the quad, one for the fixed-wing — and connect your actual invoke server to both of them.

---

## Requirements

- Linux, macOS, or Windows (WSL2 recommended on Windows)
- Python 3.7+
- Git
- ~2 GB disk space for ArduPilot source

---

## Installation

### Step 1 — Clone ArduPilot

```bash
git clone https://github.com/ArduPilot/ardupilot.git
cd ardupilot
git submodule update --init --recursive
```

This takes 5–10 minutes depending on your connection.

### Step 2 — Install dependencies

```bash
# From inside the ardupilot folder
Tools/environment_install/install-prereqs-ubuntu.sh -y

# Reload your shell PATH
. ~/.profile
```

On macOS, use the `install-prereqs-mac.sh` script instead.

### Step 3 — Build SITL (one-time, takes ~5 min)

```bash
# Build ArduCopter SITL
./waf configure --board sitl
./waf build --target bin/arducopter

# Build ArduPlane SITL
./waf build --target bin/arduplane
```

---

## Running the Simulation

### Terminal 1 — Start the quad SITL

```bash
cd ardupilot

# Start ArduCopter SITL on MAVLink port 5762
# --home sets the starting GPS coordinate (lat,lon,alt,heading)
# Change to your actual test location

sim_vehicle.py -v ArduCopter \
  --frame=quad \
  --home=33.5731,-7.5898,10,180 \
  --out=tcp:127.0.0.1:5762 \
  --no-mavproxy \
  -I 0
```

The `--out` flag creates a TCP connection. Your invoke server connects here instead of a serial port.

### Terminal 2 — Start the fixed-wing SITL

```bash
cd ardupilot

# Start ArduPlane SITL on a different port
sim_vehicle.py -v ArduPlane \
  --frame=flying-wing \
  --home=33.5731,-7.5898,10,180 \
  --out=tcp:127.0.0.1:5763 \
  --no-mavproxy \
  -I 1
```

`-I 1` gives it a different instance number so ports don't clash.

### Terminal 3 — Connect your invoke server to SITL

Edit `ground_station/config.py` temporarily:

```python
# SITL mode — use TCP instead of serial
QUAD_PORT = "tcp:127.0.0.1:5762"
FW_PORT   = "tcp:127.0.0.1:5763"
```

Then start the server:

```bash
cd aegis/ground_station
python3 invoke_server.py
```

You will see both virtual aircraft connect. Their GPS coordinates, battery, and mode update in real time.

### Step 4 — Connect Mission Planner to both SITL instances

Open Mission Planner → top-right dropdown → TCP → Connect to `127.0.0.1:5762`

Open a second Mission Planner window → TCP → `127.0.0.1:5763`

You can now watch both virtual aircraft in the map view as the invoke command flies them to a target.

---

## Running a Full Invoke Test Against SITL

With both SITL instances running and the invoke server connected:

```bash
# Send an invoke with coordinates near the SITL home location
curl -X POST http://localhost:5000/invoke \
  -H "Content-Type: application/json" \
  -d '{"lat": 33.5740, "lon": -7.5880, "alt": 15}'
```

Watch Mission Planner. You will see:
1. Quad switches to GUIDED mode
2. Quad arms and takes off
3. Quad flies toward the target coordinate
4. Quad enters a hover at 15m
5. Fixed-wing switches to AUTO mode
6. Fixed-wing flies to the loiter waypoint
7. Fixed-wing enters a constant-radius orbit

---

## Simulating Failsafes

### Test lost-link failsafe

```bash
# In the SITL terminal for the quad, type:
# (MAVProxy console is available when running without --no-mavproxy)
mode GUIDED    # ensure it's flying
# Then kill the invoke_server.py process
# Within 5 seconds, the quad should switch to RTL
```

Or more precisely, test via `mavproxy`:

```bash
mavproxy.py --master=tcp:127.0.0.1:5762 --baudrate=57600
# Once connected, type:
long MAV_CMD_DO_SET_MODE 0 6 0 0 0 0 0  # GUIDED mode
# Then disconnect — watch it RTL after 5s
```

### Test low battery

```bash
# In MAVProxy console for the quad:
param set BATT_LOW_VOLT 12.0  # set threshold above current voltage
# The battery failsafe should trigger immediately
```

### Test geofence

```bash
# Enable a circular geofence at home position, radius 100m
param set FENCE_ENABLE 1
param set FENCE_TYPE 2        # circle
param set FENCE_RADIUS 100    # 100m radius
param set FENCE_ACTION 1      # RTL on breach

# Now invoke with a coordinate outside 100m
# The aircraft should RTL before reaching the target
```

---

## SITL with Wind

Test how your loiter orbit behaves in wind conditions:

```bash
# Start ArduPlane SITL with 5 m/s north wind
sim_vehicle.py -v ArduPlane \
  --frame=flying-wing \
  --home=33.5731,-7.5898,10,180 \
  --out=tcp:127.0.0.1:5763 \
  --no-mavproxy \
  -I 1 \
  --add-param-file=<(echo "SIM_WIND_SPD=5\nSIM_WIND_DIR=0")
```

Observe how ArduPlane adjusts bank angle to hold the loiter radius in crosswind.

---

## Parameter Files in SITL

Load your AEGIS parameter files into the virtual aircraft just like you would a real one:

```bash
# In MAVProxy console (or Mission Planner Full Parameter List):
param load /path/to/aegis/firmware/quad/params.param
param load /path/to/aegis/firmware/fixedwing/params.param
```

This lets you verify your failsafe values and navigation parameters before loading them onto the real aircraft.

---

## Automating SITL Tests

You can script the entire test sequence using DroneKit Python:

```python
from dronekit import connect, VehicleMode, LocationGlobalRelative
import time

# Connect to SITL quad instance
vehicle = connect('tcp:127.0.0.1:5762', wait_ready=True)

print(f"GPS: {vehicle.gps_0.fix_type}, Armable: {vehicle.is_armable}")

# Wait for GPS
while not vehicle.is_armable:
    time.sleep(1)

# Switch to GUIDED, arm, fly to waypoint
vehicle.mode = VehicleMode("GUIDED")
vehicle.armed = True
while not vehicle.armed:
    time.sleep(0.5)

target = LocationGlobalRelative(33.5740, -7.5880, 15)
vehicle.simple_goto(target)

# Watch it fly for 30 seconds
for i in range(30):
    loc = vehicle.location.global_relative_frame
    print(f"  Alt: {loc.alt:.1f}m  Speed: {vehicle.groundspeed:.1f}m/s")
    time.sleep(1)

vehicle.close()
```

---

## Quick Reference

| Command | What it does |
|---------|-------------|
| `sim_vehicle.py -v ArduCopter --frame=quad -I 0` | Start quad SITL instance 0 |
| `sim_vehicle.py -v ArduPlane --frame=flying-wing -I 1` | Start FW SITL instance 1 |
| `--out=tcp:127.0.0.1:5762` | Expose MAVLink on TCP port |
| `--home=LAT,LON,ALT,HDG` | Set starting GPS location |
| `param set PARAM_NAME value` | Change parameter in MAVProxy console |
| `mode GUIDED` | Switch flight mode in MAVProxy console |
| `arm throttle` | Arm vehicle in MAVProxy console |

---

## Workflow Recommendation

1. Write a feature or change a parameter
2. Test it in SITL — confirm the behaviour is what you expect
3. Run `python3 tools/test_bench.py` — confirms the Python code is correct
4. Load parameters onto the real aircraft
5. Fly manually in STABILIZE to confirm the aircraft is healthy
6. Run one automated test flight with someone standing by on the RC transmitter

Never skip SITL when changing failsafe parameters. A wrong `BATT_CRT_ACTION` value or `FS_GCS_TIMEOUT` is trivial to catch in simulation and potentially catastrophic in the field.
