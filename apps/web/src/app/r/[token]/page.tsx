"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { SECTION_LABELS, api, assetUrl, type Newsletter } from "@/lib/api";
import { VoiceControl } from "@/components/VoiceControl";

export default function LeadReviewPage() {
  const { token } = useParams<{ token: string }>();
  const [nl, setNl] = useState<Newsletter | null>(null);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<"approved" | "changes" | "denied" | null>(null);

  useEffect(() => {
    api.publicReview(token).then(setNl).catch((e) => setError(e.message));
  }, [token]);

  async function approveSection(sectionId: string) {
    setBusy(true);
    setError("");
    try {
      const updated = await api.publicApproveSection(token, sectionId);
      setNl(updated);
      setMsg("Section approved. Bader can send it from Lead approved.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally {
      setBusy(false);
    }
  }

  async function approve() {
    setBusy(true);
    setError("");
    try {
      const updated = await api.publicApprove(token);
      setNl(updated);
      setDone("approved");
      setMsg("Approved and sent back. Bader will see this newsletter under Lead approved.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally {
      setBusy(false);
    }
  }

  async function deny() {
    setBusy(true);
    setError("");
    try {
      const updated = await api.publicDeny(token);
      setNl(updated);
      setDone("denied");
      setMsg("Denied. Bader will see this under Lead denied until the end of the day.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally {
      setBusy(false);
    }
  }

  async function sendRecommendations() {
    if (!nl) return;
    const comments = nl.sections
      .map((section) => ({
        section_id: section.id,
        body: (notes[section.id] || "").trim(),
      }))
      .filter((item) => item.body);
    if (!comments.length) {
      setError("Add a change comment on at least one section, or approve the newsletter.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const updated = await api.publicRecommendations(token, comments);
      setNl(updated);
      setDone("changes");
      setMsg("Recommendations sent to Bader.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally {
      setBusy(false);
    }
  }

  if (!nl && !error) return <p className="muted">Loading newsletter…</p>;
  if (!nl) return <p className="error">{error}</p>;

  return (
    <div className="stack">
      <div className="hero">
        <h1>{nl.headline || nl.title}</h1>
        <p className="lede">
          Review every section. Approve the newsletter, or write the specific
          change you want on any section and send it back to Bader.
        </p>
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
        {nl.sections.map((section, index) => (
          <div key={section.id} className="preview-section stack">
            <h3 style={{ marginTop: 0 }}>
              {index + 1}. {section.title || SECTION_LABELS[section.section_type]}
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
            {!done && section.lead_decision !== "approved" && section.lead_decision !== "queued" && (
              <div className="stack">
                <label>
                  Changes required for this section
                  <VoiceControl
                    value={notes[section.id] || ""}
                    onChange={(next) =>
                      setNotes((current) => ({ ...current, [section.id]: next }))
                    }
                  >
                    <textarea
                      value={notes[section.id] || ""}
                      placeholder="Leave blank if this section is fine. Otherwise describe the specific change."
                      onChange={(e) =>
                        setNotes((current) => ({ ...current, [section.id]: e.target.value }))
                      }
                    />
                  </VoiceControl>
                </label>
                <button
                  type="button"
                  className="secondary"
                  disabled={busy}
                  onClick={() => approveSection(section.id)}
                >
                  Approve this section
                </button>
              </div>
            )}
            {(section.lead_decision === "approved" || section.lead_decision === "queued") && (
              <p className="muted">This section is already approved.</p>
            )}
          </div>
        ))}
      </div>

      {!done && (
        <div className="row">
          <button className="primary" type="button" disabled={busy} onClick={approve}>
            Approve
          </button>
          <button className="secondary" type="button" disabled={busy} onClick={deny}>
            Deny
          </button>
          <button
            className="secondary"
            type="button"
            disabled={busy}
            onClick={sendRecommendations}
          >
            Send recommendations to Bader
          </button>
        </div>
      )}

      {msg && <p className="success">{msg}</p>}
      {error && <p className="error">{error}</p>}
    </div>
  );
}
