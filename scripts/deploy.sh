#!/usr/bin/env bash
# Pulls, installs deps, and re-installs the systemd timer + Caddy snippet.
# See CLAUDE.md -> Infrastructure. Run this on the droplet as the lalutir
# user (sudo is only needed for the systemd/Caddy steps).
set -euo pipefail

cd /home/lalutir/news-scanner
git pull
python3 -m venv venv --upgrade-deps && source venv/bin/activate
pip install -r requirements.txt && deactivate
sudo cp systemd/news-scanner.service systemd/news-scanner.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now news-scanner.timer
sudo cp caddy/news.caddy /etc/caddy/conf.d/news.caddy
caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
