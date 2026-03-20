"""
AEGIS Invoke Server
-------------------
Receives an HTTP POST /invoke with the user's GPS coordinates,
then pushes MAVLink commands to the quadcopter and fixed-wing
via two SiK radio serial connections.

Run:
    python3 invoke_server.py

Test from terminal:
    curl -X POST http://localhost:5000/invoke \
         -H "Content-Type: application/json" \
         -d '{"lat": 33.5731, "lon": -7.5898, "alt": 15}'
"""

import time
import threading
import logging
from flask import Flask, request, jsonify, send_from_directory
from mavlink_bridge import AegisBridge
from config import SERVER_PORT, WEB_DIR

logging.basicConfig(
    level=logging.INFO,
    format="[AEGIS %(asctime)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("aegis")

app = Flask(__name__)
bridge = AegisBridge()


@app.route("/")
def index():
    """Serve the phone invoke webpage."""
    return send_from_directory(WEB_DIR, "index.html")


@app.route("/status", methods=["GET"])
def status():
    """
    Returns current status of both vehicles.
    Poll this from the phone page to show live battery + mode.
    """
    return jsonify(bridge.get_status())


@app.route("/invoke", methods=["POST"])
def invoke():
    """
    Main invoke endpoint.

    Expected JSON body:
        {
            "lat": 33.5731,
            "lon": -7.5898,
            "alt": 15          (optional — defaults to config values)
        }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"ok": False, "error": "No JSON body"}), 400

    lat = data.get("lat")
    lon = data.get("lon")
    alt = data.get("alt", None)  # None = use defaults from config

    if lat is None or lon is None:
        return jsonify({"ok": False, "error": "lat and lon are required"}), 400

    try:
        lat = float(lat)
        lon = float(lon)
        if alt is not None:
            alt = float(alt)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "lat/lon/alt must be numbers"}), 400

    log.info(f"INVOKE received: lat={lat:.6f} lon={lon:.6f} alt={alt}")

    # Run in background thread so the HTTP response returns immediately
    thread = threading.Thread(
        target=bridge.invoke, args=(lat, lon, alt), daemon=True
    )
    thread.start()

    return jsonify({
        "ok": True,
        "message": "Invoke sequence started",
        "target": {"lat": lat, "lon": lon, "alt": alt},
    })


@app.route("/abort", methods=["POST"])
def abort():
    """
    Sends RTL command to both vehicles immediately.
    Use this as an emergency stop from the phone.
    """
    log.info("ABORT received — sending RTL to all vehicles")
    bridge.abort()
    return jsonify({"ok": True, "message": "RTL command sent to all vehicles"})


if __name__ == "__main__":
    log.info("Starting AEGIS ground station...")
    bridge.connect()
    log.info(f"Invoke server running on port {SERVER_PORT}")
    log.info(f"Open http://YOUR-PI-IP:{SERVER_PORT} on your phone")
    app.run(host="0.0.0.0", port=SERVER_PORT, debug=False)
