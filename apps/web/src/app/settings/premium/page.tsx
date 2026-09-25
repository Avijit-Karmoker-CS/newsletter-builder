"use client";

import { useEffect, useState } from "react";
import { api, type Workspace } from "@/lib/api";
import { VoiceControl } from "@/components/VoiceControl";

export default function PremiumSettingsPage() {
  const [ws, setWs] = useState<Workspace | null>(null);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.workspace().then(setWs).catch((e) => setError(e.message));
  }, []);

  async function save(partial: Partial<Workspace>) {
    if (!ws) return;
    setBusy(true);
    setError("");
    try {
      const updated = await api.updateWorkspace(partial);
      setWs(updated);
      setMsg("Saved.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  if (!ws && !error) return <p className="muted">Loading…</p>;
  if (!ws) return <p className="error">{error}</p>;

  const premium = ws.plan === "premium";

  return (
    <div className="stack">
      <div className="hero">
        <h1>Premium settings</h1>
        <p className="lede">
          AI tool picking and app customization are premium features. Free plans
          can still build and review manually.
        </p>
      </div>

      <section className="panel stack">
        <h2>Plan</h2>
        <p>
          Current plan: <strong>{ws.plan}</strong>
        </p>
        <div className="row">
          <button
            type="button"
            className={ws.plan === "premium" ? "primary" : "secondary"}
            disabled={busy}
            onClick={() => save({ plan: "premium" })}
          >
            Use premium
          </button>
          <button
            type="button"
            className={ws.plan === "free" ? "primary" : "secondary"}
            disabled={busy}
            onClick={() => save({ plan: "free" })}
          >
            Use free
          </button>
        </div>
      </section>

      <section className="panel stack">
        <h2>AI options {premium ? "" : "(locked)"}</h2>
        <label>
          Provider
          <select
            disabled={!premium || busy}
            value={ws.ai_provider === "cursor" ? "cursor" : "claude"}
            onChange={(e) => setWs({ ...ws, ai_provider: e.target.value })}
          >
            <option value="claude">Claude</option>
            <option value="cursor">Cursor</option>
          </select>
        </label>
        <button
          type="button"
          className="primary"
          disabled={!premium || busy}
          onClick={async () => {
            const tool = ws.ai_provider === "cursor" ? "cursor" : "claude";
            setBusy(true);
            setError("");
            try {
              const user = await api.me();
              if (user.mailchimp_email && user.slack_email) {
                await api.updateProfile({
                  mailchimp_email: user.mailchimp_email,
                  slack_email: user.slack_email,
                  ai_tool: tool,
                });
              }
              const updated = await api.updateWorkspace({
                ai_provider: tool,
                ai_model: tool,
              });
              setWs(updated);
              setMsg("Saved.");
            } catch (e) {
              setError(e instanceof Error ? e.message : "Save failed");
            } finally {
              setBusy(false);
            }
          }}
        >
          Save AI settings
        </button>
      </section>

      <section className="panel stack">
        <h2>App customization {premium ? "" : "(locked)"}</h2>
        <label>
          Brand color
          <input
            type="color"
            disabled={!premium || busy}
            value={ws.brand_color || "#0f766e"}
            onChange={(e) => setWs({ ...ws, brand_color: e.target.value })}
          />
        </label>
        <label>
          Headline style
          <select
            disabled={!premium || busy}
            value={ws.headline_style || "classic"}
            onChange={(e) => setWs({ ...ws, headline_style: e.target.value })}
          >
            <option value="classic">Classic</option>
            <option value="bold">Bold</option>
            <option value="minimal">Minimal</option>
          </select>
        </label>
        <label>
          Default background URL
          <VoiceControl
            value={ws.default_background_url || ""}
            onChange={(next) => setWs({ ...ws, default_background_url: next })}
          >
            <input
              disabled={!premium || busy}
              value={ws.default_background_url || ""}
              onChange={(e) =>
                setWs({ ...ws, default_background_url: e.target.value })
              }
              placeholder="https://…"
            />
          </VoiceControl>
        </label>
        <button
          type="button"
          className="primary"
          disabled={!premium || busy}
          onClick={() =>
            save({
              brand_color: ws.brand_color,
              headline_style: ws.headline_style,
              default_background_url: ws.default_background_url,
            })
          }
        >
          Save customization
        </button>
      </section>

      {msg && <p className="success">{msg}</p>}
      {error && <p className="error">{error}</p>}
    </div>
  );
}
