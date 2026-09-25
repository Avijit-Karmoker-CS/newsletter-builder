"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

function profileComplete(user: { mailchimp_email?: string | null; slack_email?: string | null; ai_tool?: string | null }) {
  return Boolean(
    user.mailchimp_email &&
      user.slack_email &&
      (user.ai_tool === "claude" || user.ai_tool === "cursor")
  );
}

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const leadReview = pathname.startsWith("/r/");
  const [gate, setGate] = useState<"loading" | "ok" | "signup" | "login">("loading");
  const [accountEmail, setAccountEmail] = useState("");

  useEffect(() => {
    if (leadReview) {
      setGate("ok");
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const status = await api.authStatus();
        if (cancelled) return;
        if (!status.password_set) {
          if (pathname !== "/signup") {
            setGate("signup");
            router.replace("/signup");
            return;
          }
          setGate("ok");
          return;
        }
        try {
          const user = await api.me();
          if (cancelled) return;
          setAccountEmail(user.email);
          if (!profileComplete(user) && pathname !== "/signup") {
            setGate("signup");
            router.replace("/signup");
            return;
          }
          setGate("ok");
        } catch {
          if (cancelled) return;
          if (pathname !== "/login" && pathname !== "/signup") {
            setGate("login");
            router.replace("/login");
            return;
          }
          setGate("ok");
        }
      } catch {
        if (!cancelled) setGate("ok");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [leadReview, pathname, router]);

  async function logout() {
    await api.logout().catch(() => {});
    setAccountEmail("");
    router.replace("/login");
  }

  if (leadReview) {
    return (
      <div className="shell">
        <header className="topbar">
          <span className="brand">Newsletter review</span>
        </header>
        <main className="main">{children}</main>
      </div>
    );
  }

  if (gate !== "ok") {
    return (
      <div className="shell">
        <main className="main">
          <p className="muted">Loading…</p>
        </main>
      </div>
    );
  }

  return (
    <div className="shell">
      <header className="topbar">
        <Link href="/" className="brand">
          Newsletter Builder
        </Link>
        <nav className="nav">
          <Link href="/">Dashboard</Link>
          <Link href="/newsletters/new">New issue</Link>
          <Link href="/archive">Archive</Link>
          <Link href="/settings/premium">Premium</Link>
        </nav>
        <div className="role-switch">
          <span>{accountEmail || "Bader"}</span>
          {accountEmail && (
            <button type="button" onClick={logout}>
              Log out
            </button>
          )}
        </div>
      </header>
      <main className="main">{children}</main>
    </div>
  );
}

export function useLeaveFinishedWizard(status: string | undefined) {
  const router = useRouter();
  useEffect(() => {
    if (status !== "sent") return;
    router.replace("/");
  }, [status, router]);
}

export function WizardNav({
  id,
  step,
}: {
  id: string;
  step: "layouts" | "content" | "chrome" | "preview" | "review" | "send";
}) {
  useEffect(() => {
    api.updateNewsletter(id, { last_step: step }).catch(() => {});
  }, [id, step]);

  const steps = [
    { key: "layouts", href: `/newsletters/${id}/layouts`, label: "Layouts" },
    { key: "content", href: `/newsletters/${id}/content`, label: "Content" },
    { key: "chrome", href: `/newsletters/${id}/chrome`, label: "Chrome" },
    { key: "preview", href: `/newsletters/${id}/preview`, label: "Preview" },
    { key: "review", href: `/newsletters/${id}/review`, label: "Review" },
    { key: "send", href: `/newsletters/${id}/send`, label: "Send" },
  ] as const;

  return (
    <ol className="wizard-nav">
      {steps.map((s) => (
        <li key={s.key} className={s.key === step ? "current" : ""}>
          <Link href={s.href}>{s.label}</Link>
        </li>
      ))}
    </ol>
  );
}

export function StatusPill({ status }: { status: string }) {
  return <span className={`pill status-${status}`}>{status.replace(/_/g, " ")}</span>;
}
