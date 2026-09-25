export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type Role = "bader" | "lead";

export const TOKENS: Record<Role, string> = {
  bader: "bader-demo-token",
  lead: "lead-demo-token",
};

export type SectionType =
  | "news"
  | "featured_story"
  | "tips"
  | "events"
  | "cta";

export type NewsletterStatus =
  | "drafting"
  | "in_review"
  | "changes_requested"
  | "review_complete"
  | "ready_to_send"
  | "sent";

export type Comment = {
  id: string;
  section_id: string;
  body: string;
  resolved: boolean;
  created_at: string;
};

export type Section = {
  id: string;
  section_type: SectionType;
  layout_key: string | null;
  sort_order: number;
  title: string | null;
  body: string | null;
  image_urls: string[];
  saved: boolean;
  saved_at: string | null;
  comments: Comment[];
};

export type ReviewEvent = {
  id: string;
  event_type: string;
  message: string;
  meta?: Record<string, unknown> | null;
  created_at: string;
};

export type Newsletter = {
  id: string;
  title: string;
  headline: string | null;
  issue_date: string | null;
  background_url: string | null;
  status: NewsletterStatus;
  section_count: number;
  mailchimp_campaign_id: string | null;
  mailchimp_editor_url: string | null;
  created_at: string;
  updated_at: string;
  sent_at: string | null;
  sections: Section[];
  review_events: ReviewEvent[];
};

export type NewsletterSummary = Omit<
  Newsletter,
  "sections" | "review_events" | "background_url"
>;

export type Workspace = {
  id: string;
  name: string;
  plan: "free" | "premium";
  brand_color: string | null;
  default_background_url: string | null;
  headline_style: string | null;
  ai_provider: string | null;
  ai_model: string | null;
};

export type User = {
  id: string;
  email: string;
  name: string;
  role: Role;
  workspace: Workspace;
};

function getToken(): string {
  if (typeof window === "undefined") return TOKENS.bader;
  const role = (localStorage.getItem("nb_role") as Role) || "bader";
  return localStorage.getItem("nb_token") || TOKENS[role];
}

export function setRole(role: Role) {
  localStorage.setItem("nb_role", role);
  localStorage.setItem("nb_token", TOKENS[role]);
}

export function getRole(): Role {
  if (typeof window === "undefined") return "bader";
  return (localStorage.getItem("nb_role") as Role) || "bader";
}

export function assetUrl(path: string | null | undefined): string {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  return `${API_URL}${path}`;
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${getToken()}`);
  }
  if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail || JSON.stringify(data);
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  me: () => request<User>("/me"),
  workspace: () => request<Workspace>("/workspace"),
  updateWorkspace: (body: Partial<Workspace>) =>
    request<Workspace>("/workspace", { method: "PATCH", body: JSON.stringify(body) }),
  listNewsletters: (status?: NewsletterStatus) =>
    request<NewsletterSummary[]>(
      status ? `/newsletters?status=${status}` : "/newsletters"
    ),
  archive: () => request<NewsletterSummary[]>("/newsletters/archive?months=12"),
  getNewsletter: (id: string) => request<Newsletter>(`/newsletters/${id}`),
  createNewsletter: (title: string, sections: { section_type: SectionType }[]) =>
    request<Newsletter>("/newsletters", {
      method: "POST",
      body: JSON.stringify({ title, sections }),
    }),
  updateNewsletter: (id: string, body: Record<string, unknown>) =>
    request<Newsletter>(`/newsletters/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  updateSection: (nlId: string, sectionId: string, body: Record<string, unknown>) =>
    request<Section>(`/newsletters/${nlId}/sections/${sectionId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  generateSection: (nlId: string, sectionId: string, topic?: string) =>
    request<{ body: string }>(`/newsletters/${nlId}/sections/${sectionId}/generate`, {
      method: "POST",
      body: JSON.stringify({ topic }),
    }),
  uploadSectionImage: async (nlId: string, sectionId: string, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<{ url: string; image_urls: string[] }>(
      `/newsletters/${nlId}/sections/${sectionId}/images`,
      { method: "POST", body: fd }
    );
  },
  uploadBackground: async (nlId: string, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<{ background_url: string; headline: string; issue_date: string }>(
      `/newsletters/${nlId}/chrome/background`,
      { method: "POST", body: fd }
    );
  },
  requestReview: (id: string) =>
    request<Newsletter>(`/newsletters/${id}/review/request`, { method: "POST" }),
  approveReview: (id: string) =>
    request<Newsletter>(`/newsletters/${id}/review/approve`, { method: "POST" }),
  demoRequestChanges: (id: string, sectionIndex: number, body: string) =>
    request<{ message: string }>(
      `/newsletters/${id}/demo/request-changes?section_index=${sectionIndex}&body=${encodeURIComponent(body)}`,
      { method: "POST" }
    ),
  addComment: (id: string, section_id: string, body: string) =>
    request<Comment>(`/newsletters/${id}/comments`, {
      method: "POST",
      body: JSON.stringify({ section_id, body }),
    }),
  resolveComment: (nlId: string, commentId: string) =>
    request<Comment>(`/newsletters/${nlId}/comments/${commentId}/resolve`, {
      method: "POST",
    }),
  syncMailchimp: (id: string) =>
    request<{ campaign_id: string; editor_url: string; demo: boolean }>(
      `/newsletters/${id}/mailchimp/sync`,
      { method: "POST" }
    ),
  confirmSent: (id: string) =>
    request<Newsletter>(`/newsletters/${id}/mailchimp/confirm-sent`, {
      method: "POST",
    }),
};

export const SECTION_LABELS: Record<SectionType, string> = {
  news: "News",
  featured_story: "Featured story",
  tips: "Tips",
  events: "Events",
  cta: "Call to action",
};

export const LAYOUTS: { key: string; label: string; desc: string }[] = [
  { key: "image_left", label: "Image left", desc: "Photo beside copy" },
  { key: "image_top", label: "Image top", desc: "Banner image above text" },
  { key: "text_only", label: "Text only", desc: "Copy-focused block" },
  { key: "split_cards", label: "Split cards", desc: "Two-column cards" },
  { key: "cta_banner", label: "CTA banner", desc: "Bold action strip" },
];

export const STATUS_LABELS: Record<NewsletterStatus, string> = {
  drafting: "Drafting",
  in_review: "In review",
  changes_requested: "Changes requested",
  review_complete: "Review complete",
  ready_to_send: "Ready to send",
  sent: "Sent",
};
