"""
AEGIS Configuration
-------------------
All tunable settings in one place.
Edit this file before running invoke_server.py.
"""

import os

# ------------------------------------------------------------------
# Serial ports
# ------------------------------------------------------------------
# Run `ls /dev/ttyUSB*` on the Pi to see available ports.
# Power up one aircraft at a time to confirm which port is which.

QUAD_PORT   = os.getenv("AEGIS_QUAD_PORT",  "/dev/ttyUSB0")
QUAD_BAUD   = int(os.getenv("AEGIS_QUAD_BAUD", "57600"))

FW_PORT     = os.getenv("AEGIS_FW_PORT",    "/dev/ttyUSB1")
FW_BAUD     = int(os.getenv("AEGIS_FW_BAUD",   "57600"))

# ------------------------------------------------------------------
# Flight parameters
# ------------------------------------------------------------------

# Altitude the quadcopter hovers at above the user's GPS coordinate (metres)
QUAD_ALT    = int(os.getenv("AEGIS_QUAD_ALT", "15"))

# Altitude the fixed-wing loiters at above the user's GPS coordinate (metres)
FW_ALT      = int(os.getenv("AEGIS_FW_ALT", "30"))

# Radius of the fixed-wing loiter orbit (metres)
# Smaller = tighter circle, but harder to fly in wind
FW_RADIUS   = int(os.getenv("AEGIS_FW_RADIUS", "50"))

# ------------------------------------------------------------------
# Connection settings
# ------------------------------------------------------------------

# How long to wait for each vehicle to respond on connect (seconds)
CONNECT_TIMEOUT = int(os.getenv("AEGIS_CONNECT_TIMEOUT", "30"))

# How long to wait for arming to complete (seconds)
ARM_TIMEOUT     = int(os.getenv("AEGIS_ARM_TIMEOUT", "15"))

# ------------------------------------------------------------------
# Server settings
# ------------------------------------------------------------------

SERVER_PORT = int(os.getenv("AEGIS_PORT", "5000"))

# Path to the web folder containing index.html
WEB_DIR = os.path.join(os.path.dirname(__file__), "web")

# ------------------------------------------------------------------
# Optional: print config on import (useful for debugging)
# ------------------------------------------------------------------
if __name__ == "__main__":
    print("AEGIS configuration:")
    print(f"  Quad:       {QUAD_PORT} @ {QUAD_BAUD} baud")
    print(f"  Fixed-wing: {FW_PORT} @ {FW_BAUD} baud")
    print(f"  Quad alt:   {QUAD_ALT}m")
    print(f"  FW alt:     {FW_ALT}m  radius={FW_RADIUS}m")
    print(f"  Server:     port {SERVER_PORT}")
