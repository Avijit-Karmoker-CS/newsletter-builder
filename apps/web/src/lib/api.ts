const DIRECT_API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

/** Browser calls go through the Next.js app so the login cookie stays on this site. */
export function apiUrl(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  if (typeof window === "undefined") return `${DIRECT_API}${normalized}`;
  return `/backend${normalized}`;
}

export const API_URL = DIRECT_API;

export type Role = "bader" | "lead";

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
  | "sent"
  | "denied";

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
  ai_topic?: string | null;
  ai_instructions?: string | null;
  image_urls: string[];
  saved: boolean;
  saved_at: string | null;
  lead_decision?: "pending" | "changes" | "approved" | "queued" | null;
  review_sent_at?: string | null;
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
  lead_slack_email?: string | null;
  review_token?: string | null;
  last_step?: string | null;
  review_requested_at?: string | null;
  denied_at?: string | null;
  created_at: string;
  updated_at: string;
  sent_at: string | null;
  slack_share_url?: string | null;
  sections: Section[];
  review_events: ReviewEvent[];
};

export type LeadNote = {
  section_id: string;
  section_title: string;
  body: string;
};

export type NewsletterSummary = Omit<
  Newsletter,
  "sections" | "review_events" | "background_url"
> & {
  lead_notes?: LeadNote[];
};

export type Workspace = {
  id: string;
  name: string;
  plan: "free" | "premium";
  brand_color: string | null;
  default_background_url: string | null;
  headline_style: string | null;
  ai_provider: string | null;
  ai_model: string | null;
  slack_connected?: boolean;
};

export type User = {
  id: string;
  email: string;
  name: string;
  role: Role;
  mailchimp_email?: string | null;
  slack_email?: string | null;
  ai_tool?: "claude" | "cursor" | string | null;
  has_password?: boolean;
  workspace: Workspace;
};

export type SourceClip = {
  title: string;
  excerpt: string;
  url: string;
  source: string;
};

export type LeadOption = {
  id: string;
  email: string;
  name: string;
};

export function getRole(): Role {
  return "bader";
}

export function assetUrl(path: string | null | undefined): string {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  return apiUrl(path);
}

async function request<T>(
  path: string,
  options: RequestInit & { auth?: boolean } = {}
): Promise<T> {
  const rest = { ...options };
  delete rest.auth;
  const headers = new Headers(rest.headers || {});
  if (rest.body && !(rest.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(apiUrl(path), {
    ...rest,
    headers,
    credentials: "include",
  });
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
  authStatus: () => request<{ password_set: boolean }>("/auth/status", { auth: false }),
  register: (body: {
    email: string;
    password: string;
    mailchimp_email: string;
    slack_email: string;
    ai_tool: "claude" | "cursor";
  }) => request<User>("/auth/register", { method: "POST", body: JSON.stringify(body), auth: false }),
  login: (email: string, password: string) =>
    request<User>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
      auth: false,
    }),
  logout: () => request<{ ok: boolean }>("/auth/logout", { method: "POST" }),
  me: () => request<User>("/me"),
  updateProfile: (body: {
    mailchimp_email: string;
    slack_email: string;
    ai_tool: "claude" | "cursor";
  }) => request<User>("/me", { method: "PATCH", body: JSON.stringify(body) }),
  listLeads: () => request<LeadOption[]>("/leads"),
  workspace: () => request<Workspace>("/workspace"),
  updateWorkspace: (body: Partial<Workspace> & { slack_bot_token?: string }) =>
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
  searchSources: (nlId: string, sectionId: string, query: string) =>
    request<{ query: string; results: SourceClip[] }>(
      `/newsletters/${nlId}/sections/${sectionId}/search`,
      { method: "POST", body: JSON.stringify({ query }) }
    ),
  generateSection: (
    nlId: string,
    sectionId: string,
    topic: string,
    instructions: string
  ) =>
    request<{ body: string }>(`/newsletters/${nlId}/sections/${sectionId}/generate`, {
      method: "POST",
      body: JSON.stringify({ topic, instructions }),
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
  requestReview: (id: string, leadEmail: string) =>
    request<Newsletter>(`/newsletters/${id}/review/request`, {
      method: "POST",
      body: JSON.stringify({ lead_email: leadEmail }),
    }),
  confirmChanges: (id: string) =>
    request<Newsletter>(`/newsletters/${id}/review/confirm-changes`, { method: "POST" }),
  resubmitReview: (id: string) =>
    request<Newsletter>(`/newsletters/${id}/review/resubmit`, { method: "POST" }),
  urgentReview: (id: string) =>
    request<Newsletter>(`/newsletters/${id}/review/urgent`, { method: "POST" }),
  releaseToCommunity: (id: string) =>
    request<Newsletter>(`/newsletters/${id}/review/release`, { method: "POST" }),
  queueSection: (id: string, sectionId: string) =>
    request<Newsletter>(`/newsletters/${id}/sections/${sectionId}/queue`, { method: "POST" }),
  publicReview: (token: string) =>
    request<Newsletter>(`/public/reviews/${token}`, { auth: false }),
  publicApprove: (token: string) =>
    request<Newsletter>(`/public/reviews/${token}/approve`, { method: "POST", auth: false }),
  publicDeny: (token: string) =>
    request<Newsletter>(`/public/reviews/${token}/deny`, { method: "POST", auth: false }),
  publicApproveSection: (token: string, sectionId: string) =>
    request<Newsletter>(`/public/reviews/${token}/sections/${sectionId}/approve`, {
      method: "POST",
      auth: false,
    }),
  publicRecommendations: (token: string, comments: { section_id: string; body: string }[]) =>
    request<Newsletter>(`/public/reviews/${token}/recommendations`, {
      method: "POST",
      auth: false,
      body: JSON.stringify({ comments }),
    }),
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
  denied: "Lead denied",
};
