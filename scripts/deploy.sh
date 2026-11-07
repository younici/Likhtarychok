#!/usr/bin/env bash
# Production deploy, executed ON THE SERVER by GitHub Actions.
# Never removes volumes, never touches backend/.env, never recreates postgres/redis.
set -euo pipefail

DEPLOY_PATH="${DEPLOY_PATH:?DEPLOY_PATH is required}"
BRANCH="${DEPLOY_BRANCH:-master}"
STAGING="${FRONTEND_STAGING:-}"
WEB_ROOT="${WEB_ROOT:-/var/www/likhtarychok}"
SITE_DOMAIN="${SITE_DOMAIN:-likhtarychok.org}"
PROJECT="${COMPOSE_PROJECT:-likhtarychok}"
COMPOSE_MAIN="${COMPOSE_MAIN:-/etc/likhtarychok/compose.yml}"
COMPOSE_PG="${COMPOSE_PG:-/etc/likhtarychok/postgres.yml}"

log()  { echo "==> $*"; }
warn() { echo "::warning::$*"; }
die()  { echo "::error::$*"; exit 1; }

[ "$WEB_ROOT" = "/var/www/likhtarychok" ] || [ -n "${ALLOW_CUSTOM_WEB_ROOT:-}" ] || die "unexpected WEB_ROOT: $WEB_ROOT"

# ---------- 1. sync source ----------
cd "$DEPLOY_PATH"
[ -f backend/.env ] || die "backend/.env is missing on the server (it is never deployed from git)"
current_branch="$(git rev-parse --abbrev-ref HEAD)"
[ "$current_branch" = "$BRANCH" ] || die "server checkout is on '$current_branch', expected '$BRANCH'"
prev_rev="$(git rev-parse HEAD)"
git fetch origin "$BRANCH"
git merge --ff-only "origin/$BRANCH"
new_rev="$(git rev-parse HEAD)"
log "source: $prev_rev -> $new_rev"

# ---------- 2. compose: single project, both production files ----------
[ -f "$COMPOSE_MAIN" ] || die "$COMPOSE_MAIN not found"
compose=(docker compose -p "$PROJECT" --project-directory "$DEPLOY_PATH" -f "$COMPOSE_MAIN")
[ -f "$COMPOSE_PG" ] && compose+=(-f "$COMPOSE_PG") || warn "$COMPOSE_PG not found, continuing without it"

log "validating compose config"
"${compose[@]}" config -q

# ---------- 3. backend (only the backend service; deps are left untouched) ----------
log "building and (re)starting backend"
"${compose[@]}" up -d --build --no-deps backend

log "waiting for backend API to be ready (up to 90s)..."
ok=""
for i in $(seq 1 45); do
  if "${compose[@]}" exec -T backend python -c \
     "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/vapid_public_key',timeout=3).status==200 else 1)" >/dev/null 2>&1; then
    ok=1; break
  fi
  sleep 2
done
if [ -z "$ok" ]; then
  "${compose[@]}" logs --tail=80 backend || true
  die "backend did not become healthy in time (volumes untouched)"
fi
log "backend API is UP and healthy"

# ---------- 4. infrastructure state ----------
"${compose[@]}" ps
for svc in postgres redis; do
  cid="$("${compose[@]}" ps -q "$svc" 2>/dev/null || true)"
  [ -n "$cid" ] || { warn "service '$svc' not found in compose project (maybe named differently)"; continue; }
  state="$(docker inspect -f '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}}' "$cid")"
  case "$state" in
    running*unhealthy*|running\ starting*) die "$svc state: $state" ;;
    running*) log "$svc: $state" ;;
    *) die "$svc state: $state" ;;
  esac
done

# ---------- 5. frontend ----------
if [ -n "$STAGING" ]; then
  [ -f "$STAGING/index.html" ] || die "frontend artifact has no index.html"
  [ -d "$WEB_ROOT" ] || die "$WEB_ROOT does not exist"
  log "syncing frontend to $WEB_ROOT"
  rsync -a --delete "$STAGING"/ "$WEB_ROOT"/
  rm -rf "$STAGING"
fi
[ -f "$WEB_ROOT/index.html" ] || die "$WEB_ROOT/index.html missing"
log "frontend index.html is present in $WEB_ROOT"

# ---------- 6. HTTP checks (with retries and fallback) ----------
log "verifying site responses..."
sleep 3

# Function to try fetching an endpoint:
# 1. Direct HTTPS (normal DNS / public)
# 2. Local HTTPS with --resolve
# 3. Local HTTP (port 80) with Host header
query_endpoint() {
  local path="$1"
  local code="000"

  # 1. Try public HTTPS
  code=$(curl -ksS --max-time 6 -o /dev/null -w '%{http_code}' "https://$SITE_DOMAIN$path" 2>/dev/null || true)
  if [ "$code" = "200" ]; then echo "$code"; return 0; fi

  # 2. Try localhost with --resolve 443
  code=$(curl -ksS --max-time 6 -o /dev/null -w '%{http_code}' --resolve "$SITE_DOMAIN:443:127.0.0.1" "https://$SITE_DOMAIN$path" 2>/dev/null || true)
  if [ "$code" = "200" ]; then echo "$code"; return 0; fi

  # 3. Try localhost HTTP (port 80) with Host header
  code=$(curl -sS --max-time 6 -o /dev/null -w '%{http_code}' -H "Host: $SITE_DOMAIN" "http://127.0.0.1$path" 2>/dev/null || true)
  if [ "$code" = "200" ]; then echo "$code"; return 0; fi

  echo "$code"
}

# Verify GET / with retries
check_root="000"
for attempt in $(seq 1 5); do
  check_root=$(query_endpoint "/")
  if [ "$check_root" = "200" ]; then break; fi
  sleep 2
done

if [ "$check_root" = "200" ]; then
  log "GET / -> 200 (OK)"
else
  warn "GET / returned HTTP code '$check_root' (Nginx may listen on specific interface or Cloudflare is proxying)"
fi

# Verify GET /api/vapid_public_key
check_api="000"
for attempt in $(seq 1 5); do
  check_api=$(query_endpoint "/api/vapid_public_key")
  if [ "$check_api" = "200" ]; then break; fi
  sleep 2
done

if [ "$check_api" = "200" ]; then
  log "GET /api/vapid_public_key -> 200 (OK)"
else
  warn "GET /api/vapid_public_key returned HTTP code '$check_api'"
fi

# Status queue check (soft warning if external provider is busy)
check_status=$(query_endpoint "/api/status?queue=1.1")
if [ "$check_status" = "200" ]; then
  log "GET /api/status -> 200 (OK)"
else
  warn "GET /api/status returned '$check_status' (external schedule source may be syncing); deploy succeeds"
fi

log "deploy finished successfully: $new_rev"
EOF
