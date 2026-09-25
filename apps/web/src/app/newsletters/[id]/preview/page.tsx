"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  SECTION_LABELS,
  api,
  assetUrl,
  getRole,
  type Newsletter,
} from "@/lib/api";
import { StatusPill, WizardNav } from "@/components/Shell";

export default function PreviewPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [nl, setNl] = useState<Newsletter | null>(null);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [role, setRoleState] = useState<"bader" | "lead">("bader");

  useEffect(() => {
    setRoleState(getRole());
    api.getNewsletter(id).then(setNl).catch((e) => setError(e.message));
  }, [id]);

  async function sendForReview() {
    if (!nl) return;
    setBusy(true);
    setError("");
    try {
      const updated = await api.requestReview(nl.id);
      setNl(updated);
      setMsg("Sent to lead via Slack (demo logs if Slack is not configured).");
      router.push(`/newsletters/${nl.id}/review`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally {
      setBusy(false);
    }
  }

  async function approve() {
    if (!nl) return;
    setBusy(true);
    try {
      const updated = await api.approveReview(nl.id);
      setNl(updated);
      setMsg("Approved.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally {
      setBusy(false);
    }
  }

  if (!nl && !error) return <p className="muted">Loading…</p>;
  if (!nl) return <p className="error">{error}</p>;

  return (
    <div className="stack">
      <WizardNav id={nl.id} step="preview" />
      <div className="hero row" style={{ justifyContent: "space-between" }}>
        <div>
          <h1>Preview</h1>
          <p className="lede">
            Review the full draft, then send it to your lead for Slack approval.
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

      <div className="row">
        {role === "bader" && (
          <button className="primary" type="button" disabled={busy} onClick={sendForReview}>
            Send preview for review
          </button>
        )}
        {role === "lead" && (
          <button className="primary" type="button" disabled={busy} onClick={approve}>
            Approve newsletter
          </button>
        )}
        <button
          className="secondary"
          type="button"
          onClick={() => router.push(`/newsletters/${nl.id}/review`)}
        >
          Open review log
        </button>
      </div>

      {msg && <p className="success">{msg}</p>}
      {error && <p className="error">{error}</p>}
    </div>
  );
}
