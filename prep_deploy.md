# Deploying to a New Tennis Club

This guide covers deploying the Tennis Ranking app to a new club instance (e.g., `ts-breaking.duckdns.org`). The Docker images and code are identical for all clubs — only the configuration differs.

## Prerequisites

- Raspberry Pi 4+ with 64-bit Raspberry Pi OS
- Internet connection
- A DuckDNS account with a registered domain (free at [duckdns.org](https://www.duckdns.org))
- Router access for port forwarding

## Step 1: Install Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $(whoami)
exit
```

Log back in and verify:

```bash
docker --version
docker compose version
sudo systemctl enable docker
```

## Step 2: Clone the Repository

```bash
cd ~
git clone -b docker https://github.com/AINxtGenDev/stecher_tennis.git
cd stecher_tennis
```

## Step 3: Create the Environment File

```bash
cp .env.example .env
nano .env
```

Set the following values:

| Variable | Value | Notes |
|----------|-------|-------|
| `SECRET_KEY` | Unique random string | Generate with: `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `DUCKDNS_DOMAIN` | `ts-breaking` | Your DuckDNS subdomain (without `.duckdns.org`) |
| `DUCKDNS_TOKEN` | Your DuckDNS API token | 36-char UUID from duckdns.org |
| `ACME_EMAIL` | Your email | For Let's Encrypt certificate registration |
| `ACME_CA` | `https://acme-staging-v02.api.letsencrypt.org/directory` | Start with staging, switch to production later |
| `CORS_ALLOWED_ORIGINS` | `https://ts-breaking.duckdns.org` | Must match the user-facing URL exactly |
| `HTTPS_PORT` | `10443` | Or `443` depending on your router setup |

## Step 4: Router Port Forwarding

On the club's router, add these port forwarding rules:

| External Port | Internal Port | Protocol | Purpose |
|--------------|---------------|----------|---------|
| 443 | 10443 | TCP | HTTPS (Caddy TLS via Docker) |
| 80 | 80 | TCP | HTTP to HTTPS redirect |

## Step 5: Pull and Start

```bash
docker compose pull
docker compose up -d
```

Check status:

```bash
docker compose ps
```

Both containers should show `Up` and the app should be `(healthy)`.

## Step 6: Verify with Staging Certificate

```bash
docker compose logs caddy | grep "certificate obtained"
```

Visit `https://ts-breaking.duckdns.org` in a browser. Accept the staging certificate warning and verify the app loads correctly.

## Step 7: Switch to Production Certificate

Once staging works:

```bash
# Update ACME_CA in .env
sed -i 's|acme-staging-v02|acme-v02|' .env

# Stop the stack
docker compose down

# Clear cached staging certificates
docker volume rm $(docker volume ls -q | grep caddy_data)

# Start with production certs
docker compose up -d
```

Wait 1-2 minutes, then visit `https://ts-breaking.duckdns.org` — no browser warning this time.

## Step 8: Customize Player Data

The app auto-initializes with default players from `initial_players.json`. For the new club, either:

- **Option A**: Log in as superadmin, go to `/db_settings`, and manage players there
- **Option B**: Upload a prepared database via the superadmin panel
- **Option C**: Edit `initial_players.json` before first start, then reset the database

## Updating the Deployment

When a new version is available:

```bash
cd ~/stecher_tennis
git pull
docker compose pull
docker compose up -d
```

## Troubleshooting

- **Site can't be reached**: Check router port forwarding
- **TLS errors**: Clear caddy_data volume and restart (`docker compose down && docker volume rm $(docker volume ls -q | grep caddy_data) && docker compose up -d`)
- **Pyramid not showing**: Check `CORS_ALLOWED_ORIGINS` matches the exact URL (no trailing slash, correct port)
- **After changing `.env`**: Must use `docker compose down && docker compose up -d` (not just `restart`)
