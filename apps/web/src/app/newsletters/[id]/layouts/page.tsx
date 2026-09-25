"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { LAYOUTS, SECTION_LABELS, api, type Newsletter } from "@/lib/api";
import { WizardNav, useLeaveFinishedWizard } from "@/components/Shell";

export default function LayoutsPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [nl, setNl] = useState<Newsletter | null>(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.getNewsletter(id).then(setNl).catch((e) => setError(e.message));
  }, [id]);

  async function pickLayout(sectionId: string, layout_key: string) {
    if (!nl) return;
    setSaving(true);
    try {
      const section = await api.updateSection(nl.id, sectionId, { layout_key });
      setNl({
        ...nl,
        sections: nl.sections.map((s) => (s.id === section.id ? { ...s, ...section } : s)),
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function next() {
    if (!nl) return;
    const missing = nl.sections.filter((s) => !s.layout_key);
    if (missing.length) {
      setError("Pick a layout for every section.");
      return;
    }
    router.push(`/newsletters/${nl.id}/content`);
  }

  useLeaveFinishedWizard(nl?.status);

  if (!nl && !error) return <p className="muted">Loading…</p>;
  if (!nl) return <p className="error">{error}</p>;
  if (nl.status === "sent") {
    return <p className="muted">This issue is sent. Opening the dashboard…</p>;
  }

  return (
    <div className="stack">
      <WizardNav id={nl.id} step="layouts" />
      <div className="hero">
        <h1>Choose layouts</h1>
        <p className="lede">
          Each layout maps to a Mailchimp template block later. Selections autosave.
        </p>
      </div>

      {nl.sections.map((section) => (
        <section key={section.id} className="panel stack">
          <h2>
            {SECTION_LABELS[section.section_type]}{" "}
            <span className="muted">· section {section.sort_order + 1}</span>
          </h2>
          <div className="grid grid-3">
            {LAYOUTS.map((layout) => (
              <button
                key={layout.key}
                type="button"
                className={`layout-card ${section.layout_key === layout.key ? "selected" : ""}`}
                onClick={() => pickLayout(section.id, layout.key)}
              >
                <strong>{layout.label}</strong>
                <div className="muted">{layout.desc}</div>
              </button>
            ))}
          </div>
        </section>
      ))}

      {error && <p className="error">{error}</p>}
      <div className="row">
        <button className="primary" type="button" onClick={next} disabled={saving}>
          Next: section content
        </button>
      </div>
    </div>
  );
}
