# Deployment Guide

This guide covers the current single-server Web MVP deployment model. It assumes
a Linux server where an administrator deploys NoviScope once for a research
group, then group members register and use the shared web URL.

## Requirements

- Python 3.11 or newer
- Node.js 20 or newer
- PostgreSQL for shared deployment
- HTTPS-capable reverse proxy such as Nginx or Caddy
- A persistent directory for artifacts and future generated files

SQLite is acceptable for local development and smoke testing. Use PostgreSQL for
group usage.

## Environment

Create `.env` from `.env.example` and replace all placeholders:

```bash
cp .env.example .env
```

Required shared-deployment settings:

```bash
NOVISCOPE_DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/noviscope
NOVISCOPE_PROVIDER_SECRET_KEY=<long-random-secret>
NOVISCOPE_SESSION_SECRET_KEY=<different-long-random-secret>
NOVISCOPE_SESSION_COOKIE_SECURE=true
NOVISCOPE_DEV_ADMIN_HEADER_ENABLED=false
NOVISCOPE_DEV_ADMIN_TOKEN=
NOVISCOPE_ARTIFACT_ROOT=/srv/noviscope/artifacts
NOVISCOPE_GITHUB_REPO=kopang0730/NoviScope
NOVISCOPE_GITHUB_BRANCH=main
NOVISCOPE_VERSION_CHECK_TIMEOUT_SECONDS=3
```

For non-SQLite deployments, the app refuses to start with placeholder or weak
provider/session secrets.

Generate secrets with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Backend

Install and run:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn noviscope.main:app --host 127.0.0.1 --port 8000
```

For a production-like service manager, run the same command under systemd,
supervisord, tmux, or another process manager available on the lab server.

The app creates tables on startup. A migration tool is not integrated yet, so
database schema changes should be reviewed carefully before shared deployment.

## Frontend

Build the web app:

```bash
cd web
npm install
npm run build
```

Serve `web/dist` with a reverse proxy and route `/api/` to the backend.

Example Nginx shape:

```nginx
server {
  listen 443 ssl;
  server_name noviscope.example.internal;

  ssl_certificate /etc/ssl/certs/noviscope.pem;
  ssl_certificate_key /etc/ssl/private/noviscope.key;

  location /api/ {
    proxy_pass http://127.0.0.1:8000/;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }

  location / {
    root /srv/noviscope/web/dist;
    try_files $uri /index.html;
  }
}
```

## Bootstrap Admin

The current MVP does not have a first-admin UI. Use the dev admin header only for
initial setup or local smoke tests:

1. Generate a bootstrap token:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```
2. Temporarily set:
   ```bash
   NOVISCOPE_DEV_ADMIN_HEADER_ENABLED=true
   NOVISCOPE_DEV_ADMIN_TOKEN=<generated-token>
   ```
3. Restart the backend.
4. Create a one-use invite:
   ```bash
   curl -s -X POST http://127.0.0.1:8000/admin/invites \
     -H "Content-Type: application/json" \
     -H "X-NoviScope-Dev-Admin: ${NOVISCOPE_DEV_ADMIN_TOKEN}" \
     -d '{"code":"BOOTSTRAP-INVITE","max_uses":1}'
   ```
5. Register the bootstrap user in the web app.
6. Promote that user to admin in PostgreSQL:
   ```sql
   UPDATE "user" SET role = 'admin' WHERE email = 'admin@example.com';
   ```
7. Set `NOVISCOPE_DEV_ADMIN_HEADER_ENABLED=false`, clear
   `NOVISCOPE_DEV_ADMIN_TOKEN`, and restart the backend.

Do not leave the dev admin header enabled in shared deployment.

## Provider Configuration

Users can configure model providers from the web app. Shared providers are for
group-wide use and should be created by administrators. Personal providers are
visible only to the owning user.

Provider responses never return the API key. The stored key is encrypted with
`NOVISCOPE_PROVIDER_SECRET_KEY`, so rotating that secret requires a key-migration
plan.

## Updating a Deployment

The web header always shows the public version number. Admins also get a
read-only update notice from `/admin/version` when the running commit is behind
`NOVISCOPE_GITHUB_REPO` / `NOVISCOPE_GITHUB_BRANCH`. The web app does not run
server commands.

For a non-root deployment user, the recommended update command is:

```bash
./scripts/update-and-build.sh
```

The script refuses to run on a dirty worktree, fetches the configured remote and
branch, fast-forwards only when possible, reinstalls the backend package if
`.venv/bin/python` exists, and rebuilds `web/dist`. To restart after a successful
build:

```bash
NOVISCOPE_RESTART_COMMAND='./restart-noviscope.sh' \
./scripts/update-and-build.sh
```

Manual update flow:

1. Pull the latest code with a fast-forward merge.
2. Review release notes or PR descriptions for database model changes.
3. Stop the backend.
4. Reinstall backend dependencies if `pyproject.toml` changed.
5. Rebuild the frontend if `web/` changed.
6. Start the backend.
7. Run a smoke test:
   - log in;
   - create or open a quest;
   - open provider settings;
   - run a stage that does not need private data, or confirm it blocks with a
     clear reason.

## Known Deployment Gaps

- No first-admin web flow yet.
- No formal database migrations yet.
- No background queue or GPU job isolation yet.
- No built-in HTTPS server; use a reverse proxy.
- No artifact cleanup policy yet.
