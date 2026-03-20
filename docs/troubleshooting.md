# AEGIS Troubleshooting Guide

---

## Quadcopter won't arm

**Check Mission Planner Messages tab first** — it will tell you exactly which check failed.

| Message | Cause | Fix |
|---------|-------|-----|
| `GPS: Need 3D Fix` | Not enough satellites | Wait 60–90 sec in open sky |
| `Compass not calibrated` | Skipped calibration | Run compass cal in Mission Planner |
| `Compass variance` | Magnetic interference | Move away from metal, redo cal at flying site |
| `EKF: IMU0 over speed` | Vibration too high | Check FC mounting foam pads |
| `PreArm: RC not calibrated` | Skipped RC cal | Run radio calibration |
| `PreArm: Throttle below Failsafe` | Throttle too low | Check FS_THR_VALUE param |
| `PreArm: Battery failsafe` | Voltage too low | Charge LiPo |
| `PreArm: Hardware safety switch` | Safety button not pressed | Some FCs have a safety button — press it |

---

## SiK radio won't connect

**Symptoms:** Radio LED stays blinking (not solid), DroneKit says "no heartbeat received"

1. Confirm both radios have matching Net ID
   - Mission Planner → Setup → Optional Hardware → SiK Radio → Load Settings
   - Ground and air radios must have same Net ID (25 for quad, 26 for FW)

2. Check baud rate matches
   - Radio: default 57600
   - FC: `SERIAL2_BAUD = 57`

3. Confirm TX/RX wiring is crossed (TX→RX, RX→TX)

4. Try different USB port on the Pi

5. Test with MAVProxy directly:
   ```bash
   mavproxy.py --master=/dev/ttyUSB0 --baudrate=57600
   ```
   You should see `heartbeat from` messages within 5 seconds.

6. Check the air radio has 5V power (measure with multimeter)

---

## DroneKit says "vehicle not responding" or connection timeout

1. Power cycle the aircraft and wait 15 seconds for full boot
2. Check the correct serial port: `ls /dev/ttyUSB*`
   - Power up one aircraft at a time to confirm which is which
3. Confirm `SERIAL2_PROTOCOL = 2` on the FC
4. Lower baud rate to 9600 temporarily to test: change both FC param and MAVProxy `--baudrate=9600`
5. Check if another process is using the serial port: `lsof /dev/ttyUSB0`

---

## Quad drifts significantly during hover

A 1–3m drift is normal. More than that:

1. **Compass interference** — redo compass calibration at your flying site, not indoors
2. **GPS HDOP too high** — wait for more satellites (8+ is good, 12+ is great)
3. **EKF not settled** — wait 2 min after GPS fix before invoking
4. **Prop balance** — an unbalanced prop causes vibration which confuses the IMU
5. **Reduce speed** — set `WPNAV_SPEED = 200` (2 m/s) for very stable hover

---

## Fixed-wing won't hold loiter orbit

1. Check `WP_LOITER_RAD = 50` is set
2. Increase orbit radius if it's fighting the wind: set to 70 or 80m
3. Check `CRUISE_SPEED` is realistic for your airframe
4. Verify GPS has 3D fix before uploading mission
5. Confirm the LOITER_UNLIM waypoint was actually uploaded:
   - In QGroundControl, go to Plan view and check the active mission

---

## Invoke command doesn't reach the Pi

**Test step by step:**

```bash
# Step 1: Is the server running?
systemctl status aegis

# Step 2: Can you reach it from the same WiFi?
curl http://192.168.x.x:5000/status

# Step 3: Does the Pi have internet?
curl ifconfig.me

# Step 4: Is DuckDNS updating?
cat ~/duckdns/duck.log

# Step 5: Can you reach it over 4G from your phone?
# Open phone browser → http://YOUR-DOMAIN.duckdns.org:5000

# Step 6: Is the firewall blocking port 5000?
sudo ufw status
sudo ufw allow 5000
```

---

## Fixed-wing goes into wrong mode after invoke

The FW must already be airborne when the invoke command arrives.

1. Hand-launch first
2. Wait for it to stabilise in FBWA or MANUAL
3. Then tap INVOKE

If the FW receives AUTO mode while still on the ground, it won't take off — it will try to navigate on the ground. If this happens, take manual control (switch RC transmitter to MANUAL), then re-invoke once it's airborne.

---

## One vehicle connects but the other doesn't

1. Check `/dev/ttyUSB0` and `/dev/ttyUSB1` are assigned to the right aircraft
   ```bash
   # Unplug one radio, run:
   ls /dev/ttyUSB*
   # Note which port disappeared — that radio was that port
   ```

2. Edit `/etc/systemd/system/aegis.service` or `config.py` to swap the port assignments

3. If both radios are on the same Net ID, they interfere with each other — change one pair's Net ID

---

## Aircraft returns to wrong home point

The home point is set automatically when the aircraft gets its first 3D GPS fix after arming. If you:
- Move the aircraft before it gets a GPS fix
- Power it up indoors

...the home point will be wrong.

**Fix:** Always power up outdoors, let it get a GPS fix (watch the LED or check Mission Planner), then arm. Never move a powered aircraft before it has GPS lock.

---

## Battery voltage reads wrong

1. Check the BATT_VOLT_MULT parameter matches your voltage divider ratio
2. If not using a voltage divider, set `BATT_MONITOR = 3` (voltage only, no current)
3. Calibrate by measuring actual LiPo voltage with a multimeter and comparing to Mission Planner readout, then adjusting BATT_VOLT_MULT

---

## Mission Planner can't connect over SiK radio

1. Set baud rate to 57600 in the Mission Planner connection dialog
2. Select the correct COM port
3. The SiK ground radio must be plugged into your laptop directly (not the Pi) for direct Mission Planner access
4. If Pi is relaying via MAVProxy, connect Mission Planner to the Pi's UDP output:
   ```bash
   # On Pi:
   mavproxy.py --master=/dev/ttyUSB0 --baudrate=57600 --out=udp:0.0.0.0:14550
   # In Mission Planner: UDP → port 14550
   ```

---

## LiPo battery is puffy (swollen)

**Do not fly this battery. Do not charge it.**

1. Fully discharge it using a battery discharger or in salt water (outdoors)
2. Place in a LiPo disposal bag
3. Take to a battery recycling point

A puffy LiPo can catch fire when charged or during flight.

---

## Prop strike — aircraft hit something

1. Land immediately, disarm
2. Inspect every prop — replace any with chips, cracks, or bends
3. Inspect motors — check for bent shafts (spin by hand, should be smooth)
4. Inspect arms — check for cracks, especially near motor mounts
5. Check all wiring — a hard impact can loosen connectors
6. Do not fly again until everything is inspected and clear

---

## Getting help

- **ArduPilot forums:** https://discuss.ardupilot.org/ — very active, huge community
- **Mission Planner docs:** https://ardupilot.org/planner/
- **DroneKit Python docs:** https://dronekit.io/
- **Matek H743 docs:** http://www.mateksys.com/?portfolio=h743-slim
- **Open an issue on this repo** with your Mission Planner logs attached
