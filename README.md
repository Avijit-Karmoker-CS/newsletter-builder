# Newsletter Builder

Bader builds a newsletter in the browser. The lead gets an email with a link, then approves it, denies it, or asks for changes. Approved issues can be copied into Mailchimp.

A new person can have the site open in about 15–30 minutes. The first Docker build is the slow part.

A sent five-section issue, Monthly community letter (September 24, 2026), is in [exports/Monthly-community-letter.pdf](exports/Monthly-community-letter.pdf).

## What you need

- A computer with [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- Git
- About 2 GB of free disk space
- A browser

You do not need Python or Node for this path. Those are only for local development, further down.

## 1. Get the code

```bash
git clone https://github.com/Avijit-Karmoker-CS/newsletter-builder.git
cd newsletter-builder
```

## 2. Create the settings file

```bash
cp .env.example .env
```

Open `.env` and set the address people will type into a browser.

For a trial on this computer only:

```bash
WEB_APP_URL=http://localhost:3000
CORS_ORIGINS=http://localhost:3000
```

Review links are built from `WEB_APP_URL`. If the lead will open the link on another computer, set both values to an address that computer can reach, such as `http://192.168.1.20:3000` on the same network or `https://your-public-address` on the internet.

Leave the `SMTP_*` lines empty for the first run. Mail still goes out. The lead’s first message is an activation email. After they click **Activate Form**, later review links arrive normally.

To send straight from your own mailbox instead, fill in:

```bash
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=you@example.com
SMTP_PASSWORD=your-mail-password
SMTP_FROM=you@example.com
SMTP_TLS=true
```

Use port `465` for providers that require SSL. Leave `SMTP_TLS=true` for port `587`.

Mailchimp and AI keys can stay empty. The app still runs. Mailchimp then uses a demo campaign, and AI text uses a local draft until a key is added.

## 3. Start the app

```bash
docker compose up --build -d
```

The first build often takes 5–10 minutes. When it finishes, open:

http://localhost:3000

If that page does not load, check that Docker Desktop is running, then:

```bash
docker compose ps
docker compose logs --tail=50
```

Both `api` and `web` should be running. The site is served on port `3000`.

Stop it later with:

```bash
docker compose down
```

Accounts and newsletters stay in Docker’s `appdata` volume. `docker compose down` does not delete them. `docker compose down -v` does.

## 4. Create Bader’s account

On the site, choose **Create your account** and fill in:

1. **Sign-in email** — the address Bader uses to log in
2. **Password** — at least 8 characters, entered twice
3. **Mailchimp email** — the address tied to the Mailchimp account
4. **Lead email** — where review requests are sent
5. **AI tool** — Claude or Cursor

Submit the form. You land on the dashboard.

## 5. Send one newsletter and confirm the path

1. Choose **Start new newsletter**. Keep the default title, or type one, and continue.
2. Move through **Layouts**, **Content**, and **Chrome**. On Content, write a short paragraph in each section and save it. Search can pull text from news, quotes, facts, and research.
3. On **Preview**, type the lead’s email and choose **Send newsletter link to the lead**.
4. If email settings were left empty, open the lead inbox and click **Activate Form** in that first message. Return to Preview and send again. The second email contains the review link.
5. Open the link. It looks like `/r/` followed by a code. Approve the newsletter, deny it, or write a change on one section.
6. In the app, open **Review**.
   - Waiting issues stay in **Pending review log**.
   - An approval moves the newsletter to **Lead approved**.
   - A denial moves it to **Lead denied**. Denied issues are removed at the end of the day, America/Halifax.
7. From **Lead approved**, choose **Send**. **Sync to Mailchimp campaign** copies the finished HTML into a campaign. Without a Mailchimp API key, the campaign id starts with `demo-` and nothing is emailed to subscribers. **Confirm community send** marks the issue sent in this app and returns you to the dashboard.

That is a complete setup. The next issue starts from **Start new newsletter**.

## Optional: real Mailchimp

In `.env`:

```bash
MAILCHIMP_API_KEY=your-key-us1
MAILCHIMP_SERVER_PREFIX=us1
MAILCHIMP_LIST_ID=your-audience-id
MAILCHIMP_FROM_NAME=Newsletter
MAILCHIMP_REPLY_TO=you@example.com
```

The server prefix is the suffix on the API key, such as `us1`. Restart after saving:

```bash
docker compose up -d
```

Sync still does not email the audience. It places the newsletter in Mailchimp so Bader can open the editor. **Confirm community send** records the send in this app.

## Optional: AI text

Add one key to `.env`, then restart with `docker compose up -d`.

```bash
OPENAI_API_KEY=sk-...
```

or, for Claude:

```bash
ANTHROPIC_API_KEY=sk-ant-...
```

The account’s AI tool on the signup page should match the key you set. **Generate with AI** is available on a premium workspace. New accounts start on premium.

## Run it from the source code

Use this only when you are changing the app. Install Python 3.9+ and Node.js 22.

```bash
cp .env.example .env
```

Set `WEB_APP_URL=http://localhost:3000` and `CORS_ORIGINS=http://localhost:3000`.

API, in one terminal:

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

On Windows, activate with `.venv\Scripts\activate`.

Web, in a second terminal:

```bash
cd apps/web
npm install
npm run dev
```

Open http://localhost:3000. The browser talks to the API through the site, so you do not open port 8000 yourself.

## If something fails

| What you see | What to do |
| --- | --- |
| Browser cannot open the site | Docker Desktop is stopped, or port 3000 is already in use. Quit the other program or set `WEB_PORT=3001` in `.env`, then run `docker compose up -d` again and open that port. |
| “Could not email the review” and it mentions SMTP | The SMTP values in `.env` are blank or rejected by the mail provider. Fix them and restart, or clear them and use the activation email described in step 5. |
| The lead never sees the review | Check spam. If there was no SMTP setup, the first message is **Activate Form**, not the review. Click it, then send again from Preview. `WEB_APP_URL` must be an address the lead’s computer can open. |
| Mailchimp campaign id starts with `demo-` | No API key or audience id is set. The copy stays inside this app until those values are added. |
| Login says the account already exists | Use **Sign in** with that email. Each email gets one account. |

Newsletters are stored in SQLite on the server. They are not in git. Copy the Docker volume or the local database file if you need a backup.
