# FAQ & Contributing

## Frequently Asked Questions

### "Do I need coding experience?"

Minimal. The only code you write is installing the pre-written Python server on the Raspberry Pi and running it. If you can copy-paste commands into a terminal and edit a text file, you have enough skill. The aircraft fly themselves.

### "Can I use WiFi instead of SiK radio for the drone link?"

Technically yes, but don't. WiFi at 2.4 GHz drops off rapidly with distance and obstacles. SiK at 915 MHz reliably reaches 1–2 km and is designed specifically for MAVLink. The $15 cost difference is not worth the reliability tradeoff.

### "Can I use Bluetooth to talk to the drones?"

No. Bluetooth max range is 30–100m in open air under ideal conditions. Useless for this application.

### "Do I need a Jetson Nano or any AI chip?"

No. ArduPilot on the STM32H7 handles all navigation entirely. It is mature, battle-tested software that has flown millions of missions. The Raspberry Pi only routes commands — a Pi Zero 2W would work if you want to save $30.

### "Can I add obstacle avoidance later?"

Yes, and ArduPilot supports it natively. Options from cheapest to best:
1. **Ultrasonic sonar** (~$10): basic forward avoidance, limited range
2. **Benewake TF-Mini LiDAR** (~$50): 12m range, single direction  
3. **Benewake TF-Luna ×5** (~$150): 360° coverage with 5 sensors
4. **RPLidar A1** (~$100): full 2D scan, best but needs mounting

None of these require changing the ground station code — they plug into the FC and ArduPilot handles the avoidance logic.

### "Can I add more drones?"

Yes. For each additional aircraft:
1. Get another SiK radio pair
2. Add it to `/dev/ttyUSBx`
3. Add a new vehicle connection in `mavlink_bridge.py`
4. Add the vehicle to the `invoke()` method

The Flask server and phone page don't need changes.

### "What is the maximum range?"

- **SiK radio link:** 1–2 km with stock antennas (upgrade to high-gain antennas for more)
- **4G invoke command:** unlimited — wherever cell coverage exists
- **Practical limit:** visual line of sight, roughly 400–600m in good conditions

You are legally required in most countries to maintain VLOS (visual line of sight) with your aircraft.

### "What if my phone GPS is inaccurate?"

Phone GPS is typically ±3–10m outdoors in open sky. That is acceptable for this system — the hover waypoint doesn't need to be millimetre-accurate. If you want better precision, you can pair a dedicated Bluetooth GPS receiver to your phone (e.g. a Bad Elf or Garmin GLO2) which provides WAAS-corrected accuracy of ~1–2m.

### "Can the fixed-wing auto-land?"

ArduPlane supports automatic landing via a LAND waypoint in a mission. However, it requires careful tuning of:
- `LAND_FLARE_ALT` — altitude to begin flare
- `LAND_FLARE_SEC` — time before landing to flare
- `TECS_LAND_SINK` — sink rate during approach
- A clear, unobstructed approach path aligned with the wind

For a first build, manual landing using the RC transmitter is strongly recommended. Once you are comfortable with the aircraft's handling in FBWA mode, you can experiment with auto-landing.

### "How long does the battery last?"

| Aircraft | Battery | Estimated flight time |
|----------|---------|----------------------|
| F450 quad | 3S 2200 mAh | 12–15 minutes |
| F450 quad | 4S 3000 mAh | 18–22 minutes |
| SkyWalker X8 | 3S 4000 mAh | 40–50 minutes |
| SkyWalker X8 | 4S 5000 mAh | 55–70 minutes |

The fixed-wing has dramatically better endurance. This is intentional — it provides the persistent surveillance role while the quad holds position.

### "Is this legal?"

Drone regulations vary significantly by country. Common requirements:
- Register your drones (usually required if over 250g — both of these are well over 250g)
- Fly below maximum altitude (usually 120–150m AGL)
- Maintain visual line of sight
- Stay away from airports, controlled airspace, people, and sensitive infrastructure
- In some countries, you need a pilot licence for this class of aircraft

**Check your local aviation authority's rules before flying. It is your responsibility.**

### "Can I use a different flight controller?"

Yes, any ArduPilot-compatible FC works. The Matek H743 is recommended because it is reliable, affordable, and well-documented. Other options:
- **Pixhawk 6C** — the reference standard, more expensive (~$200)
- **Holybro Kakute H7** — cheaper, good for smaller builds  
- **Any Pixhawk-clone with STM32F7 or H7** — check ArduPilot hardware list

The wiring, parameters, and Python code are identical across all ArduPilot-compatible FCs.

### "Can I use QGroundControl instead of Mission Planner?"

Yes. QGroundControl (QGC) is actually better for mobile use and is cross-platform. Use it on your phone or laptop for:
- Live telemetry from both aircraft
- Flight mode switching
- Parameter editing
- Mission planning

Download at: https://qgroundcontrol.com/

To connect QGC to the Pi's MAVProxy relay:
```bash
# On the Pi, add --out flag:
mavproxy.py --master=/dev/ttyUSB0 --baudrate=57600 --out=udp:0.0.0.0:14550

# In QGC: Application Settings → Comm Links → Add → UDP → Port 14550
```

---

## Contributing

Contributions are welcome. If you build this system, please share your experience.

### How to contribute

1. Fork the repo
2. Create a branch: `git checkout -b my-improvement`
3. Make your changes
4. Open a pull request with a description of what you changed and why

### What we need

- **Build logs** — photos and notes from your own build in `/community-builds/`
- **Parameter tuning** — if you found better parameters for a specific airframe, share them in `/firmware/`
- **Alternative airframes** — parameter files and notes for airframes other than F450 + SkyWalker X8
- **Bug fixes** — especially in `mavlink_bridge.py`
- **Translations** — README and docs in other languages
- **Video walkthroughs** — link them in the README

### Reporting issues

Open an issue and include:
- Which step in the build guide failed
- Your hardware (FC model, GPS, radio)
- Any error messages from Mission Planner or the terminal
- Your Mission Planner log file if relevant (`.bin` from the SD card)

### Code style

- Python: PEP8, 4-space indents, type hints where useful
- Comments explaining *why*, not *what*
- Keep `invoke_server.py` simple — it should stay under 100 lines
- All configurable values belong in `config.py`, not hardcoded

---

## License

MIT License

Copyright (c) 2025 AEGIS Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND. The authors accept no liability for damage to property, injury, or legal consequences arising from the use of this software. **You are solely responsible for operating your aircraft safely and legally.**
