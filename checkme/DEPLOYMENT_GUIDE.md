# AFASA 2.0 Deployment Guide (Self‑Hosted VPS)

This guide is written so Antigravity can deploy AFASA safely while you provide environment values.

## 0) Principles (do this to prevent breakage)
- **Pin image versions** (avoid `:latest` for infra).
- **Deploy from Git commits** (reproducible).
- **CI must pass** before deployment.
- **Keep rollback simple**: previous Git commit + `docker compose up -d`.

## 1) Prerequisites (VPS)
- Ubuntu 24.04.x LTS
- Docker Engine + Docker Compose plugin installed
- `git` installed
- Repo checked out to `~/afasa2.0` (or your chosen path)

Recommended:
- A dedicated directory for ops logs: `~/afasa2.0/_ops`

## 2) Repo layout expectations
- `docker-compose.yml` at repo root
- `.env` at repo root (NOT committed; you create it on the VPS)
- Services in `services/*`

## 3) First-time setup on VPS
1. Clone repo:
   ```bash
   cd ~
   git clone <YOUR_REPO_URL> afasa2.0
   cd ~/afasa2.0
   ```
2. Create `.env` from example (if present):
   ```bash
   cp .env.example .env
   nano .env
   ```
3. Bring up infra first:
   ```bash
   docker compose up -d postgres redis nats minio keycloak mediamtx traefik
   docker compose ps
   ```
4. Bring up app services:
   ```bash
   docker compose up -d
   docker compose ps
   ```

## 4) Verification checklist (must pass)
Run:
```bash
cd ~/afasa2.0
docker compose ps
docker compose logs traefik --tail=100
docker compose logs keycloak --tail=100
```

Validate:
- Traefik is running and not erroring on Docker provider discovery.
- Keycloak health endpoint is reachable (if you use healthchecks).
- Portal responds at its configured route (e.g., `/portal`).
- API services respond via Traefik routes (e.g., `/api/media`).

## 5) Ongoing deployments (manual)
Standard deployment sequence:
```bash
cd ~/afasa2.0
git pull
docker compose pull
docker compose up -d --remove-orphans
docker compose ps
```

If you changed Dockerfiles or local build context:
```bash
docker compose build
docker compose up -d --remove-orphans
```

## 6) Rollback (fast and reliable)
1. See recent commits:
   ```bash
   git log --oneline -n 10
   ```
2. Reset to previous commit:
   ```bash
   git reset --hard <COMMIT_SHA>
   ```
3. Redeploy:
   ```bash
   docker compose up -d --force-recreate --remove-orphans
   docker compose ps
   ```

## 7) GitHub Actions auto-deploy (Render-like)
Your repo includes:
- `ci.yml`: runs checks on push/PR (lint/build/smoke)
- `deploy.yml`: runs on push to main/master and deploys via SSH

### You must set these GitHub secrets:
- `VPS_HOST`
- `VPS_USER`
- `VPS_PORT`
- `VPS_SSH_KEY` (private key for the deploy user)
Optional:
- `VPS_PATH` (default `~/afasa2.0`)

Once secrets exist, pushing to the deployment branch will:
1) run CI
2) SSH into VPS
3) `git pull`
4) `docker compose up -d`

## 8) Renovate (safe updates)
Renovate opens PRs to update:
- container image tags (where configured)
- package dependencies (if configured)

Rules:
- Never auto-merge without CI green.
- Review major version bumps carefully.
- Prefer scheduled update windows.

## 9) Notes on Traefik + Docker Engine compatibility
If Traefik cannot talk to Docker:
- You will see errors in Traefik logs.
- Fix by pinning a known-good Traefik version, or switching to file-provider routes.
- As a last resort, downgrade Docker Engine to a stable supported version and hold packages.

---

If you want, add a **staging** environment (separate compose project + separate domain) so broken changes never hit production first.
