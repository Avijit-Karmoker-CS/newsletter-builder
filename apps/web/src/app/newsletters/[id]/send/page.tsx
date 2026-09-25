"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type Newsletter } from "@/lib/api";
import { StatusPill, WizardNav } from "@/components/Shell";

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

  if (!nl && !error) return <p className="muted">Loading…</p>;
  if (!nl) return <p className="error">{error}</p>;

  const canSync =
    nl.status === "review_complete" ||
    nl.status === "ready_to_send" ||
    nl.status === "sent";

  return (
    <div className="stack">
      <WizardNav id={nl.id} step="send" />
      <div className="hero row" style={{ justifyContent: "space-between" }}>
        <div>
          <h1>Send to community</h1>
          <p className="lede">
            Sync content into Mailchimp for final template polish, schedule, and
            tracking. Confirm here after you send.
          </p>
        </div>
        <StatusPill status={nl.status} />
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
          disabled={!nl.mailchimp_campaign_id || busy || nl.status === "sent"}
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
