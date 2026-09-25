"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getRole, setRole, type Role } from "@/lib/api";

export function Shell({ children }: { children: React.ReactNode }) {
  const [role, setRoleState] = useState<Role>("bader");

  useEffect(() => {
    setRoleState(getRole());
  }, []);

  function switchRole(next: Role) {
    setRole(next);
    setRoleState(next);
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
          <span>Acting as</span>
          <button
            type="button"
            className={role === "bader" ? "active" : ""}
            onClick={() => switchRole("bader")}
          >
            Bader
          </button>
          <button
            type="button"
            className={role === "lead" ? "active" : ""}
            onClick={() => switchRole("lead")}
          >
            Lead
          </button>
        </div>
      </header>
      <main className="main">{children}</main>
    </div>
  );
}

export function WizardNav({
  id,
  step,
}: {
  id: string;
  step: "layouts" | "content" | "chrome" | "preview" | "review" | "send";
}) {
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
