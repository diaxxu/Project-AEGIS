# AEGIS Wiring Reference

## SiK Radio → Flight Controller (both aircraft, identical wiring)

```
SiK Radio 6-pin JST    Matek H743 FC
─────────────────────────────────────
Pin 1: GND          →  GND
Pin 2: 5V           →  5V output (from BEC or FC 5V rail)
Pin 3: TXD          →  UART2 RX  ← CROSS these
Pin 4: RXD          →  UART2 TX  ← CROSS these
Pin 5: CTS          →  (leave unconnected)
Pin 6: RTS          →  (leave unconnected)
```

> IMPORTANT: TX of the radio connects to RX of the FC.
> RX of the radio connects to TX of the FC.
> If you don't cross them, there is no communication.

## M8N GPS → Flight Controller (both aircraft, identical wiring)

```
M8N GPS module         Matek H743 FC
──────────────────────────────────────
GND                 →  GND
5V                  →  5V
TX (GPS serial out) →  GPS1 RX (UART1)
RX (GPS serial in)  →  GPS1 TX (UART1)
SDA (compass I2C)   →  I2C1 SDA
SCL (compass I2C)   →  I2C1 SCL
```

Set in ArduPilot:
- SERIAL3_PROTOCOL = 5 (GPS)
- SERIAL3_BAUD = 38 (38400 baud, default for M8N)

## Quadcopter — ESC → Motor → FC

```
4-in-1 ESC        Matek H743-Slim FC
────────────────────────────────────────
Signal M1       →  Output 1 (front-left CW)
Signal M2       →  Output 2 (front-right CCW)
Signal M3       →  Output 3 (rear-right CW)
Signal M4       →  Output 4 (rear-left CCW)
5V BEC          →  5V power input
GND             →  GND
```

Motor layout (top view, X frame):
```
    FRONT
  M1(CW)  M2(CCW)
     \      /
      \    /
       \  /
        \/  ← FC (arrow forward)
        /\
       /  \
      /    \
  M3(CCW) M4(CW)
    REAR
```

## Fixed-Wing — Servo / ESC → FC

```
SkyWalker X8 servos     Matek H743-Wing FC
───────────────────────────────────────────
Left elevon servo    →  Output 1
Right elevon servo   →  Output 2
ESC signal           →  Output 3 (throttle)
```

Elevon mixing is handled in ArduPlane (ELEVON_OUTPUT=4).
Do NOT mix manually in your transmitter.

## RC Receiver → Flight Controller

```
RC Receiver (FS-iA6B)   Matek H743 FC
────────────────────────────────────────────
SBUS out             →  SBUS input pin on FC
5V                   →  (powered by FC 5V rail)
GND                  →  GND
```

Enable SBUS in ArduPilot:
- SERIAL7_PROTOCOL = 23 (RCIN)
Or use the dedicated RC input pin on the Matek.

## Power Distribution (Quadcopter)

```
3S LiPo (11.1V)
     │
     ├──► 4-in-1 ESC (main power)
     │         │
     │         ├──► Motor 1
     │         ├──► Motor 2
     │         ├──► Motor 3
     │         └──► Motor 4
     │         │
     │         └──► 5V BEC ──► Matek FC 5V input
     │                              │
     │                              ├──► SiK radio (5V)
     │                              └──► RC receiver (5V)
     │
     └──► Voltage divider ──► FC ADC pin (battery monitoring)
```

## Power Distribution (Fixed-Wing)

```
3S LiPo (11.1V)
     │
     ├──► ESC (motor power + 5V BEC output)
     │         │
     │         └──► 5V BEC ──► Matek H743-Wing 5V input
     │                              │
     │                              ├──► SiK radio (5V)
     │                              ├──► Left servo
     │                              └──► Right servo
     │
     └──► Voltage divider ──► FC ADC pin
```

## Ground Station Wiring

```
Power Bank (5V USB)
     │
     └──► Raspberry Pi 4 (USB-C power)
               │
               ├──► USB port 1 ──► SiK Radio (quad link)   /dev/ttyUSB0
               ├──► USB port 2 ──► SiK Radio (FW link)     /dev/ttyUSB1
               └──► USB port 3 ──► 4G dongle               usb0 / eth1
```

## Voltage Divider for Battery Monitoring (optional but recommended)

Connect to FC ADC pin to get battery voltage readings in Mission Planner.

```
LiPo +  ──── 10kΩ ──── ADC pin
                  │
                 47kΩ
                  │
                 GND
```

Voltage divider ratio = 47 / (10 + 47) = 0.825
Set in ArduPilot: BATT_VOLT_MULT = 1 / 0.825 = 1.21

## Notes

- All grounds must be common. Connect ESC GND to FC GND.
- Use heat shrink on all solder joints.
- Route all signal wires away from power wires to reduce noise.
- Keep the GPS mast as high as possible and away from the FC and ESCs.
- SiK radio antenna should point straight up for best horizontal range.
