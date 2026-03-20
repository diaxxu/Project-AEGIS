# Centre of Gravity Guide — SkyWalker X8

This is the single most important thing to get right on a flying wing.
A quad with wrong CG just flies poorly. A flying wing with wrong CG will crash
on its first throw.

---

## What CG Is and Why It Matters

The Centre of Gravity (CG) is the point where the aircraft balances horizontally.
On a flying wing with no tail, the CG position completely controls pitch stability.

```
Too far FORWARD            Correct CG             Too far BACK
(nose heavy)                                        (tail heavy)

     ↓ nose dips                                      ↑ pitches up
Hard to fly, needs         Stable, self-corrects   UNSTABLE — will
 lots of up elevator.       minor disturbances.    flip and crash on
 Slow and draggy.          ArduPlane can hold it.  launch. Dangerous.
```

**"When in doubt, go slightly nose-heavy."**
A nose-heavy aircraft is hard to fly. A tail-heavy aircraft crashes.

---

## SkyWalker X8 Recommended CG Location

The X8 1880mm has a swept wing with a known stable CG range.

```
                    NOSE ──────────────────────── TAIL
                      │                               │
                      │◄──────── ~980mm ─────────────►│
                      │         (root chord)           │

CG range:    ◄──────────────────►
             32% to 36% of root chord from leading edge

  Leading edge of wing root ──► measure 315mm to 350mm back

  IDEAL for first flights: 320–330mm from leading edge at wing root
```

### How to find and mark the CG point

1. Lay the X8 flat on a table
2. Find where the wing meets the fuselage — this is the **wing root**
3. Find the **leading edge** of the wing at the root — the front-most point
4. Measure straight back along the wing surface: **320mm**
5. Mark this point with a small piece of tape on the top of the wing
6. Mark the same point on both sides of the fuselage

This mark is your target CG.

---

## How to Check CG

### Method 1 — Two-finger balance test

1. Hold the aircraft upside down
2. Place one fingertip under each wing, at the CG mark position
3. Let go gently — the aircraft should hang level or very slightly nose-low
4. If the nose drops sharply: too nose-heavy — move battery back
5. If the tail drops: too tail-heavy — move battery forward IMMEDIATELY

### Method 2 — Balance stand

Rest both wing tips on the edges of two cups or blocks of equal height.
The aircraft should sit level or just slightly nose-low when balanced at the CG mark.

---

## Where the Battery Goes in the X8

The X8 fuselage has a large internal bay. Battery position is your main CG adjustment tool.

```
FUSELAGE CROSS-SECTION (top view, nose at left):

  NOSE ──[Battery bay]──────────────────[Motor]── TAIL
          ↑
          Battery slides forward/back here

  Forward battery = nose-heavy (more stable, slower)
  Rear battery    = tail-heavy (DANGER — do not do this)
```

### Starting battery position for a 3S 4000mAh

1. Place the battery in the bay, roughly centered
2. Check the CG with the two-finger test
3. If too nose-heavy (nose dips), slide battery slightly back (1–2cm)
4. If tail-heavy (any tail drop), slide battery forward immediately
5. Repeat until the aircraft hangs level or slightly nose-low
6. Secure the battery with velcro straps when position is confirmed

> The battery is heavy. A 2cm shift forward or backward makes a noticeable difference to CG.

---

## CG With Different Battery Sizes

| Battery | Approx weight | Typical position |
|---------|--------------|-----------------|
| 3S 2200mAh | 180g | Closer to nose |
| 3S 4000mAh | 290g | ~40mm from nose of bay |
| 4S 4000mAh | 310g | ~35mm from nose of bay |
| 4S 5000mAh | 380g | ~25mm from nose of bay |

These are starting points only. **Always verify with the two-finger test with your actual battery.**

---

## Adding Nose Weight (if needed)

If you cannot move the battery far enough forward to reach the CG point, add nose weight:

1. Use small fishing weights or steel washers
2. Tape them temporarily inside the nose cone first — check CG
3. When you have the right amount, glue them in permanently with CA glue + baking soda

Start with 20g and work up. Most X8 builds with a rear-mounted motor and correctly-sized battery do not need added nose weight.

---

## Incidence Angle Check

While you have the aircraft on the bench, also check the wing incidence angle.
The X8 wing should sit at approximately 2–3° positive incidence (leading edge slightly higher than trailing edge when the fuselage is level).

Check this with a simple incidence meter or a phone spirit level app:
1. Level the fuselage (sit it on its belly with nose pointing forward)
2. Place the phone flat on the wing surface
3. Read the angle — should be 2–3° positive
4. If it is 0° or negative, the wing may need shimming at the root

An incorrect incidence angle causes ArduPlane to use constant elevator to maintain level flight, which drains battery and increases stall risk.

---

## CG Checklist — Do This Before Every First Flight of a New Battery

```
□ Aircraft empty (no battery) — does it balance far nose-heavy? (good)
□ Insert battery in starting position
□ Two-finger test — nose slightly down or level? (good)
□ Tail does NOT drop? (absolutely critical — if tail drops, move battery forward)
□ Mark final battery position on the velcro with a pen
□ Secure battery strap firmly — it must not move during flight
□ Re-check CG after securing strap (straps can shift things slightly)
```

---

## What Happens If You Get It Wrong

**Slightly nose-heavy (safe):**
ArduPlane will compensate with slight up-elevator. The plane will be docile and forgiving. First flights are fine here.

**Correct:**
The plane self-stabilises with minimal elevator input. Best performance and efficiency.

**Slightly tail-heavy (risky):**
The plane will want to climb and may be twitchy. In FBWA mode ArduPlane can just about manage it. Do not let it get to this point.

**Tail-heavy (dangerous):**
The plane will pitch up violently on launch, stall, and tumble. There is no software fix for this. Move the battery forward before the first throw.

---

## The Throw

Once CG is confirmed correct, the launch technique:

1. Set mode to FBWA (fly-by-wire A) on your RC transmitter
2. Arm the aircraft (motor will run at low idle — keep hands clear of prop)
3. Hold the aircraft by the fuselage, wings level, nose pointing into wind
4. Throw it firmly and level — like throwing a javelin, not a dart
5. Release with a clean horizontal motion
6. Do not throw it upward — a nose-up throw stalls it immediately
7. ArduPlane will take over as soon as you release

If the CG is correct and the throw is level, the X8 will climb out smoothly and start flying on its own.
