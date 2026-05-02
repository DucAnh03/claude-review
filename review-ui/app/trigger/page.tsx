"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { getDevs, getJob, getRepos, triggerCommitReview, triggerPrReview } from "@/lib/api";
import type { Job } from "@/lib/api";
import { Button, inputClass, PageHeader, Panel, SectionHeader, StatusBadge, textareaClass } from "@/components/ui";
import { GitPullRequest, Play } from "lucide-react";

export default function TriggerPage() {
  const [type, setType] = useState<"commit" | "pr">("commit");
  const [form, setForm] = useState({ repo: "", commit: "", pr_number: "", task: "", slack_id: "" });
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState("");

  const { data: repos = [] } = useQuery({ queryKey: ["repos"], queryFn: getRepos });
  const { data: devs = [] } = useQuery({ queryKey: ["devs", form.repo], queryFn: () => getDevs(form.repo), enabled: !!form.repo });

  const trigger = useMutation({
    mutationFn: () =>
      type === "commit"
        ? triggerCommitReview({ repo: form.repo, commit: form.commit, task: form.task, slack_id: form.slack_id })
        : triggerPrReview({ repo: form.repo, pr_number: Number(form.pr_number), slack_id: form.slack_id }),
    onSuccess: (d) => {
      setJobId(d.job_id);
      setJob(null);
      setError("");
    },
    onError: (e: Error) => setError(e.message),
  });

  useEffect(() => {
    if (!jobId || job?.status === "done" || job?.status === "failed") return;
    const iv = setInterval(async () => {
      try {
        setJob(await getJob(jobId));
      } catch {
        // Keep the current status visible while the backend recovers.
      }
    }, 2500);
    return () => clearInterval(iv);
  }, [jobId, job?.status]);

  const canSubmit = !!form.repo && (type === "commit" ? !!form.commit : !!form.pr_number) && !trigger.isPending;

  return (
    <div className="space-y-5 pb-8">
      <PageHeader title="Run review" description="Submit a commit or pull request review job and watch its worker status." />

      <div className="grid gap-5 px-5 xl:grid-cols-[minmax(0,640px)_minmax(320px,1fr)]">
        <Panel>
          <SectionHeader title="Review request" description="The backend queues jobs and runs them sequentially." />
          <div className="space-y-4 p-4">
            <div className="inline-flex rounded border border-slate-300 bg-slate-100 p-0.5">
              {(["commit", "pr"] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setType(t)}
                  className={`h-8 rounded px-3 text-sm font-medium ${type === t ? "bg-white text-blue-700 shadow-sm" : "text-slate-600 hover:text-slate-950"}`}
                >
                  {t === "commit" ? "Commit" : "Pull request"}
                </button>
              ))}
            </div>

            <label className="block">
              <span className="mb-1 block text-xs font-semibold text-slate-600">Repository *</span>
              <select value={form.repo} onChange={(e) => setForm({ ...form, repo: e.target.value, slack_id: "" })} className={inputClass}>
                <option value="">Select repo...</option>
                {repos.map((r) => <option key={r.name} value={r.name}>{r.name}</option>)}
              </select>
            </label>

            {type === "commit" ? (
              <>
                <Field label="Commit hash *" value={form.commit} onChange={(v) => setForm({ ...form, commit: v })} placeholder="b58927b" />
                <label className="block">
                  <span className="mb-1 block text-xs font-semibold text-slate-600">Task description</span>
                  <textarea
                    value={form.task}
                    onChange={(e) => setForm({ ...form, task: e.target.value })}
                    placeholder="What should Claude focus on?"
                    className={`${textareaClass} min-h-24 resize-y`}
                  />
                </label>
              </>
            ) : (
              <Field label="PR number *" value={form.pr_number} onChange={(v) => setForm({ ...form, pr_number: v })} placeholder="1" type="number" />
            )}

            <label className="block">
              <span className="mb-1 block text-xs font-semibold text-slate-600">Developer</span>
              {devs.length > 0 ? (
                <select value={form.slack_id} onChange={(e) => setForm({ ...form, slack_id: e.target.value })} className={inputClass}>
                  <option value="">Select developer...</option>
                  {devs.map((d) => <option key={d.id} value={d.slack_id || d.dev_name}>{d.dev_name}</option>)}
                </select>
              ) : (
                <input value={form.slack_id} onChange={(e) => setForm({ ...form, slack_id: e.target.value })} placeholder="Slack user id" className={inputClass} />
              )}
            </label>

            {error && <p className="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

            <Button onClick={() => trigger.mutate()} disabled={!canSubmit} className="w-full">
              <Play size={15} /> {trigger.isPending ? "Submitting..." : "Run review"}
            </Button>
          </div>
        </Panel>

        <Panel className="h-fit">
          <SectionHeader title="Job status" description="Polls every 2.5 seconds while active" />
          {jobId ? (
            <div className="space-y-4 p-4">
              <div>
                <div className="mb-1 text-xs font-semibold uppercase text-slate-500">Job ID</div>
                <div className="break-all rounded bg-slate-100 px-2 py-1 font-mono text-xs text-slate-700">{jobId}</div>
              </div>

              {job ? (
                <div className="space-y-3">
                  <StatusBadge value={job.status} />
                  {job.result && (
                    <div className="rounded border border-slate-200 bg-slate-50 p-3 text-sm">
                      <div className="mb-2 flex items-center justify-between">
                        <span className="font-semibold text-slate-800">Result</span>
                        <StatusBadge value={job.result.verdict} />
                      </div>
                      <a href={`/reviews/${job.result.review_id}`} className="inline-flex items-center gap-1 text-blue-700 hover:underline">
                        <GitPullRequest size={14} /> View report
                      </a>
                    </div>
                  )}
                  {job.error && <p className="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{job.error}</p>}
                </div>
              ) : (
                <p className="text-sm text-slate-500">Queued, waiting for worker...</p>
              )}
            </div>
          ) : (
            <p className="px-4 py-8 text-center text-sm text-slate-500">Submit a review to see job progress here.</p>
          )}
        </Panel>
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-semibold text-slate-600">{label}</span>
      <input type={type} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} className={inputClass} />
    </label>
  );
}
