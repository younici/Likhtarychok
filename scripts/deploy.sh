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

log "waiting for backend API"
ok=""
for i in $(seq 1 30); do
  if "${compose[@]}" exec -T backend python -c \
     "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/vapid_public_key',timeout=3).status==200 else 1)" >/dev/null 2>&1; then
    ok=1; break
  fi
  sleep 2
done
if [ -z "$ok" ]; then
  "${compose[@]}" logs --tail=80 backend || true
  die "backend did not become healthy (previous revision was $prev_rev; volumes untouched)"
fi
log "backend OK"

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
log "frontend index.html present"

# ---------- 6. HTTP checks through nginx (no DNS dependency) ----------
curl_site() { curl -ksS --max-time "$2" -o /dev/null -w '%{http_code}' \
  --resolve "$SITE_DOMAIN:443:127.0.0.1" "https://$SITE_DOMAIN$1"; }

code="$(curl_site / 10 || true)"
[ "$code" = "200" ] || die "GET / returned '$code'"
log "GET / -> 200"

code="$(curl_site /api/vapid_public_key 10 || true)"
[ "$code" = "200" ] || die "GET /api/vapid_public_key returned '$code'"
log "GET /api/vapid_public_key -> 200"

# External schedule source: failure is only a warning.
code="$(curl_site '/api/status?queue=1.1' 20 || true)"
if [ "$code" = "200" ]; then log "GET /api/status -> 200"
else warn "GET /api/status?queue=1.1 returned '$code' (external source may be down); deploy not failed"; fi

log "deploy finished: $new_rev"
