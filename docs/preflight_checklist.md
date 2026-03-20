# AEGIS Pre-Flight Checklist

Print this out or save it on your phone. Run it every single flight.

---

## Before You Leave Home

- [ ] Both LiPo batteries charged to full (12.6V on a 3S)
- [ ] LiPo charger confirmed off and unplugged
- [ ] Both aircraft visually inspected — no cracks in frame or airframe
- [ ] All props tight and undamaged (run your finger along each blade)
- [ ] All wiring secure, no loose connectors
- [ ] RC transmitter fully charged
- [ ] Phone charged
- [ ] SD card in Raspberry Pi

---

## At the Flying Site — Ground Station Setup

- [ ] Place Raspberry Pi box on flat stable surface
- [ ] Plug in power bank
- [ ] Connect both SiK radios via USB
- [ ] SSH into Pi and start invoke server: `sudo systemctl start aegis`
- [ ] Confirm 4G internet: run `curl ifconfig.me` — should return your public IP
- [ ] Open invoke page on phone: `http://YOUR-DOMAIN.duckdns.org:5000`
- [ ] Confirm page loads and status shows "Waiting for GPS"

---

## Quadcopter Pre-Flight

- [ ] Place quad on flat ground, pointed away from people
- [ ] Plug in LiPo — wait 10 seconds for FC to boot
- [ ] Listen for 3 ESC beeps = FC ready
- [ ] SiK radio LED on aircraft goes **solid green** = radio link established
- [ ] In invoke page: Quad shows **ONLINE**
- [ ] GPS fix shows **3D Fix, 8+ satellites** (wait up to 90 seconds)
- [ ] Battery voltage shows **> 12.0V**
- [ ] No red warnings in QGroundControl / Mission Planner
- [ ] Mode shows **STABILIZE** (not armed yet — that is correct)
- [ ] RC transmitter on and bound — confirm quad responds to stick inputs in STABILIZE

---

## Fixed-Wing Pre-Flight

- [ ] Check control surfaces: move stick → correct surface moves correctly
  - Pitch stick up → elevons deflect down (pushes nose back up)
  - Roll stick right → right elevon up, left elevon down
- [ ] Prop is secured and correct orientation (pusher = spinning pulls air backward)
- [ ] No obstructions on the airframe
- [ ] Plug in LiPo
- [ ] SiK radio LED goes solid green = link established
- [ ] In invoke page: FW shows **ONLINE**
- [ ] GPS fix: **3D Fix, 8+ satellites**
- [ ] Battery shows **> 12.0V**
- [ ] Mode shows **MANUAL** or **FBWA**

---

## Environmental Check

- [ ] Wind: under 20 km/h (if leaves on trees are barely moving, you are fine)
- [ ] No rain or imminent weather
- [ ] Clear line of sight to the airspace where you plan to fly
- [ ] No people, animals, or vehicles in the immediate flight path
- [ ] You are in a legal flying location (check local rules)
- [ ] No NOTAMs (Notices to Airmen) active for your area

---

## Invoke Readiness Check

- [ ] You are standing at the location where you want the escort
- [ ] Phone GPS shows accuracy **< 10m** (watch the GPS card on the invoke page)
- [ ] Both vehicles show ONLINE on invoke page
- [ ] RC transmitter in hand and ready

---

## Invoke Sequence

1. [ ] Hand-launch the fixed-wing (firm level throw into the wind)
2. [ ] Confirm FW mode switches to AUTO in invoke page
3. [ ] Tap **INVOKE AEGIS**
4. [ ] Quad arms and lifts off automatically
5. [ ] Confirm both aircraft are flying and heading toward your position

---

## During Flight — Stay Alert

- [ ] Keep both aircraft in visual line of sight at all times
- [ ] RC transmitter in hand — be ready to take manual control
- [ ] Watch battery levels on invoke page
- [ ] Watch the sky for other aircraft

---

## Recovery

**Normal RTL (triggered by battery or you):**
- [ ] Quad will fly back and land automatically
- [ ] Switch FW to FBWA and fly it down manually, OR wait for it to loiter over home then land

**Emergency:**
- [ ] Tap ABORT on the invoke page — sends RTL to both aircraft immediately
- [ ] OR flip RC transmitter flight mode switch to RTL / STABILIZE

---

## Post-Flight

- [ ] Power off quad — disconnect LiPo immediately after landing
- [ ] Power off FW — disconnect LiPo
- [ ] Check all props for damage
- [ ] Check all wires still connected
- [ ] Charge LiPo to **storage voltage** (11.1V on 3S) if not flying within 48 hours
- [ ] Review flight log in Mission Planner: Ctrl+F → Flight Data → load .bin log
- [ ] Note any anomalies for next flight

---

## Battery Care

| State | Voltage (3S) | Action |
|-------|-------------|--------|
| Full charge | 12.6V | Use within 1 hour or discharge to storage |
| Storage | 11.1V (3.7V/cell) | Safe to leave for weeks |
| Low warning | 10.5V | RTL triggered |
| Critical | 9.9V | Land immediately |
| Never discharge below | 9.0V | Cell damage point |

**Never leave a fully charged LiPo unattended or overnight.**
**Never charge a puffy (swollen) LiPo — dispose of it safely.**
