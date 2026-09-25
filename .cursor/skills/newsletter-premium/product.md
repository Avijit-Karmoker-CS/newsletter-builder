# Product facts

Use these names. Do not rename them in the interface.

## People

- **Bader** signs in, builds the issue, and sends it.
- **Lead** receives the review email and opens `/r/{token}`. No Slack send path.

## Wizard

Layouts → Content → Chrome → Preview → Review → Send.

Content search returns clips from Wikipedia, Wikinews, Wikiquote, Wikidata, and OpenAlex. Choosing a clip clears the result list before insert.

## Review buckets

- **Pending review log:** `in_review` and `changes_requested`. Open comments stay here until Bader sends the update back.
- **Lead approved:** `review_complete`. Send goes to the Mailchimp page.
- **Lead denied:** `denied`. Discarded at the end of that day, America/Halifax.

Urgent follow-up uses the time the review was requested, after two hours, and emails the lead.

## Mailchimp

Sync stores HTML on a campaign. A campaign id that starts with `demo-` means no API key or audience id is configured. Confirm community send sets status `sent` and `sent_at`.

## Accounts and plan

Signup stores sign-in email, password, Mailchimp email, lead email, and AI tool `claude` or `cursor`. New workspaces start on premium. Premium unlocks Generate with AI and brand settings (color, headline style, default background).

## Email

Review mail uses SMTP when `SMTP_HOST` is set. Otherwise the first message to a new lead address asks them to activate the form, and the next send carries the review link. `WEB_APP_URL` is the host used in that link.
