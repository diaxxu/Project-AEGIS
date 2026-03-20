# AEGIS Makefile
# Usage: make <target>
#
# Set PI_HOST to your Pi's address: make deploy PI_HOST=192.168.1.x
PI_HOST ?= aegis-base.local
PI_USER ?= pi
PI_DIR  ?= /home/pi/aegis

.PHONY: help deploy logs status restart stop start test lint clean

help:
	@echo ""
	@echo "  AEGIS — available make targets"
	@echo ""
	@echo "  deploy    Sync repo to the Raspberry Pi"
	@echo "  start     Start the AEGIS service on the Pi"
	@echo "  stop      Stop the AEGIS service on the Pi"
	@echo "  restart   Restart the AEGIS service on the Pi"
	@echo "  status    Show service status on the Pi"
	@echo "  logs      Tail live service logs from the Pi"
	@echo "  invoke    Send a test invoke command to the Pi"
	@echo "  test      Run bench tests (no hardware needed)"
	@echo "  lint      Run Python linter on ground station code"
	@echo "  clean     Remove Python cache files"
	@echo ""
	@echo "  PI_HOST=$(PI_HOST)  PI_USER=$(PI_USER)"
	@echo ""

# ── Pi operations ──────────────────────────────────────────────────────────

deploy:
	@echo "→ Syncing to $(PI_USER)@$(PI_HOST):$(PI_DIR)..."
	rsync -avz --exclude '.git' --exclude '__pycache__' --exclude '.venv' \
	  --exclude '*.pyc' --exclude '.DS_Store' \
	  ./ $(PI_USER)@$(PI_HOST):$(PI_DIR)/
	@echo "✓ Sync complete"

start:
	ssh $(PI_USER)@$(PI_HOST) 'sudo systemctl start aegis'
	@echo "✓ AEGIS service started"

stop:
	ssh $(PI_USER)@$(PI_HOST) 'sudo systemctl stop aegis'
	@echo "✓ AEGIS service stopped"

restart:
	ssh $(PI_USER)@$(PI_HOST) 'sudo systemctl restart aegis'
	@echo "✓ AEGIS service restarted"

status:
	ssh $(PI_USER)@$(PI_HOST) 'sudo systemctl status aegis --no-pager'

logs:
	@echo "→ Tailing logs from $(PI_HOST) (Ctrl+C to stop)..."
	ssh $(PI_USER)@$(PI_HOST) 'sudo journalctl -u aegis -f --no-pager'

invoke:
	@echo "→ Sending test invoke to http://$(PI_HOST):5000/invoke ..."
	curl -s -X POST http://$(PI_HOST):5000/invoke \
	  -H "Content-Type: application/json" \
	  -d '{"lat": 33.5731, "lon": -7.5898, "alt": 15}' | python3 -m json.tool
	@echo ""

vehicle-status:
	@echo "→ Fetching vehicle status from http://$(PI_HOST):5000/status ..."
	curl -s http://$(PI_HOST):5000/status | python3 -m json.tool
	@echo ""

abort:
	@echo "→ Sending ABORT to http://$(PI_HOST):5000/abort ..."
	curl -s -X POST http://$(PI_HOST):5000/abort | python3 -m json.tool
	@echo ""

# ── Local dev operations ───────────────────────────────────────────────────

test:
	@echo "→ Running AEGIS bench tests (no hardware required)..."
	python3 tools/test_bench.py

test-verbose:
	python3 tools/test_bench.py --verbose

lint:
	@echo "→ Linting ground station code..."
	@python3 -m flake8 ground_station/ \
	  --max-line-length=100 \
	  --ignore=E501,W503 \
	  --exclude=__pycache__ \
	  && echo "✓ No lint errors" || true

clean:
	@find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	@find . -name '*.pyc' -delete 2>/dev/null || true
	@find . -name '*.pyo' -delete 2>/dev/null || true
	@echo "✓ Cache files removed"

# ── Pi setup shortcut ──────────────────────────────────────────────────────

setup-pi: deploy
	@echo "→ Running installer on Pi..."
	ssh $(PI_USER)@$(PI_HOST) 'cd $(PI_DIR) && chmod +x install.sh && ./install.sh'
