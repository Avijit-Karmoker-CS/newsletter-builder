# Newsletter Builder

Premium customer work happens in this repo. Bader builds the newsletter. The lead reviews it from an email link. Mailchimp receives the finished HTML after approval.

Before drafting copy or editing review, search, voice, or send code, read `.cursor/skills/newsletter-premium/SKILL.md` and `.cursor/skills/newsletter-premium/product.md`.

## Keep intact

- One signed-in user, Bader. The lead never gets an in-app role.
- Review is email, then approve, deny, or a section comment.
- Search stays on Wikipedia, Wikinews, Wikiquote, Wikidata, and OpenAlex.
- Voice stays on typed fields only.
- Mailchimp sync does not email subscribers. Confirm community send only marks the issue sent.
- Sent issues leave the wizard. Denied issues drop off at the end of the day in America/Halifax.

## Layout

- `apps/web` — Next.js 15, React 19, TypeScript. Browser calls `/backend/...`.
- `apps/api` — FastAPI, SQLAlchemy, SQLite. Python 3.9: use `from __future__ import annotations` before `X | Y` types.
- `exports/Monthly-community-letter.pdf` — a sent five-section issue.

Do not commit `.env`, `*.db`, or `apps/api/uploads/`.
