# AEGIS Quick Start

Already have experience with ArduPilot? Start here.

## Prerequisites

- Both FCs flashed with ArduCopter / ArduPlane
- Both aircraft calibrated (compass, accel, radio)
- SiK radios wired to FCs and paired (Net ID 25 for quad, 26 for FW)

---

## 1. Load Parameters (2 minutes)

```
Mission Planner → Config → Full Parameter List → Load from file

Quad: firmware/quad/params.param
FW:   firmware/fixedwing/params.param
```

Reboot both FCs.

---

## 2. Set Up Raspberry Pi (10 minutes)

```bash
# Install dependencies
sudo apt update && sudo apt install python3-pip screen -y
pip3 install dronekit flask pymavlink

# Clone repo
git clone https://github.com/YOUR_USERNAME/aegis.git
cd aegis/ground_station

# Configure serial ports (check with: ls /dev/ttyUSB*)
nano config.py   # set QUAD_PORT and FW_PORT

# Install service (auto-starts on boot)
sudo cp ../scripts/aegis.service /etc/systemd/system/
sudo systemctl enable aegis
sudo systemctl start aegis

# Check it's running
sudo systemctl status aegis
```

---

## 3. Set Up DuckDNS (5 minutes)

1. Go to https://duckdns.org, create free account
2. Create a subdomain (e.g. `my-aegis.duckdns.org`)
3. On the Pi:
   ```bash
   mkdir ~/duckdns && cd ~/duckdns
   # Replace DOMAIN and TOKEN with yours:
   echo 'echo url="https://www.duckdns.org/update?domains=DOMAIN&token=TOKEN&ip=" | curl -k -o ~/duckdns/duck.log -K -' > duck.sh
   chmod +x duck.sh && ./duck.sh  # test it
   crontab -e
   # Add: */5 * * * * ~/duckdns/duck.sh >/dev/null 2>&1
   ```

---

## 4. Test on the Bench

```bash
# Power up quad (no props)
# Watch for heartbeat:
curl http://localhost:5000/status

# Should return JSON with both vehicles connected

# Send a test invoke (use your actual coordinates):
curl -X POST http://localhost:5000/invoke \
  -H "Content-Type: application/json" \
  -d '{"lat": 33.5731, "lon": -7.5898, "alt": 15}'

# Watch Mission Planner — quad should switch to GUIDED mode
# (No arming on bench — that requires GPS fix)
```

---

## 5. First Flight

1. Fly to a clear open area
2. Power on ground station, power on both aircraft
3. Wait for GPS lock (both aircraft, 8+ satellites)
4. Open `http://YOUR-DOMAIN.duckdns.org:5000` on your phone
5. Hand-launch the fixed-wing
6. Stand at your target position
7. Confirm GPS accuracy < 10m on phone
8. Tap **INVOKE AEGIS**
9. Quad arms and lifts off automatically
10. Both aircraft navigate to your position

---

## File Layout

```
aegis/
├── README.md                      ← Full documentation
├── docs/
│   ├── wiring.md                  ← All wiring diagrams
│   ├── preflight_checklist.md     ← Print and use every flight
│   ├── troubleshooting.md         ← When things go wrong
│   └── faq_and_contributing.md    ← Common questions
├── firmware/
│   ├── quad/params.param          ← Load into quad FC
│   └── fixedwing/params.param     ← Load into FW FC
├── ground_station/
│   ├── invoke_server.py           ← Main server (run this)
│   ├── mavlink_bridge.py          ← DroneKit vehicle logic
│   ├── config.py                  ← All settings here
│   ├── requirements.txt           ← pip install -r this
│   └── web/index.html             ← Phone invoke page
└── scripts/
    └── aegis.service              ← Systemd auto-start
```
