"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { SECTION_LABELS, api, assetUrl, type Newsletter } from "@/lib/api";
import { StatusPill, WizardNav, useLeaveFinishedWizard } from "@/components/Shell";

export default function SendPage() {
  const { id } = useParams<{ id: string }>();
  const [nl, setNl] = useState<Newsletter | null>(null);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.getNewsletter(id).then(setNl).catch((e) => setError(e.message));
  }, [id]);

  async function sync() {
    if (!nl) return;
    setBusy(true);
    setError("");
    try {
      const result = await api.syncMailchimp(nl.id);
      const updated = await api.getNewsletter(nl.id);
      setNl(updated);
      setMsg(
        result.demo
          ? "Demo sync complete — open the Mailchimp editor URL below."
          : "Campaign synced to Mailchimp."
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sync failed");
    } finally {
      setBusy(false);
    }
  }

  async function confirm() {
    if (!nl) return;
    setBusy(true);
    try {
      const updated = await api.confirmSent(nl.id);
      setNl(updated);
      setMsg("Marked as sent to the community. Opens/clicks stay in Mailchimp.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally {
      setBusy(false);
    }
  }

  useLeaveFinishedWizard(nl?.status);

  if (!nl && !error) return <p className="muted">Loading…</p>;
  if (!nl) return <p className="error">{error}</p>;
  if (nl.status === "sent") {
    return <p className="muted">This issue is sent. Opening the dashboard…</p>;
  }

  const canSync = nl.status === "review_complete" || nl.status === "ready_to_send";

  return (
    <div className="stack">
      <WizardNav id={nl.id} step="send" />
      <div className="hero row" style={{ justifyContent: "space-between" }}>
        <div>
          <h1>Send to community</h1>
          <p className="lede">
            Read the final copy below, then sync it to Mailchimp and confirm the
            community send.
          </p>
        </div>
        <StatusPill status={nl.status} />
      </div>

      <div className="preview-shell">
        <div
          className="preview-hero"
          style={{
            backgroundImage: nl.background_url
              ? `linear-gradient(rgba(15,30,28,0.45), rgba(15,30,28,0.55)), url(${assetUrl(nl.background_url)})`
              : undefined,
          }}
        >
          <h2 style={{ margin: 0 }}>{nl.headline || nl.title}</h2>
          <p style={{ marginTop: "0.5rem" }}>{nl.issue_date}</p>
        </div>
        {nl.sections.map((section) => (
          <div key={section.id} className="preview-section">
            <h3 style={{ marginTop: 0 }}>
              {section.title || SECTION_LABELS[section.section_type]}
            </h3>
            <p style={{ whiteSpace: "pre-wrap" }}>{section.body}</p>
          </div>
        ))}
      </div>

      <section className="panel stack">
        <h2>Mailchimp</h2>
        <p className="muted">
          Templates, drag-and-drop editing, schedules, automations, opens, and
          clicks live in Mailchimp — this app pushes your reviewed content.
        </p>
        <div className="row">
          <button className="primary" type="button" disabled={!canSync || busy} onClick={sync}>
            Sync to Mailchimp campaign
          </button>
          {nl.mailchimp_editor_url && (
            <a
              className="button secondary"
              href={nl.mailchimp_editor_url}
              target="_blank"
              rel="noreferrer"
              style={{ textDecoration: "none" }}
            >
              Open Mailchimp editor
            </a>
          )}
        </div>
        {nl.mailchimp_campaign_id && (
          <p className="muted">Campaign ID: {nl.mailchimp_campaign_id}</p>
        )}
        <button
          className="secondary"
          type="button"
          disabled={!nl.mailchimp_campaign_id || busy}
          onClick={confirm}
        >
          Confirm community send
        </button>
      </section>

      {msg && <p className="success">{msg}</p>}
      {error && <p className="error">{error}</p>}
    </div>
  );
}
