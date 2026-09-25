"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  SECTION_LABELS,
  api,
  assetUrl,
  type Newsletter,
  type Workspace,
} from "@/lib/api";
import { WizardNav } from "@/components/Shell";

export default function ContentPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [nl, setNl] = useState<Newsletter | null>(null);
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [newsletter, ws] = await Promise.all([
          api.getNewsletter(id),
          api.workspace(),
        ]);
        if (!cancelled) {
          setNl(newsletter);
          setWorkspace(ws);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  async function reload() {
    const [newsletter, ws] = await Promise.all([
      api.getNewsletter(id),
      api.workspace(),
    ]);
    setNl(newsletter);
    setWorkspace(ws);
  }

  async function saveSection(sectionId: string, title: string, body: string) {
    if (!nl) return;
    setBusyId(sectionId);
    setError("");
    try {
      const section = await api.updateSection(nl.id, sectionId, {
        title,
        body,
        saved: true,
      });
      setNl({
        ...nl,
        sections: nl.sections.map((s) =>
          s.id === section.id ? { ...s, ...section, comments: s.comments } : s
        ),
      });
      setMsg("Section saved.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusyId(null);
    }
  }

  async function generate(sectionId: string, topic: string) {
    if (!nl) return;
    setBusyId(sectionId);
    setError("");
    try {
      const { body } = await api.generateSection(nl.id, sectionId, topic);
      setNl({
        ...nl,
        sections: nl.sections.map((s) =>
          s.id === sectionId ? { ...s, body } : s
        ),
      });
      setMsg("AI draft inserted — review and save.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "AI failed");
    } finally {
      setBusyId(null);
    }
  }

  async function upload(sectionId: string, file: File) {
    if (!nl) return;
    setBusyId(sectionId);
    try {
      const result = await api.uploadSectionImage(nl.id, sectionId, file);
      setNl({
        ...nl,
        sections: nl.sections.map((s) =>
          s.id === sectionId ? { ...s, image_urls: result.image_urls } : s
        ),
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setBusyId(null);
    }
  }

  async function resolve(commentId: string) {
    if (!nl) return;
    await api.resolveComment(nl.id, commentId);
    await reload();
  }

  if (!nl && !error) return <p className="muted">Loading…</p>;
  if (!nl) return <p className="error">{error}</p>;

  const premium = workspace?.plan === "premium";

  return (
    <div className="stack">
      <WizardNav id={nl.id} step="content" />
      <div className="hero">
        <h1>Section content</h1>
        <p className="lede">
          Write or generate copy, upload images, and save each section. Lead
          comments appear under any section that needs changes.
        </p>
      </div>

      {nl.sections.map((section) => (
        <SectionEditor
          key={section.id}
          section={section}
          premium={premium}
          busy={busyId === section.id}
          onSave={(title, body) => saveSection(section.id, title, body)}
          onGenerate={(topic) => generate(section.id, topic)}
          onUpload={(file) => upload(section.id, file)}
          onResolve={resolve}
        />
      ))}

      {msg && <p className="success">{msg}</p>}
      {error && <p className="error">{error}</p>}

      <div className="row">
        <button
          className="primary"
          type="button"
          onClick={() => {
            const unsaved = nl.sections.filter((s) => !s.saved);
            if (unsaved.length) {
              setError(`Save all sections first (${unsaved.length} remaining).`);
              return;
            }
            router.push(`/newsletters/${nl.id}/chrome`);
          }}
        >
          Next: background & headline
        </button>
      </div>
    </div>
  );
}

function SectionEditor({
  section,
  premium,
  busy,
  onSave,
  onGenerate,
  onUpload,
  onResolve,
}: {
  section: Newsletter["sections"][number];
  premium: boolean;
  busy: boolean;
  onSave: (title: string, body: string) => void;
  onGenerate: (topic: string) => void;
  onUpload: (file: File) => void;
  onResolve: (id: string) => void;
}) {
  const [title, setTitle] = useState(section.title || "");
  const [body, setBody] = useState(section.body || "");

  useEffect(() => {
    setTitle(section.title || "");
    setBody(section.body || "");
  }, [section.title, section.body]);

  return (
    <section className="panel stack">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h2>
          {SECTION_LABELS[section.section_type]}{" "}
          <span className="muted">· {section.layout_key || "no layout"}</span>
        </h2>
        {section.saved ? <span className="pill">Saved</span> : <span className="muted">Unsaved</span>}
      </div>

      {(section.comments || [])
        .filter((c) => !c.resolved)
        .map((c) => (
          <div key={c.id} className="comment">
            <strong>Lead comment</strong>
            <p style={{ margin: "0.35rem 0" }}>{c.body}</p>
            <button type="button" className="secondary" onClick={() => onResolve(c.id)}>
              Mark resolved
            </button>
          </div>
        ))}

      <label>
        Section title
        <input value={title} onChange={(e) => setTitle(e.target.value)} />
      </label>
      <label>
        Body
        <textarea value={body} onChange={(e) => setBody(e.target.value)} />
      </label>

      <div className="row">
        <button
          type="button"
          className="primary"
          disabled={busy}
          onClick={() => onSave(title, body)}
        >
          Save section
        </button>
        <button
          type="button"
          className="secondary"
          disabled={busy || !premium}
          title={premium ? "Generate with AI" : "Premium required"}
          onClick={() => onGenerate(title || SECTION_LABELS[section.section_type])}
        >
          {premium ? "Generate with AI" : "AI (premium)"}
        </button>
        <label style={{ flexDirection: "row", alignItems: "center", gap: "0.5rem" }}>
          <span>Upload image</span>
          <input
            type="file"
            accept="image/*"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) onUpload(file);
            }}
          />
        </label>
      </div>

      {section.image_urls?.length > 0 && (
        <div className="row">
          {section.image_urls.map((url) => (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              key={url}
              src={assetUrl(url)}
              alt=""
              style={{ width: 96, height: 72, objectFit: "cover", borderRadius: 8 }}
            />
          ))}
        </div>
      )}
    </section>
  );
}
