"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  SECTION_LABELS,
  api,
  getRole,
  type Newsletter,
} from "@/lib/api";
import { StatusPill, WizardNav } from "@/components/Shell";

export default function ReviewPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [nl, setNl] = useState<Newsletter | null>(null);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [role, setRoleState] = useState<"bader" | "lead">("bader");
  const [sectionIndex, setSectionIndex] = useState(1);
  const [comment, setComment] = useState("");

  useEffect(() => {
    setRoleState(getRole());
    let cancelled = false;
    api
      .getNewsletter(id)
      .then((newsletter) => {
        if (!cancelled) setNl(newsletter);
      })
      .catch((e) => {
        if (!cancelled) setError(e.message);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  async function reload() {
    const newsletter = await api.getNewsletter(id);
    setNl(newsletter);
  }

  async function approve() {
    if (!nl) return;
    try {
      await api.approveReview(nl.id);
      setMsg("Approved — Bader can sync to Mailchimp.");
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    }
  }

  async function requestChanges() {
    if (!nl) return;
    try {
      await api.demoRequestChanges(nl.id, sectionIndex, comment);
      setComment("");
      setMsg("Changes requested (Slack button simulation).");
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    }
  }

  if (!nl && !error) return <p className="muted">Loading…</p>;
  if (!nl) return <p className="error">{error}</p>;

  const pendingComments = nl.sections.flatMap((s) =>
    (s.comments || [])
      .filter((c) => !c.resolved)
      .map((c) => ({ ...c, section: s }))
  );

  return (
    <div className="stack">
      <WizardNav id={nl.id} step="review" />
      <div className="hero row" style={{ justifyContent: "space-between" }}>
        <div>
          <h1>Review</h1>
          <p className="lede">
            Pending review log, lead comments per section, and Slack-style
            approve / request-changes actions.
          </p>
        </div>
        <StatusPill status={nl.status} />
      </div>

      <section className="panel stack">
        <h2>Pending review log</h2>
        {nl.review_events.length === 0 ? (
          <p className="muted">No events yet.</p>
        ) : (
          <ul className="list">
            {[...nl.review_events].reverse().map((ev) => (
              <li key={ev.id} className="list-item">
                <div>
                  <strong>{ev.event_type}</strong>
                  <div className="muted">{ev.message}</div>
                </div>
                <span className="muted" style={{ fontSize: "0.85rem" }}>
                  {new Date(ev.created_at).toLocaleString()}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="panel stack">
        <h2>Lead comments on sections</h2>
        {pendingComments.length === 0 ? (
          <p className="muted">No open comments.</p>
        ) : (
          pendingComments.map((c) => (
            <div key={c.id} className="comment">
              <strong>
                Section {c.section.sort_order + 1}:{" "}
                {SECTION_LABELS[c.section.section_type]}
              </strong>
              <p>{c.body}</p>
              <Link href={`/newsletters/${nl.id}/content`}>Edit this section</Link>
            </div>
          ))
        )}
      </section>

      {role === "lead" && (
        <section className="panel stack">
          <h2>Lead actions (Slack buttons)</h2>
          <p className="muted">
            Mirrors Slack Approve / Request changes when the bot is not
            connected.
          </p>
          <div className="row">
            <button type="button" className="primary" onClick={approve}>
              Approve
            </button>
          </div>
          <label>
            Section number
            <input
              type="number"
              min={1}
              max={nl.sections.length}
              value={sectionIndex}
              onChange={(e) => setSectionIndex(Number(e.target.value))}
            />
          </label>
          <label>
            Required changes
            <textarea value={comment} onChange={(e) => setComment(e.target.value)} />
          </label>
          <button
            type="button"
            className="secondary"
            disabled={!comment.trim()}
            onClick={requestChanges}
          >
            Request changes
          </button>
        </section>
      )}

      {msg && <p className="success">{msg}</p>}
      {error && <p className="error">{error}</p>}

      <div className="row">
        <button
          className="primary"
          type="button"
          onClick={() => router.push(`/newsletters/${nl.id}/send`)}
          disabled={
            nl.status !== "review_complete" &&
            nl.status !== "ready_to_send" &&
            nl.status !== "sent"
          }
        >
          Next: send via Mailchimp
        </button>
        <Link href={`/newsletters/${nl.id}/content`}>Back to content edits</Link>
      </div>
    </div>
  );
}
