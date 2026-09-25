"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import {
  SECTION_LABELS,
  api,
  assetUrl,
  type Newsletter,
  type SourceClip,
} from "@/lib/api";
import { WizardNav, useLeaveFinishedWizard } from "@/components/Shell";
import { VoiceControl } from "@/components/VoiceControl";

export default function ContentPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const focusSection = useSearchParams().get("section");
  const [nl, setNl] = useState<Newsletter | null>(null);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const newsletter = await api.getNewsletter(id);
        if (!cancelled) setNl(newsletter);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  useEffect(() => {
    if (!nl || !focusSection) return;
    document.getElementById(`section-${focusSection}`)?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }, [nl, focusSection]);

  async function reload() {
    setNl(await api.getNewsletter(id));
  }

  async function autosaveSection(
    sectionId: string,
    title: string,
    body: string,
    topic: string,
    instructions: string
  ) {
    if (!nl) return;
    try {
      await api.updateSection(nl.id, sectionId, {
        title,
        body,
        ai_topic: topic,
        ai_instructions: instructions,
        saved: true,
      });
    } catch {
      /* keep typing; the next autosave retries */
    }
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

  async function generate(sectionId: string, topic: string, instructions: string) {
    if (!nl) return;
    const prompt = instructions.trim() || `A short factual note about ${topic}.`;
    setBusyId(sectionId);
    setError("");
    try {
      const { body } = await api.generateSection(nl.id, sectionId, topic, prompt);
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

  useLeaveFinishedWizard(nl?.status);

  if (!nl && !error) return <p className="muted">Loading…</p>;
  if (!nl) return <p className="error">{error}</p>;
  if (nl.status === "sent") {
    return <p className="muted">This issue is sent. Opening the dashboard…</p>;
  }

  return (
    <div className="stack">
      <WizardNav id={nl.id} step="content" />
      <div className="hero">
        <h1>Section content</h1>
        <p className="lede">
          Search verified sources, choose the clips and links you want, then save
          the section. Lead comments appear under any section that needs changes.
        </p>
        {nl.sections.some((s) => s.comments?.some((c) => !c.resolved)) && (
          <div className="row">
            <Link href={`/newsletters/${nl.id}/review`}>Back to pending review log</Link>
            <button
              className="primary"
              type="button"
              disabled={busyId === "resubmit"}
              onClick={async () => {
                setBusyId("resubmit");
                setError("");
                try {
                  const updated = await api.resubmitReview(nl.id);
                  setMsg(
                    `Updated newsletter sent to ${updated.lead_slack_email} for approval.`
                  );
                  router.push(`/newsletters/${nl.id}/review`);
                } catch (e) {
                  setError(e instanceof Error ? e.message : "Could not send the newsletter back");
                  setBusyId(null);
                }
              }}
            >
              Send to lead for approval
            </button>
          </div>
        )}
      </div>

      {groupedSections(nl).map((group) => (
        <div key={group.title} className="stack">
          {group.title && <h2>{group.title}</h2>}
          {group.sections.map((section) => (
            <SectionEditor
              key={section.id}
              focused={focusSection === section.id}
              section={section}
              busy={busyId === section.id}
              onSave={(title, body) => saveSection(section.id, title, body)}
              onAutosave={(title, body, topic, instructions) =>
                autosaveSection(section.id, title, body, topic, instructions)
              }
              onGenerate={(topic, instructions) => generate(section.id, topic, instructions)}
              onSearch={(query) => api.searchSources(nl.id, section.id, query)}
              onUpload={(file) => upload(section.id, file)}
              onResolve={resolve}
            />
          ))}
        </div>
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

function groupedSections(nl: Newsletter) {
  if (nl.status !== "changes_requested") {
    return [{ title: "", sections: nl.sections }];
  }
  const approved = nl.sections.filter((section) => section.lead_decision === "approved");
  const changes = nl.sections.filter((section) => section.lead_decision !== "approved");
  return [
    { title: "Lead approved these sections", sections: approved },
    { title: "Lead asked for changes in these sections", sections: changes },
  ].filter((group) => group.sections.length > 0);
}

function SectionEditor({
  section,
  busy,
  focused,
  onSave,
  onAutosave,
  onGenerate,
  onSearch,
  onUpload,
  onResolve,
}: {
  section: Newsletter["sections"][number];
  busy: boolean;
  focused?: boolean;
  onSave: (title: string, body: string) => void;
  onAutosave: (title: string, body: string, topic: string, instructions: string) => void;
  onGenerate: (topic: string, instructions: string) => void;
  onSearch: (query: string) => Promise<{ results: SourceClip[] }>;
  onUpload: (file: File) => void;
  onResolve: (id: string) => void;
}) {
  const [title, setTitle] = useState(section.title || "");
  const [body, setBody] = useState(section.body || "");
  const [topic, setTopic] = useState(section.ai_topic || section.title || "");
  const [instructions, setInstructions] = useState(section.ai_instructions || "");
  const [searchQuery, setSearchQuery] = useState(section.ai_topic || section.title || "");
  const [clips, setClips] = useState<SourceClip[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchNote, setSearchNote] = useState("");
  const clipsRef = useRef<SourceClip[]>([]);
  clipsRef.current = clips;
  const ready = useRef(false);
  const saveRef = useRef(onAutosave);
  saveRef.current = onAutosave;

  useEffect(() => {
    ready.current = false;
    setTitle(section.title || "");
    setBody(section.body || "");
    setTopic(section.ai_topic || section.title || "");
    setInstructions(section.ai_instructions || "");
    const arm = window.setTimeout(() => {
      ready.current = true;
    }, 0);
    return () => window.clearTimeout(arm);
  }, [section.id, section.title, section.body, section.ai_topic, section.ai_instructions]);

  useEffect(() => {
    if (!ready.current) return;
    const handle = window.setTimeout(() => {
      saveRef.current(title, body, topic, instructions);
    }, 700);
    return () => window.clearTimeout(handle);
  }, [title, body, topic, instructions]);

  return (
    <section
      id={`section-${section.id}`}
      className={`panel stack${focused ? " section-focus" : ""}`}
    >
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
        <VoiceControl value={title} onChange={setTitle}>
          <input value={title} onChange={(e) => setTitle(e.target.value)} />
        </VoiceControl>
      </label>
      <label>
        Body
        <VoiceControl value={body} onChange={setBody}>
          <textarea value={body} onChange={(e) => setBody(e.target.value)} />
        </VoiceControl>
      </label>
      <div className="stack">
        <label>
          Search verified sources
          <VoiceControl value={searchQuery} onChange={setSearchQuery}>
            <input
              value={searchQuery}
              placeholder="Search Wikipedia before you save"
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </VoiceControl>
        </label>
        <div className="row">
          <button
            type="button"
            className="secondary"
            disabled={searching}
            onClick={async () => {
              const query = searchQuery.trim() || topic.trim() || title.trim();
              if (!query) {
                setSearchNote("Enter a search first.");
                return;
              }
              setSearching(true);
              setSearchNote("");
              try {
                const found = await onSearch(query);
                clipsRef.current = found.results;
                setClips(found.results);
                setSearchNote(
                  found.results.length
                    ? "Choose a result. It goes into the body and this list clears."
                    : "No verified pages matched that search."
                );
              } catch (e) {
                setSearchNote(e instanceof Error ? e.message : "Search failed");
              } finally {
                setSearching(false);
              }
            }}
          >
            {searching ? "Searching…" : "Search"}
          </button>
        </div>
        {searchNote && <p className="muted">{searchNote}</p>}
        {clips.length > 0 && (
          <div className="source-clips">
            {clips.map((clip) => (
              <div key={clip.url} className="source-clip">
                <button
                  type="button"
                  className="secondary"
                  onClick={() => {
                    if (!clipsRef.current.length) return;
                    clipsRef.current = [];
                    const block = `${clip.excerpt}\n${clip.source}: ${clip.title}\n${clip.url}`;
                    setBody((current) =>
                      current.includes(clip.url)
                        ? current
                        : current.trim()
                          ? `${current.trim()}\n\n${block}`
                          : block
                    );
                    setClips([]);
                    setSearchQuery("");
                    setSearchNote("Selected text is in the body. Search again with different keywords if you want other clips.");
                  }}
                >
                  Use this text
                </button>
                <span>
                  <strong>{clip.title}</strong>
                  <span className="muted"> · {clip.source}</span>
                  <p>{clip.excerpt}</p>
                  <a href={clip.url} target="_blank" rel="noreferrer">
                    {clip.url}
                  </a>
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
      <label>
        Topic
        <VoiceControl value={topic} onChange={setTopic}>
          <input
            value={topic}
            placeholder="What is this section about?"
            onChange={(e) => setTopic(e.target.value)}
          />
        </VoiceControl>
      </label>
      <label>
        What kind of text do you want?
        <VoiceControl value={instructions} onChange={setInstructions}>
          <textarea
            value={instructions}
            placeholder="Example: a warm 80-word note for neighbors, with one practical tip and no jargon."
            onChange={(e) => setInstructions(e.target.value)}
          />
        </VoiceControl>
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
          disabled={busy}
          title="Generate from your topic and prompt"
          onClick={() =>
            onGenerate(topic || title || SECTION_LABELS[section.section_type], instructions)
          }
        >
          Generate with AI
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
