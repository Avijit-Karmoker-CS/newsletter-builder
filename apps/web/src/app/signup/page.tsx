"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { VoiceControl } from "@/components/VoiceControl";

export default function SignupPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [mailchimpEmail, setMailchimpEmail] = useState("");
  const [slackEmail, setSlackEmail] = useState("");
  const [aiTool, setAiTool] = useState<"claude" | "cursor">("claude");
  const [needsPassword, setNeedsPassword] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const user = await api.me();
        if (cancelled) return;
        setNeedsPassword(false);
        setEmail(user.email);
        if (user.mailchimp_email) setMailchimpEmail(user.mailchimp_email);
        if (user.slack_email) setSlackEmail(user.slack_email);
        if (user.ai_tool === "cursor" || user.ai_tool === "claude") setAiTool(user.ai_tool);
      } catch {
        if (!cancelled) setNeedsPassword(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (needsPassword && password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      if (needsPassword) {
        await api.register({
          email: email.trim(),
          password,
          mailchimp_email: mailchimpEmail.trim(),
          slack_email: slackEmail.trim(),
          ai_tool: aiTool,
        });
      } else {
        await api.updateProfile({
          mailchimp_email: mailchimpEmail.trim(),
          slack_email: slackEmail.trim(),
          ai_tool: aiTool,
        });
      }
      router.replace("/");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save your account");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      <div className="hero">
        <h1>{needsPassword ? "Create your account" : "Set up Bader"}</h1>
        <p className="lede">
          {needsPassword
            ? "Open this site on any computer, create an account, and start a newsletter. Add the Mailchimp email, the lead email, and Claude or Cursor."
            : "Update the Mailchimp email, the lead email, and Claude or Cursor."}
        </p>
      </div>

      <form className="panel stack" onSubmit={submit}>
        <label>
          Sign-in email
          <VoiceControl value={email} onChange={setEmail}>
            <input
              type="email"
              required
              autoComplete="username"
              value={email}
              disabled={!needsPassword}
              placeholder="bader@your-domain.com"
              onChange={(e) => setEmail(e.target.value)}
            />
          </VoiceControl>
        </label>
        {needsPassword && (
          <>
            <label>
              Password
              <input
                type="password"
                required
                minLength={8}
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
            <label>
              Confirm password
              <input
                type="password"
                required
                minLength={8}
                autoComplete="new-password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
              />
            </label>
          </>
        )}
        <label>
          Mailchimp email
          <VoiceControl value={mailchimpEmail} onChange={setMailchimpEmail}>
            <input
              type="email"
              required
              value={mailchimpEmail}
              placeholder="bader@your-mailchimp-account.com"
              onChange={(e) => setMailchimpEmail(e.target.value)}
            />
          </VoiceControl>
        </label>
        <label>
          Slack email
          <VoiceControl value={slackEmail} onChange={setSlackEmail}>
            <input
              type="email"
              required
              value={slackEmail}
              placeholder="lead@example.com"
              onChange={(e) => setSlackEmail(e.target.value)}
            />
          </VoiceControl>
        </label>
        <fieldset className="stack" style={{ border: 0, padding: 0, margin: 0 }}>
          <legend>AI tool</legend>
          <label style={{ flexDirection: "row", alignItems: "center", gap: "0.5rem" }}>
            <input
              type="radio"
              name="ai-tool"
              checked={aiTool === "claude"}
              onChange={() => setAiTool("claude")}
            />
            Claude
          </label>
          <label style={{ flexDirection: "row", alignItems: "center", gap: "0.5rem" }}>
            <input
              type="radio"
              name="ai-tool"
              checked={aiTool === "cursor"}
              onChange={() => setAiTool("cursor")}
            />
            Cursor
          </label>
        </fieldset>
        <button className="primary" type="submit" disabled={busy}>
          {busy ? "Saving…" : needsPassword ? "Create secure account" : "Save"}
        </button>
        {error && <p className="error">{error}</p>}
        {needsPassword && (
          <p className="muted">
            Already set a password? <Link href="/login">Sign in</Link>
          </p>
        )}
      </form>
    </div>
  );
}
