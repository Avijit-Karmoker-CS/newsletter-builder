"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type NewsletterSummary } from "@/lib/api";
import { WizardNav, useLeaveFinishedWizard } from "@/components/Shell";

const TWO_HOURS = 2 * 60 * 60 * 1000;

export default function ReviewPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [items, setItems] = useState<NewsletterSummary[]>([]);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now());

  function load() {
    return api
      .listNewsletters()
      .then(setItems)
      .catch((e) => setError(e.message));
  }

  useEffect(() => {
    let cancelled = false;
    api
      .listNewsletters()
      .then((rows) => {
        if (!cancelled) setItems(rows);
      })
      .catch((e) => {
        if (!cancelled) setError(e.message);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 30000);
    return () => window.clearInterval(timer);
  }, []);

  async function followUp(newsletterId: string) {
    setBusyId(newsletterId);
    setError("");
    try {
      const updated = await api.urgentReview(newsletterId);
      await load();
      // #region agent log
      fetch('http://127.0.0.1:7538/ingest/6f030dbc-997f-4bbb-bb1f-a9b253a980e2',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'f3ff1c'},body:JSON.stringify({sessionId:'f3ff1c',location:'review/page.tsx:followUp',message:'urgent emailed lead',data:{emailed:true,hasShare:Boolean(updated.slack_share_url)},timestamp:Date.now(),hypothesisId:'E',runId:'post-fix'})}).catch(()=>{});
      // #endregion
      setMsg(
        `Urgent review sent to ${updated.lead_slack_email}. They open the link in that email and approve. It then appears under Lead approved.`
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Follow-up failed");
    } finally {
      setBusyId(null);
    }
  }

  async function sendBack(newsletterId: string) {
    setBusyId(newsletterId);
    setError("");
    try {
      const updated = await api.resubmitReview(newsletterId);
      await load();
      setMsg(
        `Updated newsletter sent to ${updated.lead_slack_email} for approval. After they approve, it appears under Lead approved.`
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not send the newsletter back");
    } finally {
      setBusyId(null);
    }
  }

  async function sendNewsletter(newsletterId: string) {
    setBusyId(newsletterId);
    setError("");
    try {
      await api.releaseToCommunity(newsletterId);
      router.push(`/newsletters/${newsletterId}/send`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Send failed");
      setBusyId(null);
    }
  }

  const currentStatus = items.find((item) => item.id === id)?.status;
  useLeaveFinishedWizard(currentStatus);

  const pending = items.filter(
    (item) => item.status === "in_review" || item.status === "changes_requested"
  );
  const approved = items.filter((item) => item.status === "review_complete");
  const denied = items.filter((item) => item.status === "denied");

  if (currentStatus === "sent") {
    return <p className="muted">This issue is sent. Opening the dashboard…</p>;
  }

  return (
    <div className="stack">
      <WizardNav id={id} step="review" />
      <div className="hero">
        <h1>Review</h1>
        <p className="lede">
          Each row is a whole newsletter sent to the lead. Approved newsletters
          move to Lead approved. Change requests stay here. Denials stay under
          Lead denied until the end of the day.
        </p>
      </div>

      <section className="panel stack">
        <h2>Pending review log</h2>
        {error && <p className="error">{error}</p>}
        {pending.length === 0 ? (
          <p className="muted">No newsletters are waiting on the lead.</p>
        ) : (
          <ul className="list">
            {pending.map((item) => {
              const waited = waitedMs(item.review_requested_at || item.created_at, now);
              const notes = item.lead_notes || [];
              return (
                <li key={item.id} className="list-item" style={{ alignItems: "flex-start" }}>
                  <div className="stack" style={{ gap: "0.35rem", flex: 1 }}>
                    <strong>{item.headline || item.title}</strong>
                    <div className="muted">Newsletter month: {issueMonth(item.issue_date)}</div>
                    {notes.length === 0 && (
                      <>
                        <div className="muted">
                          Sent: {sentLabel(item.review_requested_at || item.created_at)}
                        </div>
                        <div className="muted">Waiting: {waitingLabel(waited)}</div>
                      </>
                    )}
                    {notes.map((note) => (
                      <div key={`${note.section_id}-${note.body}`} className="comment">
                        <strong>Lead comment · {note.section_title}</strong>
                        <p style={{ margin: "0.35rem 0" }}>{note.body}</p>
                        <Link href={`/newsletters/${item.id}/content?section=${note.section_id}`}>
                          Review comment
                        </Link>
                      </div>
                    ))}
                  </div>
                  {notes.length > 0 ? (
                    <button
                      type="button"
                      className="primary"
                      disabled={busyId === item.id}
                      onClick={() => sendBack(item.id)}
                    >
                      Send to lead for approval
                    </button>
                  ) : (
                    waited > TWO_HOURS && (
                      <button
                        type="button"
                        className="secondary"
                        disabled={busyId === item.id}
                        onClick={() => followUp(item.id)}
                      >
                        Urgent follow-up
                      </button>
                    )
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <section className="panel stack">
        <h2>Lead approved</h2>
        {approved.length === 0 ? (
          <p className="muted">No newsletters have been approved by the lead yet.</p>
        ) : (
          <ul className="list">
            {approved.map((item) => (
              <li key={item.id} className="list-item">
                <div>
                  <strong>{item.headline || item.title}</strong>
                  <div className="muted">Newsletter month: {issueMonth(item.issue_date)}</div>
                </div>
                <div className="row">
                  <Link href={`/newsletters/${item.id}/preview`}>Review</Link>
                  <button
                    type="button"
                    className="primary"
                    disabled={busyId === item.id}
                    onClick={() => sendNewsletter(item.id)}
                  >
                    Send
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="panel stack">
        <h2>Lead denied</h2>
        {denied.length === 0 ? (
          <p className="muted">No denied newsletters. These are removed after the day they were denied.</p>
        ) : (
          <ul className="list">
            {denied.map((item) => (
              <li key={item.id} className="list-item">
                <div>
                  <strong>{item.headline || item.title}</strong>
                  <div className="muted">Newsletter month: {issueMonth(item.issue_date)}</div>
                  <div className="muted">Denied: {sentLabel(item.denied_at || item.updated_at)}</div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {msg && <p className="success">{msg}</p>}
    </div>
  );
}

function issueMonth(issueDate: string | null) {
  if (!issueDate) return "No issue month";
  return new Date(`${issueDate}T12:00:00`).toLocaleString(undefined, {
    month: "long",
    year: "numeric",
  });
}

function asUtc(value: string) {
  const trimmed = value.trim().replace(" ", "T");
  if (/[zZ]$|[+-]\d{2}:\d{2}$/.test(trimmed)) return new Date(trimmed);
  return new Date(`${trimmed}Z`);
}

function sentLabel(value: string | null | undefined) {
  if (!value) return "Not sent yet";
  return asUtc(value).toLocaleString();
}

function waitedMs(value: string | null | undefined, now: number) {
  if (!value) return 0;
  return Math.max(0, now - asUtc(value).getTime());
}

function waitingLabel(ms: number) {
  const minutes = Math.floor(ms / 60000);
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? "" : "s"}`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (!rest) return `${hours} hour${hours === 1 ? "" : "s"}`;
  return `${hours} hour${hours === 1 ? "" : "s"} ${rest} minute${rest === 1 ? "" : "s"}`;
}
