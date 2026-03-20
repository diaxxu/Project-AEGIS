"""
AEGIS MAVLink Bridge
--------------------
Manages DroneKit connections to the quadcopter and fixed-wing.
Handles arming, mode switching, and mission uploading.
"""

import time
import logging
from dronekit import connect, VehicleMode, LocationGlobalRelative, Command
from pymavlink import mavutil
from config import (
    QUAD_PORT, QUAD_BAUD,
    FW_PORT, FW_BAUD,
    QUAD_ALT, FW_ALT, FW_RADIUS,
    CONNECT_TIMEOUT, ARM_TIMEOUT,
)

log = logging.getLogger("aegis")


class AegisBridge:
    """
    Manages both vehicles and exposes high-level commands.
    """

    def __init__(self):
        self.quad = None
        self.fw = None
        self._connected = False

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self):
        """
        Connect to both vehicles over their SiK radio serial ports.
        Blocks until both are connected or raises on timeout.
        """
        log.info(f"Connecting to quad on {QUAD_PORT} @ {QUAD_BAUD} baud...")
        try:
            self.quad = connect(
                QUAD_PORT,
                baud=QUAD_BAUD,
                wait_ready=True,
                timeout=CONNECT_TIMEOUT,
            )
            log.info(f"Quad connected. Mode: {self.quad.mode.name}  "
                     f"GPS: {self.quad.gps_0.fix_type}  "
                     f"Battery: {self.quad.battery.voltage:.1f}V")
        except Exception as e:
            log.error(f"Failed to connect to quad: {e}")
            raise

        log.info(f"Connecting to fixed-wing on {FW_PORT} @ {FW_BAUD} baud...")
        try:
            self.fw = connect(
                FW_PORT,
                baud=FW_BAUD,
                wait_ready=True,
                timeout=CONNECT_TIMEOUT,
            )
            log.info(f"Fixed-wing connected. Mode: {self.fw.mode.name}  "
                     f"GPS: {self.fw.gps_0.fix_type}  "
                     f"Battery: {self.fw.battery.voltage:.1f}V")
        except Exception as e:
            log.error(f"Failed to connect to fixed-wing: {e}")
            raise

        self._connected = True
        log.info("Both vehicles connected. AEGIS ready.")

    # ------------------------------------------------------------------
    # Main invoke sequence
    # ------------------------------------------------------------------

    def invoke(self, lat: float, lon: float, alt: float = None):
        """
        Full invoke sequence:
        1. Send quad to GUIDED mode → arm → fly to coordinate → hover
        2. Upload loiter mission to fixed-wing → set AUTO mode

        lat, lon: target GPS coordinate (user's position)
        alt:      override altitude (None = use config defaults)
        """
        if not self._connected:
            log.error("Cannot invoke — vehicles not connected")
            return

        quad_alt = alt if alt is not None else QUAD_ALT
        fw_alt   = alt if alt is not None else FW_ALT
        # FW always flies higher than quad
        if fw_alt <= quad_alt:
            fw_alt = quad_alt + 15

        log.info(f"INVOKE: target ({lat:.6f}, {lon:.6f})  "
                 f"quad@{quad_alt}m  fw@{fw_alt}m radius={FW_RADIUS}m")

        # Run both in parallel
        import threading
        t1 = threading.Thread(
            target=self._invoke_quad, args=(lat, lon, quad_alt), daemon=True
        )
        t2 = threading.Thread(
            target=self._invoke_fw, args=(lat, lon, fw_alt), daemon=True
        )
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        log.info("Invoke sequence complete. Both vehicles on mission.")

    def _invoke_quad(self, lat: float, lon: float, alt: float):
        """
        Send the quadcopter to a GPS coordinate and hover there.
        Uses ArduCopter GUIDED mode.
        """
        v = self.quad
        log.info(f"[QUAD] Switching to GUIDED mode...")
        v.mode = VehicleMode("GUIDED")
        _wait_for_mode(v, "GUIDED")

        # Pre-arm check: GPS fix
        gps_fix = v.gps_0.fix_type
        if gps_fix < 3:
            log.error(f"[QUAD] GPS fix insufficient (type={gps_fix}). Need 3D fix.")
            return

        log.info(f"[QUAD] Arming motors...")
        v.armed = True
        _wait_for_armed(v, timeout=ARM_TIMEOUT)

        if not v.armed:
            log.error("[QUAD] Failed to arm. Check pre-arm failures in Mission Planner.")
            return

        log.info(f"[QUAD] Armed. Flying to ({lat:.6f}, {lon:.6f}) at {alt}m...")
        target = LocationGlobalRelative(lat, lon, alt)
        v.simple_goto(target)
        log.info(f"[QUAD] Waypoint sent. Quad is en route.")

    def _invoke_fw(self, lat: float, lon: float, alt: float):
        """
        Upload a loiter mission to the fixed-wing and activate AUTO mode.
        Uses ArduPlane NAV_LOITER_UNLIM — orbits indefinitely until new command.
        """
        v = self.fw
        log.info(f"[FW] Uploading loiter mission to ({lat:.6f}, {lon:.6f}) at {alt}m...")

        cmds = v.commands
        cmds.clear()

        # Command 0: Dummy waypoint (required by ArduPlane as mission start)
        # Uses current home location
        cmds.add(Command(
            0, 0, 0,
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
            mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
            0, 0,
            0, 0, 0, 0,  # params 1-4 (hold time, accept radius, pass radius, yaw)
            lat, lon, alt
        ))

        # Command 1: Loiter indefinitely at target coordinate
        # param3 = loiter radius in metres (positive = clockwise)
        cmds.add(Command(
            0, 0, 0,
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
            mavutil.mavlink.MAV_CMD_NAV_LOITER_UNLIM,
            0, 0,
            0,         # param1 — unused
            1,         # param2 — heading required (0 = no)
            FW_RADIUS, # param3 — orbit radius in metres
            0,         # param4 — xtrack location (1 = centre fix, 0 = entry point)
            lat, lon, alt
        ))

        cmds.upload()
        log.info(f"[FW] Mission uploaded ({len(cmds)} waypoints).")

        log.info(f"[FW] Switching to AUTO mode...")
        v.mode = VehicleMode("AUTO")
        _wait_for_mode(v, "AUTO")
        log.info(f"[FW] AUTO mode active. Fixed-wing will loiter when it reaches the WP.")

    # ------------------------------------------------------------------
    # Abort / RTL
    # ------------------------------------------------------------------

    def abort(self):
        """Send RTL to both vehicles immediately."""
        if self.quad:
            log.info("[QUAD] Sending RTL...")
            self.quad.mode = VehicleMode("RTL")
        if self.fw:
            log.info("[FW] Sending RTL...")
            self.fw.mode = VehicleMode("RTL")

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_status(self) -> dict:
        """Return a dict of current vehicle states for the status endpoint."""
        def vehicle_status(v, name):
            if v is None:
                return {"connected": False}
            try:
                return {
                    "connected": True,
                    "name": name,
                    "mode": v.mode.name,
                    "armed": v.armed,
                    "battery_voltage": round(v.battery.voltage or 0, 2),
                    "battery_level": v.battery.level,
                    "gps_fix": v.gps_0.fix_type,
                    "satellites": v.gps_0.satellites_visible,
                    "lat": v.location.global_frame.lat,
                    "lon": v.location.global_frame.lon,
                    "alt": round(v.location.global_relative_frame.alt or 0, 1),
                    "groundspeed": round(v.groundspeed or 0, 1),
                    "heading": v.heading,
                    "ekf_ok": v.ekf_ok,
                    "is_armable": v.is_armable,
                    "system_status": str(v.system_status.state),
                }
            except Exception as e:
                return {"connected": True, "error": str(e)}

        return {
            "quad": vehicle_status(self.quad, "Quadcopter"),
            "fw":   vehicle_status(self.fw,   "Fixed-Wing"),
        }

    def close(self):
        """Close vehicle connections cleanly."""
        if self.quad:
            self.quad.close()
        if self.fw:
            self.fw.close()
        log.info("Vehicle connections closed.")


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _wait_for_mode(vehicle, mode_name: str, timeout: float = 10.0):
    """Block until the vehicle's mode matches mode_name."""
    deadline = time.time() + timeout
    while vehicle.mode.name != mode_name:
        if time.time() > deadline:
            log.warning(f"Timeout waiting for mode {mode_name} "
                        f"(current: {vehicle.mode.name})")
            return
        time.sleep(0.2)
    log.info(f"Mode confirmed: {mode_name}")


def _wait_for_armed(vehicle, timeout: float = 15.0):
    """Block until the vehicle is armed."""
    deadline = time.time() + timeout
    while not vehicle.armed:
        if time.time() > deadline:
            log.warning("Timeout waiting for arming")
            return
        time.sleep(0.5)
    log.info("Vehicle armed.")
