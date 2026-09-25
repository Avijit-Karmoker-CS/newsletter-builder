# Newsletter Builder

Multi-step newsletter builder for Bader and lead approvers.

- **Next.js** (`apps/web`) — wizard UI, status board, archive, premium settings
- **FastAPI** (`apps/api`) — REST API, uploads, Slack, Mailchimp, AI
- **SQLite** — stored on the server with the site (Postgres is optional)
- **Mailchimp** — templates / drag-drop editor, schedule, opens & clicks
- **Slack** — Approve / Request changes buttons for the lead

## Use it on any computer

People do not install Python or Node. One server runs the site and the API. Each person opens that address, creates an account, and starts a newsletter. Review links use the same address, so a lead on another computer can open them.

1. Copy `.env.example` to `.env`.
2. Set `WEB_APP_URL` to the public address (for example `https://newsletters.example.com`).
3. Set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, and `SMTP_FROM` so review emails can leave the server.
4. Point that address at this machine’s port `3000` (or `WEB_PORT`).
5. Start the site:

```bash
docker compose up --build -d
```

Open `WEB_APP_URL`. Create an account, build a newsletter, and send it to the lead’s email. The lead uses the link in that email.

## Local development

```bash
# API
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../../.env.example ../../.env
uvicorn app.main:app --reload --port 8000

# Web (new terminal)
cd apps/web
npm install
npm run dev
```

Open http://localhost:3000. For local review email, fill in the SMTP settings in `.env` and set `WEB_APP_URL` to the address the lead can actually open.

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
