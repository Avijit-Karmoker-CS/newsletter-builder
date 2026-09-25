---
name: newsletter-premium
description: >-
  Guides premium work in Newsletter Builder for Bader: section copy, verified
  search, lead email review, Mailchimp sync, and code changes that keep those
  flows. Use when editing this repo, drafting a newsletter, or when the user
  mentions Bader, the lead, Mailchimp, preview, review, voice, or premium.
---

# Newsletter premium

Bader is the only signed-in user. The lead is not an account inside the app. The lead opens an email link, then approves, denies, or comments. Keep that split.

Read [product.md](product.md) before changing review, send, search, voice, or Mailchimp behavior.

## Help Bader write

1. Stay inside the open section. Types are news, featured story, tips, events, and call to action.
2. Use saved search clips when Bader asks for facts. Sources are Wikipedia, Wikinews, Wikiquote, Wikidata, and OpenAlex. Do not invent citations.
3. Match the section length already used by Generate with AI: news 80–120 words, featured story 120–180 words, tips as three short paragraphs, events with a date placeholder, call to action as one paragraph with a soft invite.
4. Write plain sentences. No markdown headings inside section body text.
5. Leave voice buttons on every typed field. Do not add voice to passwords, dates, file uploads, color, radios, or the section-count control.

## Help Bader finish an issue

1. Every section is saved before Preview.
2. Preview asks for the lead email and emails one link for the whole newsletter.
3. After the lead approves, Send copies HTML into a Mailchimp campaign. Confirm community send only marks the issue sent here. It does not email the Mailchimp audience.
4. A sent issue opens from the archive as read-only. Continue where you left off skips sent and denied issues.

## When changing code

- Add behavior beside the current wizard. Do not remove a step, status, or button to “simplify” the premium path.
- Python on this machine is 3.9. In `apps/api`, start files with `from __future__ import annotations` before using `str | None`.
- The browser calls `/backend/...`. The Next.js route proxies to the API. Do not point the browser at port 8000.
- Do not commit `.env`, database files, or `apps/api/uploads/`.
