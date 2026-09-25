"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, assetUrl, type Newsletter } from "@/lib/api";
import { WizardNav } from "@/components/Shell";

export default function ChromePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [nl, setNl] = useState<Newsletter | null>(null);
  const [headline, setHeadline] = useState("");
  const [issueDate, setIssueDate] = useState("");
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");

  useEffect(() => {
    api
      .getNewsletter(id)
      .then((n) => {
        setNl(n);
        setHeadline(n.headline || n.title);
        setIssueDate(n.issue_date || new Date().toISOString().slice(0, 10));
      })
      .catch((e) => setError(e.message));
  }, [id]);

  async function saveMeta() {
    if (!nl) return;
    try {
      const updated = await api.updateNewsletter(nl.id, {
        headline,
        issue_date: issueDate,
      });
      setNl(updated);
      setMsg("Headline and date saved.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    }
  }

  async function onBackground(file: File) {
    if (!nl) return;
    try {
      const result = await api.uploadBackground(nl.id, file);
      setNl({
        ...nl,
        background_url: result.background_url,
        headline: result.headline || headline,
        issue_date: result.issue_date || issueDate,
      });
      setHeadline(result.headline || headline);
      setIssueDate(result.issue_date || issueDate);
      setMsg("Background uploaded — headline and date placed automatically.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    }
  }

  if (!nl && !error) return <p className="muted">Loading…</p>;
  if (!nl) return <p className="error">{error}</p>;

  return (
    <div className="stack">
      <WizardNav id={nl.id} step="chrome" />
      <div className="hero">
        <h1>Background & chrome</h1>
        <p className="lede">
          Upload a background. Headline and issue date appear where they belong
          on the hero.
        </p>
      </div>

      <section className="panel stack">
        <label>
          Headline
          <input value={headline} onChange={(e) => setHeadline(e.target.value)} />
        </label>
        <label>
          Issue date
          <input
            type="date"
            value={issueDate}
            onChange={(e) => setIssueDate(e.target.value)}
          />
        </label>
        <label>
          Background image
          <input
            type="file"
            accept="image/*"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) onBackground(file);
            }}
          />
        </label>
        <div className="row">
          <button type="button" className="secondary" onClick={saveMeta}>
            Save headline & date
          </button>
        </div>
      </section>

      <div
        className="preview-shell"
        style={{
          backgroundImage: nl.background_url
            ? `linear-gradient(rgba(15,30,28,0.45), rgba(15,30,28,0.55)), url(${assetUrl(nl.background_url)})`
            : undefined,
        }}
      >
        <div className="preview-hero">
          <h2 style={{ margin: 0 }}>{headline}</h2>
          <p style={{ marginTop: "0.5rem", opacity: 0.9 }}>{issueDate}</p>
        </div>
      </div>

      {msg && <p className="success">{msg}</p>}
      {error && <p className="error">{error}</p>}

      <div className="row">
        <button
          className="primary"
          type="button"
          onClick={async () => {
            await saveMeta();
            router.push(`/newsletters/${nl.id}/preview`);
          }}
        >
          Next: preview
        </button>
      </div>
    </div>
  );
}
