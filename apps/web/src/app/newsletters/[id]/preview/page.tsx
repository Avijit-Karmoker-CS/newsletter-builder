"use client";

import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import {
  SECTION_LABELS,
  api,
  assetUrl,
  type LeadOption,
  type Newsletter,
} from "@/lib/api";
import { StatusPill, WizardNav, useLeaveFinishedWizard } from "@/components/Shell";
import { VoiceControl } from "@/components/VoiceControl";

export default function PreviewPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const archiveView = useSearchParams().get("archive") === "1";
  const [nl, setNl] = useState<Newsletter | null>(null);
  const [leads, setLeads] = useState<LeadOption[]>([]);
  const [leadEmail, setLeadEmail] = useState("");
  const [customEmail, setCustomEmail] = useState("");
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.getNewsletter(id).then(setNl).catch((e) => setError(e.message));
    api
      .listLeads()
      .then((rows) => {
        setLeads(rows);
        if (rows[0]) setLeadEmail(rows[0].email);
      })
      .catch(() => {});
  }, [id]);

  const chosenEmail = (leadEmail === "__custom__" ? customEmail : leadEmail).trim();

  async function sendForReview() {
    if (!nl) return;
    if (!chosenEmail) {
      setError("Choose the lead Slack email first.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const updated = await api.requestReview(nl.id, chosenEmail);
      setNl(updated);
      setMsg(
        `Review sent to ${chosenEmail}. They open the link in that email and approve. This newsletter then moves to Lead approved.`
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally {
      setBusy(false);
    }
  }

  useLeaveFinishedWizard(archiveView ? undefined : nl?.status);

  if (!nl && !error) return <p className="muted">Loading…</p>;
  if (!nl) return <p className="error">{error}</p>;
  if (nl.status === "sent" && !archiveView) {
    return <p className="muted">This issue is sent. Opening the dashboard…</p>;
  }

  return (
    <div className="stack">
      {archiveView ? null : <WizardNav id={nl.id} step="preview" />}
      {(nl.status === "review_complete" || nl.status === "ready_to_send") && (
        <p className="success">Lead approved this newsletter.</p>
      )}
      <div className="hero row" style={{ justifyContent: "space-between" }}>
        <div>
          <h1>Preview</h1>
          <p className="lede">
            {archiveView
              ? "This is the copy that was sent. Start a new newsletter from the dashboard to enter the next issue."
              : "This is the full draft. Choose the lead's email, then send every section as a review link to that address."}
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
            <div className="row">
              {section.image_urls?.map((url) => (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  key={url}
                  src={assetUrl(url)}
                  alt=""
                  style={{ maxWidth: 220, borderRadius: 10 }}
                />
              ))}
            </div>
          </div>
        ))}
      </div>

      {!archiveView && <section className="panel stack">
        <h2>Send to the lead</h2>
        <label>
          Lead Slack email
          <select value={leadEmail} onChange={(e) => setLeadEmail(e.target.value)}>
            {leads.map((lead) => (
              <option key={lead.id} value={lead.email}>
                {lead.name} — {lead.email}
              </option>
            ))}
            <option value="__custom__">Other email…</option>
          </select>
        </label>
        {leadEmail === "__custom__" && (
          <label>
            Email on their Slack account
            <VoiceControl value={customEmail} onChange={setCustomEmail}>
              <input
                type="email"
                value={customEmail}
                placeholder="lead@company.com"
                onChange={(e) => setCustomEmail(e.target.value)}
              />
            </VoiceControl>
          </label>
        )}
        <div className="row">
          <button className="primary" type="button" disabled={busy} onClick={sendForReview}>
            {busy ? "Sending…" : "Send newsletter link to the lead"}
          </button>
          <button
            className="secondary"
            type="button"
            onClick={() => router.push(`/newsletters/${nl.id}/review`)}
          >
            Open review
          </button>
        </div>
        {nl.review_token && (
          <p className="muted">
            Lead opens{" "}
            <a href={`/r/${nl.review_token}`}>{`${typeof window !== "undefined" ? window.location.origin : ""}/r/${nl.review_token}`}</a>
            {nl.lead_slack_email ? ` (sent to ${nl.lead_slack_email})` : ""}.
          </p>
        )}
      </section>}

      {msg && <p className="success">{msg}</p>}
      {error && <p className="error">{error}</p>}
    </div>
  );
}
