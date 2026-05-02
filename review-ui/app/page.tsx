"use client";

import { useQuery } from "@tanstack/react-query";
import { getHealth, getReviews, getStats, getRepos } from "@/lib/api";
import { PageHeader, Panel, SectionHeader, StatusBadge } from "@/components/ui";
import Link from "next/link";
import { Activity, CheckCircle2, ChevronDown, GitBranch, ShieldAlert } from "lucide-react";
import { useState } from "react";

export default function DashboardPage() {
  const { data: stats } = useQuery({ queryKey: ["stats"], queryFn: getStats });
  const { data: health } = useQuery({ queryKey: ["health"], queryFn: getHealth, refetchInterval: 30_000 });
  const { data: recent = [] } = useQuery({ queryKey: ["reviews-recent"], queryFn: () => getReviews({ limit: "10" }) });
  const { data: repos = [] } = useQuery({ queryKey: ["repos"], queryFn: getRepos });

  const backendOnline = health?.status === "ok";

  return (
    <div className="space-y-5 pb-8">
      <PageHeader
        title="Dashboard"
        description="Review activity, backend status, and recent reports."
        actions={
          <div className="flex items-center gap-2 rounded border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm">
            <span className={`h-2 w-2 rounded-full ${backendOnline ? "bg-green-500" : "bg-red-500"}`} />
            <span className="font-medium text-slate-700">{backendOnline ? "Backend online" : "Backend offline"}</span>
          </div>
        }
      />

      <div className="grid gap-3 px-5 sm:grid-cols-2 xl:grid-cols-4">
        <Metric label="Total reviews" value={stats?.total ?? "-"} icon={<Activity size={17} />} />
        <Metric label="OK" value={stats?.ok ?? "-"} icon={<CheckCircle2 size={17} />} tone="green" />
        <Metric label="Warnings" value={stats?.warning ?? "-"} icon={<ShieldAlert size={17} />} tone="amber" />
        <Metric label="Serious" value={stats?.serious ?? "-"} icon={<ShieldAlert size={17} />} tone="red" />
      </div>

      <div className="grid gap-5 px-5 xl:grid-cols-[1fr_1fr]">
        <Collapsible
          title="Repositories"
          badge={repos.filter(r => r.name).length}
          defaultOpen
        >
          {repos.filter(r => r.name).map((r) => {
            const reviewCount = stats?.by_repo?.find(s => s.repo_name === r.name)?.c ?? 0;
            return (
              <Link key={r.id} href={`/repos/${r.name}`} className="flex items-center justify-between px-4 py-3 text-sm hover:bg-slate-50">
                <div className="flex min-w-0 items-center gap-2">
                  <GitBranch size={15} className="shrink-0 text-blue-600" />
                  <div className="min-w-0">
                    <span className="font-medium text-blue-700">{r.name}</span>
                    {r.description && <p className="truncate text-xs text-slate-400">{r.description}</p>}
                  </div>
                </div>
                <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                  {reviewCount} reviews
                </span>
              </Link>
            );
          })}
          {!repos.filter(r => r.name).length && <Empty text="No repositories configured." />}
        </Collapsible>

        <Collapsible
          title="By developer"
          badge={stats?.by_dev?.length ?? 0}
          defaultOpen
        >
          {stats?.by_dev?.map((d) => (
            <div key={d.dev_name} className="flex items-center justify-between px-4 py-3 text-sm">
              <div className="flex items-center gap-2">
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-xs font-semibold text-indigo-700">
                  {(d.dev_name || "?")[0].toUpperCase()}
                </div>
                <span className="font-medium text-slate-800">{d.dev_name || "Unknown"}</span>
              </div>
              <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                {d.c} reviews
              </span>
            </div>
          ))}
          {!stats?.by_dev?.length && <Empty text="No developer activity yet." />}
        </Collapsible>
      </div>

      <div className="px-5">
        <Panel>
          <SectionHeader title="Recent reviews" description="Latest reports returned by the backend" />
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase text-slate-500">
                <tr>
                  <th className="px-4 py-2">Work item</th>
                  <th className="px-4 py-2">Developer</th>
                  <th className="px-4 py-2">Verdict</th>
                  <th className="px-4 py-2">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {recent.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <Link href={`/reviews/${r.id}`} className="font-medium text-blue-700 hover:underline">
                        {r.repo_name}
                      </Link>
                      <span className="ml-2 font-mono text-xs text-slate-500">
                        {r.pr_number ? `PR #${r.pr_number}` : r.commit_hash?.slice(0, 7)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{r.dev_name || "-"}</td>
                    <td className="px-4 py-3"><StatusBadge value={r.verdict} /></td>
                    <td className="px-4 py-3 text-slate-500">{r.created_at?.slice(0, 10)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!recent.length && <Empty text="No reviews found." />}
          </div>
        </Panel>
      </div>
    </div>
  );
}

function Metric({
  label,
  value,
  icon,
  tone = "blue",
}: {
  label: string;
  value: number | string;
  icon: React.ReactNode;
  tone?: "blue" | "green" | "amber" | "red";
}) {
  const tones = {
    blue: "text-blue-700 bg-blue-50",
    green: "text-green-700 bg-green-50",
    amber: "text-amber-700 bg-amber-50",
    red: "text-red-700 bg-red-50",
  };

  return (
    <Panel className="p-4">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase text-slate-500">{label}</p>
        <span className={`rounded p-1.5 ${tones[tone]}`}>{icon}</span>
      </div>
      <p className="mt-3 text-3xl font-semibold text-slate-950">{value}</p>
    </Panel>
  );
}

function Empty({ text }: { text: string }) {
  return <p className="px-4 py-8 text-center text-sm text-slate-500">{text}</p>;
}

function Collapsible({
  title,
  badge,
  defaultOpen = false,
  children,
}: {
  title: string;
  badge?: number;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-lg border border-slate-200 bg-white">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-slate-50"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-slate-800">{title}</span>
          {badge !== undefined && (
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-500">{badge}</span>
          )}
        </div>
        <ChevronDown size={16} className={`text-slate-400 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && <div className="border-t border-slate-100 divide-y divide-slate-100">{children}</div>}
    </div>
  );
}
