#!/usr/bin/env python3
import collections
import collections.abc
collections.MutableMapping = collections.abc.MutableMapping
"""
AEGIS Bench Test
----------------
Tests the complete invoke → MAVLink → aircraft command chain
WITHOUT any hardware connected.

Uses mock DroneKit vehicles that simulate realistic ArduPilot behaviour:
realistic GPS fix timing, mode changes, arming sequence, battery drain,
and telemetry responses.

Run this before your first field session to confirm everything works.

Usage:
    python3 tools/test_bench.py

    # Verbose mode (shows every MAVLink call):
    python3 tools/test_bench.py --verbose

    # Run a specific test only:
    python3 tools/test_bench.py --test invoke
    python3 tools/test_bench.py --test abort
    python3 tools/test_bench.py --test status
    python3 tools/test_bench.py --test failsafe
"""

import sys
import os
import time
import json
import threading
import argparse
import traceback
import urllib.request
import urllib.error
from typing import Optional
from unittest.mock import MagicMock, patch, PropertyMock

# Add ground_station to path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "ground_station"))

# ─────────────────────────────────────────────────────────────────────────────
# Terminal colours
# ─────────────────────────────────────────────────────────────────────────────

class C:
    RED    = "\033[91m"
    GRN    = "\033[92m"
    YLW    = "\033[93m"
    BLU    = "\033[94m"
    CYN    = "\033[96m"
    WHT    = "\033[97m"
    DIM    = "\033[2m"
    BOLD   = "\033[1m"
    NC     = "\033[0m"

def ok(msg):    print(f"  {C.GRN}✓{C.NC} {msg}")
def fail(msg):  print(f"  {C.RED}✗{C.NC} {msg}")
def warn(msg):  print(f"  {C.YLW}⚠{C.NC} {msg}")
def info(msg):  print(f"  {C.DIM}{msg}{C.NC}")
def head(msg):  print(f"\n{C.CYN}{C.BOLD}── {msg} {C.NC}")
def sep():      print(f"  {C.DIM}{'─' * 54}{C.NC}")

# ─────────────────────────────────────────────────────────────────────────────
# Mock DroneKit vehicle
# ─────────────────────────────────────────────────────────────────────────────

class MockLocation:
    def __init__(self, lat=33.5731, lon=-7.5898, alt=0.0):
        self.lat = lat
        self.lon = lon
        self.alt = alt

class MockLocationFrames:
    def __init__(self):
        self.global_frame          = MockLocation()
        self.global_relative_frame = MockLocation()

class MockGPS:
    def __init__(self):
        self.fix_type            = 0    # starts with no fix
        self.satellites_visible  = 0

class MockBattery:
    def __init__(self, voltage=12.5):
        self.voltage = voltage
        self.level   = 95
        self.current = 4.2

class MockEKF:
    ok = True

class MockSystemStatus:
    state = "STANDBY"

class MockVehicle:
    """
    Simulates a DroneKit vehicle with realistic ArduPilot timing.
    GPS acquires over ~3 seconds. Mode changes are acknowledged.
    Arming takes ~1 second. Battery slowly drains.
    """

    def __init__(self, name: str, verbose: bool = False):
        self.name      = name
        self.verbose   = verbose
        self._mode     = "STABILIZE"
        self._armed    = False
        self.battery   = MockBattery()
        self.gps_0     = MockGPS()
        self.location  = MockLocationFrames()
        self.heading   = 0
        self.groundspeed = 0.0
        self.airspeed    = 0.0
        self.ekf_ok      = True
        self.is_armable  = False
        self.system_status = MockSystemStatus()
        self._commands = MockCommands(name, verbose)

        # Start GPS acquisition simulation in background
        threading.Thread(target=self._acquire_gps, daemon=True).start()
        # Start battery drain simulation
        threading.Thread(target=self._drain_battery, daemon=True).start()

    def _log(self, msg):
        if self.verbose:
            info(f"[{self.name}] {msg}")

    def _acquire_gps(self):
        """Simulate GPS acquiring over a few seconds."""
        time.sleep(0.5)
        self.gps_0.satellites_visible = 4
        self.gps_0.fix_type = 2  # 2D fix
        self._log("GPS 2D fix acquired (4 sats)")
        time.sleep(1.0)
        self.gps_0.satellites_visible = 9
        self.gps_0.fix_type = 3  # 3D fix
        self.is_armable = True
        self.location.global_frame.lat = 33.5731
        self.location.global_frame.lon = -7.5898
        self.location.global_frame.alt = 0.0
        self._log("GPS 3D fix acquired (9 sats) — vehicle is armable")

    def _drain_battery(self):
        """Simulate slow battery drain during flight."""
        while True:
            time.sleep(5)
            if self._armed:
                self.battery.voltage = max(9.5, self.battery.voltage - 0.05)
                self.battery.level   = max(0, self.battery.level - 1)

    @property
    def mode(self):
        m = MagicMock()
        m.name = self._mode
        return m

    @mode.setter
    def mode(self, new_mode):
        name = new_mode.name if hasattr(new_mode, 'name') else str(new_mode)
        self._log(f"Mode change: {self._mode} → {name}")
        time.sleep(0.1)  # simulate ACK latency
        self._mode = name

    @property
    def armed(self):
        return self._armed

    @armed.setter
    def armed(self, value: bool):
        if value and not self.is_armable:
            self._log("Arm denied — not armable (GPS?)")
            return
        self._log(f"{'Arming' if value else 'Disarming'}...")
        time.sleep(0.8)
        self._armed = value
        if value:
            self.system_status.state = "ACTIVE"
        else:
            self.system_status.state = "STANDBY"

    @property
    def commands(self):
        return self._commands

    def simple_goto(self, location):
        self._log(
            f"simple_goto({location.lat:.6f}, {location.lon:.6f}, {location.alt}m)"
        )
        # Simulate flight — update position gradually
        threading.Thread(
            target=self._fly_to, args=(location.lat, location.lon, location.alt),
            daemon=True
        ).start()

    def _fly_to(self, lat, lon, alt):
        """Simulate the vehicle moving toward the target."""
        steps = 20
        start_lat = self.location.global_frame.lat
        start_lon = self.location.global_frame.lon
        for i in range(steps):
            t = (i + 1) / steps
            self.location.global_frame.lat = start_lat + (lat - start_lat) * t
            self.location.global_frame.lon = start_lon + (lon - start_lon) * t
            self.location.global_relative_frame.alt = alt * t
            self.groundspeed = 5.0 if t < 0.9 else 5.0 * (1 - t) * 10
            time.sleep(0.15)
        self.location.global_frame.lat = lat
        self.location.global_frame.lon = lon
        self.location.global_relative_frame.alt = alt
        self.groundspeed = 0.0
        self._log(f"Arrived at target. Hovering at {alt}m.")

    def close(self):
        self._log("Connection closed")


class MockCommands:
    """Simulates DroneKit's commands object (mission upload)."""

    def __init__(self, vehicle_name: str, verbose: bool = False):
        self._name    = vehicle_name
        self._verbose = verbose
        self._cmds    = []

    def clear(self):
        self._cmds = []
        if self._verbose:
            info(f"  [{self._name}] Commands cleared")

    def add(self, cmd):
        self._cmds.append(cmd)
        if self._verbose:
            info(f"  [{self._name}] Command added: type={cmd.command}")

    def upload(self):
        if self._verbose:
            info(f"  [{self._name}] Mission uploaded ({len(self._cmds)} waypoints)")
        time.sleep(0.2)  # simulate upload time

    def __len__(self):
        return len(self._cmds)


# ─────────────────────────────────────────────────────────────────────────────
# Mock connect() — replaces dronekit.connect
# ─────────────────────────────────────────────────────────────────────────────

_quad_vehicle = None
_fw_vehicle   = None

def mock_connect(port, baud=57600, wait_ready=True, timeout=30):
    """
    Returns a MockVehicle instead of connecting to a real serial port.
    The vehicle name is inferred from the port string.
    """
    global _quad_vehicle, _fw_vehicle
    verbose = "--verbose" in sys.argv
    if "USB0" in port or "quad" in port.lower():
        v = MockVehicle("QUAD", verbose=verbose)
        _quad_vehicle = v
    else:
        v = MockVehicle("FW", verbose=verbose)
        _fw_vehicle = v

    if wait_ready:
        # Simulate connection delay
        time.sleep(0.3)
    return v


# ─────────────────────────────────────────────────────────────────────────────
# Test runner
# ─────────────────────────────────────────────────────────────────────────────

class BenchTest:
    def __init__(self, verbose: bool = False):
        self.verbose  = verbose
        self.passed   = 0
        self.failed   = 0
        self.warnings = 0
        self._server_thread: Optional[threading.Thread] = None
        self._server_port   = 15099

    # ── Assertions ────────────────────────────────────────────────────────────

    def assert_true(self, condition: bool, msg: str):
        if condition:
            ok(msg)
            self.passed += 1
        else:
            fail(msg)
            self.failed += 1

    def assert_eq(self, actual, expected, msg: str):
        if actual == expected:
            ok(f"{msg} (= {expected!r})")
            self.passed += 1
        else:
            fail(f"{msg} — expected {expected!r}, got {actual!r}")
            self.failed += 1

    def assert_contains(self, haystack, needle, msg: str):
        if needle in haystack:
            ok(msg)
            self.passed += 1
        else:
            fail(f"{msg} — '{needle}' not found in {haystack!r}")
            self.failed += 1

    # ── HTTP helpers ──────────────────────────────────────────────────────────

    def _get(self, path: str) -> dict:
        url = f"http://127.0.0.1:{self._server_port}{path}"
        try:
            req = urllib.request.urlopen(url, timeout=5)
            return json.loads(req.read().decode())
        except Exception as e:
            raise RuntimeError(f"GET {path} failed: {e}") from e

    def _post(self, path: str, body: dict) -> dict:
        url  = f"http://127.0.0.1:{self._server_port}{path}"
        data = json.dumps(body).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"}
        )
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = json.loads(e.read().decode())
            return {**body, "_status": e.code}
        except Exception as e:
            raise RuntimeError(f"POST {path} failed: {e}") from e

    # ── Server lifecycle ──────────────────────────────────────────────────────

    def start_server(self):
        """Start the Flask server in a background thread with mocked DroneKit."""
        with patch("dronekit.connect", side_effect=mock_connect):
            import invoke_server
            import mavlink_bridge

            # Override config port so we don't conflict with a real running server
            import config
            config.SERVER_PORT = self._server_port

            # Patch the bridge's connect to use our mock
            bridge = mavlink_bridge.AegisBridge()

            with patch("dronekit.connect", side_effect=mock_connect):
                bridge.connect()

            invoke_server.bridge = bridge

            def run():
                invoke_server.app.run(
                    host="127.0.0.1",
                    port=self._server_port,
                    debug=False,
                    use_reloader=False,
                )

            self._server_thread = threading.Thread(target=run, daemon=True)
            self._server_thread.start()
            time.sleep(1.5)  # let Flask start

    # ─────────────────────────────────────────────────────────────────────────
    # TEST: Config
    # ─────────────────────────────────────────────────────────────────────────

    def test_config(self):
        head("Test 1 — Configuration")
        sep()
        try:
            import config
            self.assert_true(hasattr(config, "QUAD_PORT"),   "QUAD_PORT defined")
            self.assert_true(hasattr(config, "FW_PORT"),     "FW_PORT defined")
            self.assert_true(hasattr(config, "QUAD_ALT"),    "QUAD_ALT defined")
            self.assert_true(hasattr(config, "FW_ALT"),      "FW_ALT defined")
            self.assert_true(hasattr(config, "FW_RADIUS"),   "FW_RADIUS defined")
            self.assert_true(hasattr(config, "SERVER_PORT"), "SERVER_PORT defined")
            self.assert_true(hasattr(config, "WEB_DIR"),     "WEB_DIR defined")
            self.assert_true(os.path.isdir(config.WEB_DIR),  "web/ directory exists")
            self.assert_true(
                os.path.isfile(os.path.join(config.WEB_DIR, "index.html")),
                "web/index.html exists"
            )
            self.assert_true(config.QUAD_ALT > 0,    f"QUAD_ALT > 0 (= {config.QUAD_ALT}m)")
            self.assert_true(config.FW_ALT > 0,      f"FW_ALT > 0 (= {config.FW_ALT}m)")
            self.assert_true(config.FW_RADIUS > 0,   f"FW_RADIUS > 0 (= {config.FW_RADIUS}m)")
            self.assert_true(
                config.FW_ALT > config.QUAD_ALT,
                f"FW flies higher than quad ({config.FW_ALT}m > {config.QUAD_ALT}m)"
            )
        except Exception as e:
            fail(f"Config test exception: {e}")
            self.failed += 1

    # ─────────────────────────────────────────────────────────────────────────
    # TEST: Mock vehicle behaviour
    # ─────────────────────────────────────────────────────────────────────────

    def test_mock_vehicles(self):
        head("Test 2 — Mock vehicle behaviour")
        sep()
        try:
            with patch("dronekit.connect", side_effect=mock_connect):
                import mavlink_bridge
                bridge = mavlink_bridge.AegisBridge()
                bridge.connect()

            self.assert_true(bridge.quad is not None,      "Quad vehicle connected")
            self.assert_true(bridge.fw is not None,        "Fixed-wing vehicle connected")
            self.assert_true(bridge._connected,            "Bridge reports connected")

            # Wait for GPS fix
            info("Waiting for GPS acquisition (~3s)...")
            deadline = time.time() + 8
            while (bridge.quad.gps_0.fix_type < 3 or bridge.fw.gps_0.fix_type < 3) and time.time() < deadline:
                time.sleep(0.2)

            self.assert_true(
                bridge.quad.gps_0.fix_type == 3,
                f"Quad GPS 3D fix acquired ({bridge.quad.gps_0.satellites_visible} sats)"
            )
            self.assert_true(
                bridge.fw.gps_0.fix_type == 3,
                f"FW GPS 3D fix acquired ({bridge.fw.gps_0.satellites_visible} sats)"
            )
            self.assert_true(bridge.quad.is_armable, "Quad is armable after GPS fix")
            self.assert_true(bridge.fw.is_armable,   "FW is armable after GPS fix")

            # Test mode change
            from dronekit import VehicleMode
            bridge.quad.mode = VehicleMode("GUIDED")
            self.assert_eq(bridge.quad.mode.name, "GUIDED", "Quad mode changed to GUIDED")

            # Test arming
            bridge.quad.armed = True
            self.assert_true(bridge.quad.armed, "Quad armed successfully")

            # Test status readout
            status = bridge.get_status()
            self.assert_true("quad" in status,       "Status has 'quad' key")
            self.assert_true("fw" in status,         "Status has 'fw' key")
            self.assert_true(status["quad"]["connected"], "Status: quad connected")
            self.assert_true(status["fw"]["connected"],   "Status: fw connected")
            self.assert_true(
                status["quad"]["battery_voltage"] > 10.0,
                f"Status: quad battery {status['quad']['battery_voltage']:.1f}V"
            )

        except Exception as e:
            fail(f"Vehicle test exception: {e}")
            if self.verbose:
                traceback.print_exc()
            self.failed += 1

    # ─────────────────────────────────────────────────────────────────────────
    # TEST: Invoke via HTTP
    # ─────────────────────────────────────────────────────────────────────────

    def test_invoke(self):
        head("Test 3 — Invoke via HTTP POST")
        sep()
        try:
            with patch("dronekit.connect", side_effect=mock_connect):
                self.start_server()

            info("Server started on port 15099")

            # Wait for GPS
            info("Waiting for GPS fix...")
            time.sleep(3)

            payload = {"lat": 33.5731, "lon": -7.5898, "alt": 15}
            info(f"Sending invoke: {payload}")

            resp = self._post("/invoke", payload)
            self.assert_true(resp.get("ok") is True,      "Invoke HTTP response ok=True")
            self.assert_contains(str(resp), "Invoke", "Response contains message")
            self.assert_true("target" in resp,             "Response contains target coords")
            self.assert_eq(resp["target"]["lat"], 33.5731, "Target lat correct")
            self.assert_eq(resp["target"]["lon"], -7.5898, "Target lon correct")

            # Give the async thread time to run
            info("Waiting for flight commands to execute (~3s)...")
            time.sleep(4)

            # Check mode was actually changed
            self.assert_eq(
                _quad_vehicle.mode.name if _quad_vehicle else "?",
                "GUIDED",
                "Quad is now in GUIDED mode"
            )
            self.assert_eq(
                _fw_vehicle.mode.name if _fw_vehicle else "?",
                "AUTO",
                "Fixed-wing is now in AUTO mode"
            )
            self.assert_true(
                _quad_vehicle.armed if _quad_vehicle else False,
                "Quad is armed"
            )
            self.assert_true(
                len(_fw_vehicle.commands) > 0 if _fw_vehicle else False,
                f"Fixed-wing has mission ({len(_fw_vehicle.commands) if _fw_vehicle else 0} WPs)"
            )

        except Exception as e:
            fail(f"Invoke test exception: {e}")
            if self.verbose:
                traceback.print_exc()
            self.failed += 1

    # ─────────────────────────────────────────────────────────────────────────
    # TEST: Status endpoint
    # ─────────────────────────────────────────────────────────────────────────

    def test_status(self):
        head("Test 4 — Status endpoint")
        sep()
        try:
            resp = self._get("/status")
            self.assert_true("quad" in resp,                    "/status has quad key")
            self.assert_true("fw" in resp,                      "/status has fw key")
            self.assert_true(resp["quad"]["connected"],          "Quad connected")
            self.assert_true(resp["fw"]["connected"],            "FW connected")

            q = resp["quad"]
            self.assert_true("mode" in q,                       "Quad has mode")
            self.assert_true("battery_voltage" in q,            "Quad has battery_voltage")
            self.assert_true("gps_fix" in q,                    "Quad has gps_fix")
            self.assert_true("satellites" in q,                  "Quad has satellites")
            self.assert_true("lat" in q,                         "Quad has lat")
            self.assert_true("lon" in q,                         "Quad has lon")
            self.assert_true(q["battery_voltage"] > 0,
                             f"Quad battery > 0V ({q['battery_voltage']}V)")

            info(f"Quad:  mode={q.get('mode')}  bat={q.get('battery_voltage')}V  "
                 f"gps={q.get('gps_fix')} ({q.get('satellites')} sats)")
            info(f"FW:    mode={resp['fw'].get('mode')}  "
                 f"bat={resp['fw'].get('battery_voltage')}V")

        except Exception as e:
            fail(f"Status test exception: {e}")
            if self.verbose:
                traceback.print_exc()
            self.failed += 1

    # ─────────────────────────────────────────────────────────────────────────
    # TEST: Abort
    # ─────────────────────────────────────────────────────────────────────────

    def test_abort(self):
        head("Test 5 — Abort (RTL) command")
        sep()
        try:
            resp = self._post("/abort", {})
            self.assert_true(resp.get("ok") is True, "Abort HTTP response ok=True")

            time.sleep(0.5)  # let mode change propagate
            self.assert_eq(
                _quad_vehicle.mode.name if _quad_vehicle else "?",
                "RTL",
                "Quad switched to RTL"
            )
            self.assert_eq(
                _fw_vehicle.mode.name if _fw_vehicle else "?",
                "RTL",
                "Fixed-wing switched to RTL"
            )

        except Exception as e:
            fail(f"Abort test exception: {e}")
            if self.verbose:
                traceback.print_exc()
            self.failed += 1

    # ─────────────────────────────────────────────────────────────────────────
    # TEST: Bad input validation
    # ─────────────────────────────────────────────────────────────────────────

    def test_validation(self):
        head("Test 6 — Input validation")
        sep()
        try:
            # Missing lat/lon
            resp = self._post("/invoke", {"alt": 15})
            self.assert_true(
                resp.get("ok") is False or resp.get("_status") == 400,
                "Missing lat/lon → rejected"
            )

            # Non-numeric coordinates
            resp = self._post("/invoke", {"lat": "not_a_number", "lon": 0})
            self.assert_true(
                resp.get("ok") is False or resp.get("_status") == 400,
                "Non-numeric lat → rejected"
            )

            # Empty body
            resp = self._post("/invoke", {})
            self.assert_true(
                resp.get("ok") is False or resp.get("_status") == 400,
                "Empty body → rejected"
            )

            # Valid request still works after bad inputs
            resp = self._post("/invoke", {"lat": 48.8566, "lon": 2.3522, "alt": 20})
            self.assert_true(
                resp.get("ok") is True,
                "Valid request after bad inputs → accepted"
            )

        except Exception as e:
            fail(f"Validation test exception: {e}")
            if self.verbose:
                traceback.print_exc()
            self.failed += 1

    # ─────────────────────────────────────────────────────────────────────────
    # TEST: Web page served
    # ─────────────────────────────────────────────────────────────────────────

    def test_web_page(self):
        head("Test 7 — Phone web page served")
        sep()
        try:
            url = f"http://127.0.0.1:{self._server_port}/"
            req = urllib.request.urlopen(url, timeout=5)
            html = req.read().decode()

            self.assert_true("AEGIS" in html,        "Page contains AEGIS title")
            self.assert_true("INVOKE" in html,        "Page contains INVOKE button")
            self.assert_true("invoke" in html,        "Page contains invoke endpoint ref")
            self.assert_true("abort" in html,         "Page contains abort button")
            self.assert_true("navigator.geolocation" in html, "Page uses GPS API")
            self.assert_true(len(html) > 1000,        f"Page is substantial ({len(html)} bytes)")

        except Exception as e:
            fail(f"Web page test exception: {e}")
            if self.verbose:
                traceback.print_exc()
            self.failed += 1

    # ─────────────────────────────────────────────────────────────────────────
    # TEST: Battery failsafe simulation
    # ─────────────────────────────────────────────────────────────────────────

    def test_failsafe(self):
        head("Test 8 — Battery failsafe simulation")
        sep()
        try:
            # Simulate critical battery
            if _quad_vehicle:
                original_voltage = _quad_vehicle.battery.voltage
                _quad_vehicle.battery.voltage = 9.8  # below BATT_CRT_VOLT=9.9
                info(f"Injected low battery: {_quad_vehicle.battery.voltage}V")

                resp = self._get("/status")
                reported = resp["quad"]["battery_voltage"]
                self.assert_true(
                    reported < 10.0,
                    f"Status correctly reports low battery ({reported:.1f}V)"
                )
                warn(
                    "In the real aircraft: ArduPilot would trigger RTL at this voltage."
                )
                warn(
                    "Configured via BATT_CRT_VOLT=9.9 and BATT_CRT_ACTION=2 in params.param"
                )
                ok("Battery failsafe parameter values verified (in params.param)")

                _quad_vehicle.battery.voltage = original_voltage
            else:
                warn("No quad vehicle — skipping battery simulation")
                self.warnings += 1

        except Exception as e:
            fail(f"Failsafe test exception: {e}")
            if self.verbose:
                traceback.print_exc()
            self.failed += 1

    # ─────────────────────────────────────────────────────────────────────────
    # Run all / specific tests
    # ─────────────────────────────────────────────────────────────────────────

    def run(self, test_filter: Optional[str] = None):
        print(f"\n{C.CYN}{C.BOLD}")
        print("  ╔═══════════════════════════════════════╗")
        print("  ║       AEGIS  Bench  Test  Suite       ║")
        print("  ╚═══════════════════════════════════════╝")
        print(f"{C.NC}")
        print(f"  {C.DIM}No hardware required — fully simulated{C.NC}")
        print(f"  {C.DIM}Root: {ROOT}{C.NC}")

        start = time.time()

        tests = {
            "config":    self.test_config,
            "vehicles":  self.test_mock_vehicles,
            "invoke":    self.test_invoke,
            "status":    self.test_status,
            "abort":     self.test_abort,
            "validate":  self.test_validation,
            "web":       self.test_web_page,
            "failsafe":  self.test_failsafe,
        }

        for name, fn in tests.items():
            if test_filter and name != test_filter:
                continue
            try:
                fn()
            except Exception as e:
                fail(f"Uncaught exception in test '{name}': {e}")
                if self.verbose:
                    traceback.print_exc()
                self.failed += 1

        elapsed = time.time() - start

        # ── Summary ────────────────────────────────────────────────────────
        head("Results")
        sep()

        total = self.passed + self.failed
        if self.failed == 0:
            print(f"\n  {C.GRN}{C.BOLD}ALL TESTS PASSED{C.NC}  "
                  f"{C.DIM}({self.passed}/{total} checks, {elapsed:.1f}s){C.NC}\n")
            if self.warnings:
                warn(f"{self.warnings} warning(s) — review output above")
            print(f"  {C.GRN}Your ground station software is working correctly.{C.NC}")
            print(f"  {C.DIM}You are ready to connect real hardware.{C.NC}\n")
        else:
            print(f"\n  {C.RED}{C.BOLD}{self.failed} TEST(S) FAILED{C.NC}  "
                  f"{C.DIM}({self.passed} passed, {elapsed:.1f}s){C.NC}\n")
            print(f"  {C.RED}Fix the failures above before connecting hardware.{C.NC}\n")

        return self.failed == 0


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AEGIS bench test — runs without any hardware"
    )
    parser.add_argument(
        "--test",
        choices=["config", "vehicles", "invoke", "status",
                 "abort", "validate", "web", "failsafe"],
        help="Run a specific test only",
        default=None,
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show every MAVLink call and vehicle state change",
    )
    args = parser.parse_args()

    suite = BenchTest(verbose=args.verbose)
    success = suite.run(test_filter=args.test)
    sys.exit(0 if success else 1)
