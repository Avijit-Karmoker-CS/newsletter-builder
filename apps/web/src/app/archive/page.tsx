"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { STATUS_LABELS, api, type NewsletterSummary } from "@/lib/api";
import { StatusPill } from "@/components/Shell";

export default function ArchivePage() {
  const [items, setItems] = useState<NewsletterSummary[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api.archive().then(setItems).catch((e) => setError(e.message));
  }, []);

  return (
    <div className="stack">
      <div className="hero">
        <h1>Archive</h1>
        <p className="lede">
          Newsletters from the last 12 months that are review-complete or sent,
          with Mailchimp campaign links when available.
        </p>
      </div>

      <section className="panel">
        {error && <p className="error">{error}</p>}
        {items.length === 0 && !error ? (
          <p className="muted">No archived issues yet.</p>
        ) : (
          <ul className="list">
            {items.map((n) => (
              <li key={n.id} className="list-item">
                <div>
                  <strong>{n.title}</strong>
                  <div className="muted">
                    {n.issue_date || "No date"} · {STATUS_LABELS[n.status]}
                  </div>
                </div>
                <div className="row">
                  <StatusPill status={n.status} />
                  <Link href={`/newsletters/${n.id}/preview`}>Open</Link>
                  {n.mailchimp_editor_url && (
                    <a href={n.mailchimp_editor_url} target="_blank" rel="noreferrer">
                      Mailchimp
                    </a>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
