# Makefile – Auto-install RedSpectre on macOS + Linux
# Clones: https://github.com/asyaasha7/RedSpectre
# Requires: python3, git, npm (for localtunnel)

SHELL := /bin/sh
.DEFAULT_GOAL := help

RED_DIR     := RedSpectre
REPO_URL    := https://github.com/asyaasha7/RedSpectre.git

PYTHON      ?= python3
VENV_DIR    := $(RED_DIR)/.venv
PYTHON_BIN  := $(VENV_DIR)/bin/python
PIP         := $(VENV_DIR)/bin/pip

PORT        ?= 8000
REQUIRED_ENV := AGENTARENA_API_KEY WEBHOOK_AUTH_TOKEN

.PHONY: help clone bootstrap env check-env run-server run-local node-tools tunnel clean

help:
	@echo ""
	@echo "RedSpectre Installer"
	@echo "---------------------"
	@echo "make clone        - clone the repo"
	@echo "make bootstrap    - create venv + install deps"
	@echo "make env          - create .env"
	@echo "make run-server   - run audit-agent server"
	@echo "make tunnel       - expose with localtunnel"
	@echo "make clean        - wipe repo & env"

clone:
	@if [ -d $(RED_DIR) ]; then \
		echo "✔ Repo already cloned."; \
	else \
		echo "📥 Cloning RedSpectre..."; \
		git clone $(REPO_URL) $(RED_DIR); \
	fi

bootstrap: clone
	@echo "🐍 Creating virtualenv..."
	$(PYTHON) -m venv $(VENV_DIR)
	@echo "⬆️  Upgrading pip..."
	$(PYTHON_BIN) -m pip install --upgrade pip
	@echo "📦 Installing RedSpectre (pip install -e RedSpectre)..."
	$(PIP) install -e $(RED_DIR)
	@if [ -f $(RED_DIR)/requirements.txt ]; then \
		echo "📚 Installing extra requirements..."; \
		$(PIP) install -r $(RED_DIR)/requirements.txt; \
	fi
	@echo "✔ Install complete."

env: clone
	@if [ ! -f $(RED_DIR)/.env ]; then \
		cp $(RED_DIR)/.env.example $(RED_DIR)/.env; \
		echo "✔ .env created at $(RED_DIR)/.env"; \
	else \
		echo "✔ .env already exists."; \
	fi

check-env: env
	@echo "🔎 Checking required environment variables..."
	@missing=0; \
	for var in $(REQUIRED_ENV); do \
		if ! grep -q "^$$var=" $(RED_DIR)/.env; then \
			echo "❌ Missing: $$var"; \
			missing=1; \
		else \
			echo "✔ $$var ok"; \
		fi; \
	done; \
	if [ $$missing -eq 1 ]; then exit 1; fi

run-server: bootstrap check-env
	@echo "🚀 Starting audit-agent server..."
	cd $(RED_DIR) && .venv/bin/audit-agent server --port $(PORT)

run-local: bootstrap env
	cd $(RED_DIR) && .venv/bin/audit-agent local

node-tools:
	@if ! command -v npm >/dev/null; then \
		echo "❌ npm not found. Install Node.js first."; exit 1; \
	fi
	@if command -v lt >/dev/null; then \
		echo "✔ localtunnel already installed"; \
	else \
		echo "📦 Installing localtunnel (npm)..."; \
		npm install -g localtunnel || \
		(echo "❌ npm install failed"; exit 1); \
	fi

tunnel: node-tools
	@echo "🌐 Starting tunnel on port $(PORT)..."
	lt --port $(PORT)

clean:
	@echo "🧹 Removing cloned repo & venv..."
	rm -rf $(RED_DIR)
	@echo "✔ Cleaned."

