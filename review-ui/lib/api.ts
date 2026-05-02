const API_URL = process.env.NEXT_PUBLIC_API_URL!;
const API_KEY = process.env.NEXT_PUBLIC_API_KEY!;

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${API_KEY}`,
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json();
}

// ─── Types ────────────────────────────────────────────────────────────────────

export interface Repo {
  id: number;
  name: string;
  local_dir: string;
  description: string;
  created_at: string;
  github_url: string;
  github_token: string;
  project_name: string;
}

export interface Dev {
  id: number;
  repo_name: string;
  dev_name: string;
  slack_id: string;
  github_username: string;
  github_token: string;
}

export interface Review {
  id: number;
  repo_name: string;
  commit_hash: string;
  pr_number: number | null;
  dev_name: string;
  task: string;
  verdict: string;
  report_path: string;
  created_at: string;
}

export interface ReviewDetail extends Review {
  content: string | null;
}

export interface Job {
  job_id: string;
  type: string;
  status: "queued" | "running" | "done" | "failed";
  created_at: string;
  result: { review_id: number; verdict: string; report_path: string } | null;
  error: string | null;
}

export interface Skill {
  filename: string;
  path: string;
}

export interface Stats {
  total: number;
  ok: number;
  warning: number;
  serious: number;
  by_repo: { repo_name: string; c: number }[];
  by_dev: { dev_name: string; c: number }[];
  by_day: { day: string; c: number }[];
}

// ─── API functions ─────────────────────────────────────────────────────────────

export const getHealth = () => api<{ status: string; claude: boolean; git: boolean }>("/api/health");

// Repos
export const getRepos = () => api<Repo[]>("/api/repos");
export const getRepo = (name: string) => api<Repo>(`/api/repos/${name}`);
export const createRepo = (body: Partial<Repo>) => api<Repo>("/api/repos", { method: "POST", body: JSON.stringify(body) });
export const cloneRepo = (body: { github_url: string; parent_dir: string; name?: string; github_token?: string; description?: string }) =>
  api<{ status: string; repo: Repo; cloned_to: string }>("/api/repos/clone", { method: "POST", body: JSON.stringify(body) });
export const updateRepo = (name: string, body: Partial<Repo>) =>
  api<Repo>(`/api/repos/${name}`, { method: "PATCH", body: JSON.stringify(body) });
export const deleteRepo = (name: string) =>
  fetch(`${API_URL}/api/repos/${name}`, { method: "DELETE", headers: { Authorization: `Bearer ${API_KEY}` } });
export const getRepoSkills = (name: string) => api<{ skills: string[] }>(`/api/repos/${name}/skills`);
export const setRepoSkills = (name: string, skills: string[]) =>
  api<{ skills: string[] }>(`/api/repos/${name}/skills`, { method: "PUT", body: JSON.stringify({ skills }) });

// Devs
export const getDevs = (repo: string) => api<Dev[]>(`/api/repos/${repo}/devs`);
export const createDev = (repo: string, body: Partial<Dev>) =>
  api<Dev>(`/api/repos/${repo}/devs`, { method: "POST", body: JSON.stringify(body) });
export const updateDev = (repo: string, dev: string, body: Partial<Dev>) =>
  api<Dev>(`/api/repos/${repo}/devs/${dev}`, { method: "PATCH", body: JSON.stringify(body) });
export const deleteDev = (repo: string, dev: string) =>
  fetch(`${API_URL}/api/repos/${repo}/devs/${dev}`, { method: "DELETE", headers: { Authorization: `Bearer ${API_KEY}` } });

// Reviews
export const getReviews = (params?: Record<string, string>) => {
  const q = params ? "?" + new URLSearchParams(params).toString() : "";
  return api<Review[]>(`/api/reviews${q}`);
};
export const getReview = (id: number) => api<ReviewDetail>(`/api/reviews/${id}`);
export const triggerCommitReview = (body: { repo: string; commit: string; task: string; slack_id: string }) =>
  api<{ job_id: string }>("/api/reviews/commit", { method: "POST", body: JSON.stringify(body) });
export const triggerPrReview = (body: { repo: string; pr_number: number; slack_id: string }) =>
  api<{ job_id: string }>("/api/reviews/pr", { method: "POST", body: JSON.stringify(body) });

// Jobs
export const getJob = (id: string) => api<Job>(`/api/jobs/${id}`);
export const getJobs = () => api<Job[]>("/api/jobs");

// Skills
export const getSkills = () => api<Skill[]>("/api/skills");
export const getSkill = (filename: string) => api<{ filename: string; content: string }>(`/api/skills/${filename}`);
export const saveSkill = (filename: string, content: string) =>
  api<{ filename: string }>(`/api/skills/${filename}`, { method: "PUT", body: JSON.stringify({ content }) });
export const deleteSkill = (filename: string) =>
  fetch(`${API_URL}/api/skills/${filename}`, { method: "DELETE", headers: { Authorization: `Bearer ${API_KEY}` } });

// Stats
export const getStats = () => api<Stats>("/api/stats");
