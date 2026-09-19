# Likhtarychok

> A web service for monitoring planned power outages in Zhytomyr region, with Web Push and Telegram notifications.

Likhtarychok collects outage schedules from the official Zhytomyroblenergo source, converts them into a normalized hourly / half-hourly representation, and provides a simple web interface for checking the schedule for a selected queue.

The project is split into a **React + Vite frontend** and a **FastAPI backend**. The backend also runs Telegram bots, a notification scheduler, persistent storage, and optional Redis caching.

## Highlights

- View the outage schedule for all supported queues
- Switch between a full schedule view and compact outage intervals
- Persist the selected queue in the browser
- Refresh schedule data automatically every 5 minutes
- Receive Web Push notifications before a planned outage
- Receive the same notifications through Telegram
- Subscribe and unsubscribe directly from the website
- Expose a REST API for subscriptions and status
- Expose a gRPC-Web compatible status endpoint for the frontend
- Optional PostgreSQL-compatible database storage through SQLAlchemy + asyncpg
- Optional Redis storage / cache layer
- Background scheduling for cache refreshes and notifications
- Separate Telegram bots for notifications and help / administration
- Docker-ready backend deployment

## How it works

```text
                    ┌──────────────────────┐
                    │  Official source     │
                    │  Zhytomyroblenergo   │
                    └──────────┬───────────┘
                               │
                               │ HTML schedule
                               ▼
                    ┌──────────────────────┐
                    │      FastAPI         │
                    │      backend         │
                    │                      │
                    │ parser / cache / DB  │
                    └───────┬───────┬──────┘
                            │       │
                  gRPC-Web  │       │  subscriptions
                            │       │
                            ▼       ▼
                    ┌──────────┐  ┌──────────────┐
                    │ React UI │  │ Redis / DB   │
                    └──────────┘  └──────────────┘
                            │
                            │ Web Push
                            ▼
                       Browser user

                            │
                            │ Telegram
                            ▼
                       Telegram bots
```

The backend currently parses the schedule from `https://www.ztoe.com.ua/unhooking-search.php`. The parser supports source data represented as either 24 hourly values or 48 half-hour values and normalizes the result for the frontend.

## User flow

1. Select your outage queue.
2. The selected queue is saved locally in the browser.
3. The frontend requests the current schedule from the backend.
4. The schedule is displayed as a full timeline or compact outage ranges.
5. Enable Web Push notifications or subscribe through Telegram.
6. The backend checks upcoming schedule changes and sends notifications roughly one hour before a planned outage.

The current frontend supports queues `1.1` through `6.2` and refreshes the schedule every five minutes.

## Repository structure

```text
Likhtarychok/
├── backend/
│   ├── bots/
│   │   ├── help_bot/          # Help / administration Telegram bot
│   │   └── notifier_bot/      # Telegram notification bot
│   ├── db/
│   │   └── orm/               # SQLAlchemy ORM layer
│   ├── proto/                  # Protobuf definitions / generated code
│   ├── untils/                 # Parsing, cache, subscriptions, notifications, helpers
│   ├── .env.example
│   ├── Dockerfile
│   ├── main.py                # FastAPI application entry point
│   └── requirements.txt
│
└── frontend/
    ├── public/                 # Static assets and service worker
    ├── src/
    │   ├── components/
    │   ├── context/
    │   ├── pages/
    │   │   ├── Faq/
    │   │   ├── Graph/
    │   │   ├── Home/
    │   │   ├── Info/
    │   │   └── Privacy/
    │   └── main.jsx
    ├── package.json
    └── vite.config.js
```

The backend is started by Uvicorn on port `8000` in the included Dockerfile. The frontend is a standard Vite application with React Router and is currently organized into home, graph, information, FAQ, and privacy pages.

## Technology stack

### Frontend

- React 19
- React Router 7
- Vite 7
- Browser Notifications / Web Push
- Service Worker

The frontend package currently defines `dev`, `build`, `lint`, and `preview` scripts.

### Backend

- Python 3.12
- FastAPI
- Uvicorn
- aiogram 3
- APScheduler
- SQLAlchemy + asyncpg
- Redis
- BeautifulSoup 4
- aiohttp
- `pywebpush`
- Protobuf / gRPC-Web compatible status endpoint

The backend dependencies are pinned in `backend/requirements.txt`.

## Installation

### Prerequisites

- Python 3.12+
- Node.js and npm
- A PostgreSQL-compatible database if persistent DB storage is enabled
- Redis if Redis-backed state/cache is enabled
- Telegram bot tokens if Telegram features are enabled
- VAPID keys for Web Push notifications

## Backend setup

```bash
git clone https://github.com/younici/Likhtarychok.git
cd Likhtarychok/backend

python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Create a `.env` file from the included example:

```bash
cp .env.example .env
```

Then start the API:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

The application loads environment variables with `python-dotenv`. During startup it initializes the scheduler, optionally initializes the database and Redis, loads stored subscriptions, and starts the enabled Telegram bots.

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

For a production build:

```bash
npm run build
npm run preview
```

The production environment file currently points the frontend to `/api` as its API base.

## Environment variables

The backend ships with `backend/.env.example` containing the complete configuration surface.

| Variable | Purpose |
|---|---|
| `VAPID_PUBLIC_KEY` | Public VAPID key used by browser push subscriptions |
| `VAPID_PRIVATE_KEY` | Private VAPID key used to send push notifications |
| `REDIS_URL` | Redis connection URL |
| `REDIS_ONLINE` | Enable / disable Redis integration |
| `DB_ONLINE` | Enable / disable database integration |
| `DB_USER` | Database username |
| `DB_PASS` | Database password |
| `DB_HOST` | Database host |
| `DB_PORT` | Database port |
| `DB_NAME` | Database name |
| `NOTIFY_PASS` | Password for the authenticated notification endpoint |
| `NOTIFY_URL` | Public URL used by internal notification helpers |
| `ONLINE` | Enable scheduled online notification processing |
| `NOTIFY_BOT_TOKEN` | Telegram notifier bot token |
| `NOTIFY_BOT_ONLINE` | Enable the notification bot |
| `HELP_BOT_TOKEN` | Telegram help bot token |
| `HELP_BASE_ADMIN_ID` | Base administrator Telegram ID |
| `HELP_BOT_ONLINE` | Enable the help bot |
| `BOT_ADMINS` | Comma-separated Telegram administrator IDs |
| `CAN_CACHE` | Enable schedule caching |

### Example configuration

```env
VAPID_PUBLIC_KEY=your_public_vapid_key
VAPID_PRIVATE_KEY=your_private_vapid_key

REDIS_URL=redis://:password@127.0.0.1:6379/0
REDIS_ONLINE=true

DB_ONLINE=true
DB_USER=likhtarychok
DB_PASS=change_me
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=likhtarychok

NOTIFY_PASS=change_me
NOTIFY_URL=https://example.com

ONLINE=true

NOTIFY_BOT_TOKEN=123456:your_token
NOTIFY_BOT_ONLINE=true

HELP_BOT_TOKEN=123456:your_token
HELP_BASE_ADMIN_ID=123456789
HELP_BOT_ONLINE=true

BOT_ADMINS=123456789,987654321
CAN_CACHE=true
```

## API

The FastAPI application uses `/api` as its base path.

### Get VAPID public key

```http
GET /api/vapid_public_key
```

Returns the public VAPID key needed by the frontend to create a Web Push subscription.

### Subscribe to Web Push

```http
POST /api/subscribe
Content-Type: application/json
```

Example payload:

```json
{
  "queue": "3.1",
  "subscription": {
    "endpoint": "https://push-service.example/endpoint",
    "keys": {
      "p256dh": "...",
      "auth": "..."
    }
  }
}
```

The backend normalizes the queue identifier, stores the subscription in memory, persists it to the database when enabled, and synchronizes subscription state to Redis when available.

### Unsubscribe

```http
POST /api/unsubscribe
Content-Type: application/json
```

Payload:

```json
{
  "subscription": {
    "endpoint": "https://push-service.example/endpoint",
    "keys": {
      "p256dh": "...",
      "auth": "..."
    }
  }
}
```

### Send a notification manually

```http
POST /api/notify
Content-Type: application/json
```

Example:

```json
{
  "title": "Test notification",
  "message": "This is a test.",
  "pass": "your_notify_password"
}
```

The endpoint is protected by `NOTIFY_PASS`. Notifications can be delivered through both Web Push and Telegram subscriptions.

### Get schedule status

```http
GET /api/status?queue=3.1
```

The response contains the normalized status for the selected queue.

### gRPC-Web status endpoint

```http
POST /api/grpc/StatusService/GetStatus
Content-Type: application/grpc-web+proto
```

The frontend uses this endpoint to request queue status. It sends a protobuf-encoded queue request wrapped in a gRPC-Web frame, and the backend responds with a protobuf status payload.

## Schedule parsing and normalization

The source parser fetches the official schedule page asynchronously and extracts the table row corresponding to the selected queue. The HTML cells are then converted into binary status values:

- `0` — no planned outage
- `1` — outage / unavailable electricity

The parser can consume 24-hour or 48-half-hour representations, while the frontend normalizes the data to 48 half-hour slots for display.

## Caching

Caching is controlled by `CAN_CACHE`.

When caching is enabled, the parser reads the stored source representation through the cache layer instead of fetching the upstream page for every request. The backend also schedules a cache refresh job every five minutes.

This helps reduce repeated upstream requests while keeping the schedule reasonably fresh.

## Notifications

Likhtarychok supports two notification channels:

### Web Push

The browser registers `/sw.js`, creates a Push API subscription using the backend-provided VAPID public key, and sends the subscription to `/api/subscribe`.

### Telegram

Telegram subscriptions are associated with a Telegram user ID and a selected outage queue. The notifier selects subscriptions for the affected queue and sends the notification through the dedicated notifier bot. Invalid subscriptions can be removed from persistent storage.

### Scheduled outage reminders

The backend scheduler runs the notification check every 30 minutes when `ONLINE=true`. For half-hourly schedules, it looks ahead by approximately one hour and sends a reminder when an upcoming transition into an outage is detected.

## Docker

The backend includes a production-oriented Dockerfile based on `python:3.12-slim`.

It:

- installs the Python dependencies
- configures the container timezone as `Europe/Kyiv`
- exposes ports `8000` and `8338`
- starts Uvicorn on port `8000`

citeturn374859view0

Build the backend image with:

```bash
cd backend
docker build -t likhtarychok-backend .
```

Run it with:

```bash
docker run --rm \
  --name likhtarychok-backend \
  --env-file .env \
  -p 8000:8000 \
  likhtarychok-backend
```

## Production deployment

A typical deployment consists of:

```text
Internet
   |
   v
Reverse proxy / TLS
   |
   +--------------------+
   |                    |
   v                    v
Frontend             /api -> FastAPI
                          |
                          +--> PostgreSQL
                          +--> Redis
                          +--> Telegram API
                          +--> Official schedule source
```

A reverse proxy can serve the built frontend and forward `/api/*` requests to the backend. This matches the current production frontend configuration, which uses `/api` as its API base.

For production, also configure:

- HTTPS for the website and Web Push
- secure VAPID keys
- a persistent PostgreSQL database if subscriptions must survive restarts
- Redis if shared cache / state is required
- valid Telegram bot tokens
- firewall rules for the backend and database
- a process supervisor or container restart policy

## Telegram bots

The backend contains dedicated bot packages for:

- `help_bot` — help / administration functionality
- `notifier_bot` — delivery of outage notifications

Bot startup is controlled by the corresponding `*_ONLINE` flags and tokens in the environment configuration.

## Development notes

The project is intentionally split so that frontend and backend can be developed independently.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Backend

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Linting and production build

```bash
cd frontend
npm run lint
npm run build
```

## Data freshness

The frontend refreshes the selected queue every five minutes. The backend can also maintain a five-minute cache refresh cycle. This is intended to keep the UI responsive while avoiding unnecessary repeated scraping of the upstream source.

Actual outage schedules are controlled by the upstream electricity provider. Likhtarychok should therefore be treated as a convenience layer over the official source, not as an independent authority.

## Security considerations

The application handles several sensitive values, including database credentials, Redis credentials, Telegram bot tokens, VAPID private keys, and the notification endpoint password.

Recommended practices:

- Never commit `.env` files or real secrets
- Keep `VAPID_PRIVATE_KEY` private
- Use strong random values for `NOTIFY_PASS`
- Restrict access to PostgreSQL and Redis
- Run the public API behind HTTPS
- Restrict Telegram administration to trusted IDs
- Keep bot tokens out of client-side code
- Rotate secrets if they are ever exposed

The `/api/notify` endpoint already checks `NOTIFY_PASS`, while ordinary schedule/status endpoints are designed to be publicly consumable by the frontend.

## Known limitations

- The parser depends on the HTML structure of the upstream Zhytomyroblenergo page. A source-site redesign may require parser changes.
- Schedule interpretation depends on the upstream representation and can vary between 24-slot and 48-slot data.
- Web Push requires browser support and a secure origin in normal production deployments.
- Notification delivery depends on third-party browser push services and the Telegram API.
- The project currently exposes the FastAPI application without its built-in OpenAPI/Swagger documentation enabled.

## License

No explicit `LICENSE` file is currently visible in the repository root. Add a license file before publishing or redistributing the project under a specific open-source license.

## Contributing

Issues and pull requests are welcome.

When contributing:

1. Keep credentials and production configuration out of Git.
2. Preserve compatibility with the existing frontend/backend API contract.
3. Avoid unnecessary changes to the upstream parser unless the source format has actually changed.
4. Keep queue mapping and notification logic backward-compatible.
5. Update this README when introducing new services, environment variables, or public API endpoints.

## Project

Repository: https://github.com/younici/Likhtarychok
