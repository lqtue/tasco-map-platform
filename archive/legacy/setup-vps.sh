#!/bin/bash
# setup-vps.sh — Bootstrap a Vultr/any VPS for the TASCO tile server
# Run as root on a fresh Ubuntu 22.04/24.04 instance

set -euo pipefail

echo "=== TASCO Tile Server Setup ==="

# Update system
apt-get update && apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
systemctl enable docker && systemctl start docker

# Install Docker Compose
apt-get install -y docker-compose-plugin

# Install certbot for HTTPS
apt-get install -y certbot

# Create project directory
mkdir -p /opt/tasco-tiles
cd /opt/tasco-tiles

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Copy config/ files to /opt/tasco-tiles/"
echo "  2. cp .env.example .env && edit .env with R2 credentials"
echo "  3. Run: certbot certonly --standalone -d tiles.tasco-internal.vn"
echo "  4. Run: docker compose up -d"
echo "  5. Test: curl http://localhost:8080/healthz"
