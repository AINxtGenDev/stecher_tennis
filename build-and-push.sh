#!/usr/bin/env bash
set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────
REGISTRY="ghcr.io"
NAMESPACE="ainxtgendev"
APP_IMAGE="ghcr.io/ainxtgendev/stecher-tennis-app"
CADDY_IMAGE="ghcr.io/ainxtgendev/stecher-tennis-caddy"
BUILDER_NAME="multiarch"
PLATFORMS="linux/amd64,linux/arm64"

# ── GHCR_TOKEN validation ───────────────────────────────────────────────────
if [ -z "${GHCR_TOKEN:-}" ]; then
    echo "ERROR: GHCR_TOKEN environment variable is not set."
    echo "Create a GitHub Personal Access Token with 'write:packages' scope:"
    echo "  https://github.com/settings/tokens/new?scopes=write:packages"
    echo "Then export it: export GHCR_TOKEN=ghp_..."
    exit 1
fi

# ── Version extraction ───────────────────────────────────────────────────────
VERSION=$(grep -oP 'Version:\s*\K[0-9]+\.[0-9]+(\.[0-9]+)?' templates/index.html)
if [ -z "$VERSION" ]; then
    echo "ERROR: Could not extract version from templates/index.html"
    exit 1
fi
echo "Building version: v${VERSION}"

# ── QEMU binfmt registration (idempotent) ────────────────────────────────────
echo "==> Registering QEMU binfmt handlers..."
docker run --privileged --rm tonistiigi/binfmt --install all

# ── Buildx builder creation (idempotent) ─────────────────────────────────────
echo "==> Setting up buildx builder '${BUILDER_NAME}'..."
docker buildx create --name "${BUILDER_NAME}" --driver docker-container --bootstrap --use 2>/dev/null || \
    docker buildx use "${BUILDER_NAME}"

# ── GHCR login ───────────────────────────────────────────────────────────────
echo "==> Logging in to ${REGISTRY}..."
echo "${GHCR_TOKEN}" | docker login "${REGISTRY}" -u "${GHCR_USER:-ainxtgendev}" --password-stdin

# ── Build and push app image ─────────────────────────────────────────────────
echo "==> Building and pushing ${APP_IMAGE}:v${VERSION} (${PLATFORMS})..."
docker buildx build \
    --platform "${PLATFORMS}" \
    --tag "${APP_IMAGE}:latest" \
    --tag "${APP_IMAGE}:v${VERSION}" \
    --push \
    .

# ── Build and push caddy image ───────────────────────────────────────────────
echo "==> Building and pushing ${CADDY_IMAGE}:v${VERSION} (${PLATFORMS})..."
docker buildx build \
    --platform "${PLATFORMS}" \
    --tag "${CADDY_IMAGE}:latest" \
    --tag "${CADDY_IMAGE}:v${VERSION}" \
    --push \
    -f Dockerfile.caddy \
    .

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "===== Build Complete ====="
echo "App:   ${APP_IMAGE}:v${VERSION}"
echo "Caddy: ${CADDY_IMAGE}:v${VERSION}"
echo "Tags:  :latest, :v${VERSION}"
echo "Platforms: ${PLATFORMS}"
echo ""
echo "To deploy on RPi: docker compose pull && docker compose up -d"
