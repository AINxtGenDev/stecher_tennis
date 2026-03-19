#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Stecher Tennis — RPi Deployment / Cutover Script
#
# Automates the one-time cutover from bare-metal systemd + Caddy to Docker
# Compose on the Raspberry Pi, plus subsequent deployments.
#
# Prerequisites:
#   - SSH alias "stecher" configured in ~/.ssh/config (port 10115, key auth)
#   - Docker installed on the RPi (curl -fsSL https://get.docker.com | sh)
#   - 64-bit Raspberry Pi OS (aarch64)
#   - Images already pushed to GHCR (run build-and-push.sh first)
#
# Usage:
#   ./deploy.sh
# =============================================================================

# --- Configuration ---
RPI_HOST="stecher"
REMOTE_DIR="~/stecher_tennis"
REPO_URL="https://github.com/ainxtgendev/stecher-tennis.git"
ACME_PRODUCTION="https://acme-v02.api.letsencrypt.org/directory"
ACME_STAGING="https://acme-staging-v02.api.letsencrypt.org/directory"
HEALTH_URL="https://nechvatal.duckdns.org:10443/health"

# --- Helper ---
remote() {
    ssh "${RPI_HOST}" "$@"
}

# =============================================================================
# 1. Pre-flight checks
# =============================================================================
echo ""
echo "===== Stecher Tennis — RPi Deployment ====="
echo ""

echo "==> Checking SSH connectivity..."
if ! remote "echo 'SSH connection OK'"; then
    echo "ERROR: Cannot connect to RPi via SSH alias '${RPI_HOST}'."
    echo "Ensure ~/.ssh/config has a 'Host stecher' entry pointing to 192.168.1.213:10115."
    exit 1
fi

echo "==> Checking RPi architecture..."
ARCH=$(remote "uname -m")
if [ "${ARCH}" != "aarch64" ]; then
    echo "ERROR: RPi architecture is '${ARCH}', expected 'aarch64'."
    echo "64-bit Raspberry Pi OS is required for ARM64 Docker images."
    echo "Reinstall Raspberry Pi OS (64-bit) if necessary."
    exit 1
fi
echo "    Architecture: ${ARCH} (OK)"

echo "==> Checking Docker installation..."
if ! remote "docker --version"; then
    echo ""
    echo "ERROR: Docker is not installed on the RPi."
    echo "Install it with:"
    echo "  ssh ${RPI_HOST} 'curl -fsSL https://get.docker.com | sh'"
    echo "  ssh ${RPI_HOST} 'sudo usermod -aG docker stecher'"
    echo "Then log out and back in, and re-run this script."
    exit 1
fi

echo "==> Checking Docker Compose plugin..."
if ! remote "docker compose version"; then
    echo ""
    echo "ERROR: Docker Compose plugin is not installed on the RPi."
    echo "It should be included with the Docker convenience script install."
    echo "Try reinstalling Docker or install the plugin manually."
    exit 1
fi

# =============================================================================
# 2. Stop old services
# =============================================================================
echo ""
echo "==> Stopping old services..."
remote "sudo systemctl stop stecher-tennis.service 2>/dev/null || true"
remote "sudo systemctl disable stecher-tennis.service 2>/dev/null || true"
remote "sudo systemctl stop caddy.service 2>/dev/null || true"
remote "sudo systemctl disable caddy.service 2>/dev/null || true"
echo "    Old services stopped and disabled."

# =============================================================================
# 3. Enable Docker on boot
# =============================================================================
echo ""
echo "==> Enabling Docker to start on boot..."
remote "sudo systemctl enable docker"

# =============================================================================
# 4. Clone or update repo
# =============================================================================
echo ""
echo "==> Updating repository on RPi..."
remote "if [ -d ${REMOTE_DIR}/.git ]; then cd ${REMOTE_DIR} && git pull; else git clone ${REPO_URL} ${REMOTE_DIR}; fi"

# =============================================================================
# 5. Check .env exists
# =============================================================================
echo ""
echo "==> Checking .env configuration..."
if ! remote "test -f ${REMOTE_DIR}/.env"; then
    echo ""
    echo "ERROR: .env file not found on RPi at ${REMOTE_DIR}/.env"
    echo "Create it from .env.example:"
    echo "  ssh ${RPI_HOST} 'cp ${REMOTE_DIR}/.env.example ${REMOTE_DIR}/.env'"
    echo "  ssh ${RPI_HOST} 'nano ${REMOTE_DIR}/.env'"
    echo ""
    echo "Required values: SECRET_KEY, DUCKDNS_TOKEN, ACME_EMAIL"
    echo "Then re-run this script."
    exit 1
fi
echo "    .env file found."

# =============================================================================
# 6. Pull and start Docker stack (staging certs first)
# =============================================================================
echo ""
echo "==> Pulling Docker images..."
remote "cd ${REMOTE_DIR} && docker compose pull"

echo ""
echo "==> Starting Docker stack (staging certs)..."
remote "cd ${REMOTE_DIR} && docker compose up -d"

# =============================================================================
# 7. Wait for health check
# =============================================================================
echo ""
echo "==> Waiting for app to become healthy..."
for i in $(seq 1 30); do
    if remote "curl -sf http://localhost:5000/health" > /dev/null 2>&1; then
        echo "    Health check passed!"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "ERROR: Health check failed after 30 attempts."
        echo "Check logs: ssh ${RPI_HOST} 'cd ${REMOTE_DIR} && docker compose logs'"
        exit 1
    fi
    sleep 2
done

# =============================================================================
# 8. Switch to production ACME (interactive prompt)
# =============================================================================
echo ""
echo "===== Staging verification complete ====="
echo "The Docker stack is running with staging certificates."
echo ""
read -p "Switch to production Let's Encrypt certificates? [y/N] " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "==> Switching ACME_CA to production..."
    remote "cd ${REMOTE_DIR} && sed -i 's|${ACME_STAGING}|${ACME_PRODUCTION}|' .env"

    echo "==> Restarting stack with production certs..."
    remote "cd ${REMOTE_DIR} && docker compose down"

    # Remove caddy_data volume to clear cached staging certs
    echo "==> Clearing cached staging certificates..."
    remote "docker volume rm \$(docker volume ls -q | grep caddy_data) 2>/dev/null || true"

    remote "cd ${REMOTE_DIR} && docker compose up -d"

    echo "==> Waiting for production certificate (this may take 1-2 minutes)..."
    sleep 30

    echo "==> Verifying production certificate..."
    if curl -sf --max-time 10 "${HEALTH_URL}" > /dev/null 2>&1; then
        echo "    Production HTTPS is working!"
    else
        echo "    WARNING: Could not verify production HTTPS yet."
        echo "    Certificate issuance may take a few more minutes."
        echo "    Check manually: curl -v ${HEALTH_URL}"
    fi
else
    echo "Skipping production cert switch. You can do it later:"
    echo "  1. Edit .env on RPi: change ACME_CA to ${ACME_PRODUCTION}"
    echo "  2. docker compose down"
    echo "  3. docker volume rm \$(docker volume ls -q | grep caddy_data)"
    echo "  4. docker compose up -d"
fi

# =============================================================================
# 9. Final summary
# =============================================================================
echo ""
echo "===== Deployment Complete ====="
echo "App URL:  ${HEALTH_URL}"
echo "SSH:      ssh ${RPI_HOST}"
echo "Logs:     ssh ${RPI_HOST} 'cd ${REMOTE_DIR} && docker compose logs -f'"
echo "Update:   ssh ${RPI_HOST} 'cd ${REMOTE_DIR} && docker compose pull && docker compose up -d'"
