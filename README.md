# Newsletter Builder

Multi-step newsletter builder for Bader and lead approvers.

- **Next.js** (`apps/web`) — wizard UI, status board, archive, premium settings
- **FastAPI** (`apps/api`) — REST API, uploads, Slack, Mailchimp, AI
- **Postgres** — source of truth (via Docker Compose)
- **Mailchimp** — templates / drag-drop editor, schedule, opens & clicks
- **Slack** — Approve / Request changes buttons for the lead

## Quick start

```bash
# 1. API (SQLite by default — no Docker required)
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../../.env.example ../../.env
python -m app.seed
uvicorn app.main:app --reload --port 8000

# Optional Postgres instead of SQLite:
# docker compose up -d
# set DATABASE_URL=postgresql+psycopg://newsletter:newsletter@localhost:5432/newsletter_builder
# pip install 'psycopg[binary]>=3.2.4'
# alembic upgrade head && python -m app.seed

# 2. Web (new terminal)
cd apps/web
npm install
npm run dev
```

Open http://localhost:3000

Demo tokens (send as `Authorization: Bearer …`):

| Role  | Token             |
|-------|-------------------|
| Bader | `bader-demo-token` |
| Lead  | `lead-demo-token`  |

The web app stores the role in local storage and attaches the token automatically.

## Wizard flow

1. **Intake** — section count + types (news, featured story, tips, events, CTA)
2. **Layouts** — layout variant per section
3. **Content** — images, AI text (premium), edit/save, lead comments
4. **Chrome** — background, auto headline + date
5. **Preview** — send for Slack review
6. **Review** — pending review log + section comments
7. **Send** — sync to Mailchimp editor, confirm community send
8. **Archive** — last 12 months

## Statuses

`drafting` → `in_review` → `changes_requested` | `review_complete` → `ready_to_send` → `sent`

## Premium

Workspace plan `premium` unlocks AI generation options and brand customization under **Settings → Premium**.
