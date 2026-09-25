"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { SECTION_LABELS, api, type SectionType } from "@/lib/api";
import { VoiceControl } from "@/components/VoiceControl";

const TYPES = Object.keys(SECTION_LABELS) as SectionType[];

export default function NewNewsletterPage() {
  const router = useRouter();
  const [title, setTitle] = useState("Monthly community letter");
  const [count, setCount] = useState(3);
  const [types, setTypes] = useState<SectionType[]>(["news", "featured_story", "cta"]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function syncCount(next: number) {
    const n = Math.max(1, Math.min(8, next));
    setCount(n);
    setTypes((prev) => {
      const copy = [...prev];
      while (copy.length < n) copy.push("news");
      return copy.slice(0, n);
    });
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const nl = await api.createNewsletter(
        title,
        types.map((section_type) => ({ section_type }))
      );
      router.push(`/newsletters/${nl.id}/layouts`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create");
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      <div className="hero">
        <h1>New newsletter</h1>
        <p className="lede">
          Tell us how many sections you want and what each one should be. Your
          answers are saved as soon as you continue.
        </p>
      </div>

      <form className="panel stack" onSubmit={onSubmit}>
        <label>
          Working title
          <VoiceControl value={title} onChange={setTitle}>
            <input value={title} onChange={(e) => setTitle(e.target.value)} required />
          </VoiceControl>
        </label>

        <label>
          How many sections?
          <input
            type="number"
            min={1}
            max={8}
            value={count}
            onChange={(e) => syncCount(Number(e.target.value))}
          />
        </label>

        <div className="stack">
          <strong>Section types</strong>
          {types.map((t, i) => (
            <label key={i}>
              Section {i + 1}
              <select
                value={t}
                onChange={(e) => {
                  const next = [...types];
                  next[i] = e.target.value as SectionType;
                  setTypes(next);
                }}
              >
                {TYPES.map((opt) => (
                  <option key={opt} value={opt}>
                    {SECTION_LABELS[opt]}
                  </option>
                ))}
              </select>
            </label>
          ))}
        </div>

        {error && <p className="error">{error}</p>}

        <div className="row">
          <button className="primary" type="submit" disabled={busy}>
            {busy ? "Saving…" : "Next: pick layouts"}
          </button>
        </div>
      </form>
    </div>
  );
}
