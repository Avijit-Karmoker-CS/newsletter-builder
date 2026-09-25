"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  STATUS_LABELS,
  api,
  type NewsletterStatus,
  type NewsletterSummary,
} from "@/lib/api";
import { StatusPill } from "@/components/Shell";

const GROUPS: { title: string; statuses: NewsletterStatus[]; empty: string }[] = [
  {
    title: "Drafting",
    statuses: ["drafting"],
    empty: "No drafts yet.",
  },
  {
    title: "In review / changes requested",
    statuses: ["in_review", "changes_requested"],
    empty: "Nothing waiting on the lead.",
  },
  {
    title: "Review complete — awaiting Bader confirm",
    statuses: ["review_complete", "ready_to_send"],
    empty: "No approved issues waiting to send.",
  },
  {
    title: "Recently sent",
    statuses: ["sent"],
    empty: "No sends yet.",
  },
];

export default function DashboardPage() {
  const [items, setItems] = useState<NewsletterSummary[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .listNewsletters()
      .then(setItems)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const resumable = items.filter((n) => n.status !== "sent" && n.status !== "denied");
  const latest = [...resumable].sort((a, b) => (a.updated_at < b.updated_at ? 1 : -1))[0];

  return (
    <div className="stack">
      <div className="hero row" style={{ justifyContent: "space-between" }}>
        <div>
          <h1>Dashboard</h1>
          <p className="lede">
            Track drafts, Slack reviews, lead comments, and issues waiting to
            go out through Mailchimp.
          </p>
        </div>
        <Link className="button primary" href="/newsletters/new" style={{ textDecoration: "none" }}>
          Start new newsletter
        </Link>
      </div>

      {!loading && latest && (
        <section className="panel stack">
          <h2>Continue where you left off</h2>
          <p className="muted">
            Drafts, reviews, comments, and your Mailchimp and Slack setup stay
            saved on this computer.
          </p>
          <Link href={continueHref(latest)} style={{ fontWeight: 700 }}>
            {latest.title}
          </Link>
        </section>
      )}

      {loading && <p className="muted">Loading…</p>}
      {error && <p className="error">{error}</p>}

      <div className="grid grid-2">
        {GROUPS.map((group) => {
          const rows = items.filter((n) => group.statuses.includes(n.status));
          return (
            <section key={group.title} className="panel">
              <h2>{group.title}</h2>
              {rows.length === 0 ? (
                <p className="muted">{group.empty}</p>
              ) : (
                <ul className="list">
                  {rows.map((n) => (
                    <li key={n.id} className="list-item">
                      <div>
                        <strong>{n.title}</strong>
                        <div className="muted" style={{ fontSize: "0.9rem" }}>
                          {STATUS_LABELS[n.status]} · {n.section_count} sections
                        </div>
                      </div>
                      <div className="row">
                        <StatusPill status={n.status} />
                        <Link href={openHref(n)}>Open</Link>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          );
        })}
      </div>
    </div>
  );
}

function openHref(n: NewsletterSummary): string {
  if (n.status === "sent") return `/newsletters/${n.id}/preview?archive=1`;
  return continueHref(n);
}

function continueHref(n: NewsletterSummary): string {
  if (
    n.last_step &&
    ["layouts", "content", "chrome", "preview", "review", "send"].includes(n.last_step)
  ) {
    return `/newsletters/${n.id}/${n.last_step}`;
  }
  switch (n.status) {
    case "drafting":
      return `/newsletters/${n.id}/layouts`;
    case "in_review":
    case "changes_requested":
      return `/newsletters/${n.id}/review`;
    case "review_complete":
    case "ready_to_send":
      return `/newsletters/${n.id}/send`;
    case "sent":
      return `/newsletters/${n.id}/preview`;
    case "denied":
      return `/newsletters/${n.id}/review`;
    default:
      return `/newsletters/${n.id}/preview`;
  }
}
