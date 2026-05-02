"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createDev, deleteDev, getDevs, getRepo, getRepoSkills, getSkills, setRepoSkills } from "@/lib/api";
import { Button, inputClass, PageHeader, Panel, SectionHeader } from "@/components/ui";
import Link from "next/link";
import { Plus, Save, Trash2 } from "lucide-react";

export default function RepoDetailPage() {
  const { name } = useParams<{ name: string }>();
  const qc = useQueryClient();

  const { data: repo } = useQuery({ queryKey: ["repo", name], queryFn: () => getRepo(name) });
  const { data: devs = [] } = useQuery({ queryKey: ["devs", name], queryFn: () => getDevs(name) });
  const { data: repoSkills } = useQuery({ queryKey: ["repo-skills", name], queryFn: () => getRepoSkills(name) });
  const { data: allSkills = [] } = useQuery({ queryKey: ["skills"], queryFn: getSkills });

  const [newDev, setNewDev] = useState({ dev_name: "", slack_id: "", github_username: "" });
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);

  const skillOptions = useMemo(
    () => allSkills.map((s) => ({ filename: s.filename, label: skillLabel(s.filename) })),
    [allSkills],
  );

  useEffect(() => {
    if (!repoSkills || !skillOptions.length) return;
    // Normalize: convert any label-format ("Python") → filename-format ("python.md")
    const normalized = repoSkills.skills.map((s) => {
      if (s.endsWith(".md")) return s;
      const match = skillOptions.find((o) => o.label.toLowerCase() === s.toLowerCase());
      return match ? match.filename : s;
    });
    setSelectedSkills(normalized);
  }, [repoSkills, skillOptions]);

  const addDev = useMutation({
    mutationFn: () => createDev(name, newDev),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["devs", name] });
      setNewDev({ dev_name: "", slack_id: "", github_username: "" });
    },
  });

  const delDev = useMutation({
    mutationFn: (dev: string) => deleteDev(name, dev),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["devs", name] }),
  });

  const saveSkills = useMutation({
    mutationFn: () => setRepoSkills(name, selectedSkills),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["repo-skills", name] }),
  });

  const toggleSkill = (skill: string) =>
    setSelectedSkills((prev) => (prev.includes(skill) ? prev.filter((x) => x !== skill) : [...prev, skill]));

  return (
    <div className="space-y-5 pb-8">
      <PageHeader
        title={repo?.name || name}
        description={repo?.description || "Repository settings, assigned skills, and known developers."}
        eyebrow={
          <span>
            <Link href="/repos" className="text-blue-700 hover:underline">Repositories</Link>
            <span className="px-1 text-slate-400">/</span>
            <span>{name}</span>
          </span>
        }
      />

      <div className="grid gap-5 px-5 xl:grid-cols-[minmax(0,1fr)_380px]">
        <div className="space-y-5">
          {repo && (
            <Panel>
              <SectionHeader title="Repository profile" description="Backend path and source metadata" />
              <div className="grid gap-4 p-4 text-sm md:grid-cols-2">
                <Info label="Local directory" value={repo.local_dir} mono />
                <Info label="GitHub URL" value={repo.github_url || "-"} link={repo.github_url} />
                <Info label="Project" value={repo.project_name || "-"} />
                <Info label="Created" value={repo.created_at || "-"} />
              </div>
            </Panel>
          )}

          <Panel>
            <SectionHeader
              title="Assigned skills"
              description="Rules that Claude will read when reviewing this repository"
              actions={
                <Button onClick={() => saveSkills.mutate()} disabled={saveSkills.isPending}>
                  <Save size={14} /> {saveSkills.isPending ? "Saving..." : "Save"}
                </Button>
              }
            />
            <div className="flex flex-wrap gap-2 p-4">
              {skillOptions.map((s) => {
                const active = selectedSkills.includes(s.filename);
                return (
                  <button
                    key={s.filename}
                    onClick={() => toggleSkill(s.filename)}
                    className={`h-8 rounded border px-3 text-sm font-medium ${
                      active ? "border-blue-200 bg-blue-50 text-blue-700" : "border-slate-300 bg-white text-slate-600 hover:bg-slate-50"
                    }`}
                  >
                    {s.label}
                  </button>
                );
              })}
              {!skillOptions.length && <p className="text-sm text-slate-500">No skill files found.</p>}
            </div>
          </Panel>
        </div>

        <Panel>
          <SectionHeader title="Developers" description={`${devs.length} mapped Slack/GitHub users`} />
          <div className="divide-y divide-slate-100">
            {devs.map((d) => (
              <div key={d.id} className="flex items-center justify-between gap-3 px-4 py-3">
                <div className="min-w-0 text-sm">
                  <div className="truncate font-medium text-slate-950">{d.dev_name}</div>
                  <div className="mt-1 flex flex-wrap gap-1.5">
                    {d.slack_id && (
                      <span className="rounded border border-slate-200 bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                        Slack: {d.slack_id}
                      </span>
                    )}
                    {d.github_username && <span className="text-xs text-slate-500">GitHub: {d.github_username}</span>}
                  </div>
                </div>
                <button
                  onClick={() => {
                    if (confirm(`Remove ${d.dev_name}?`)) delDev.mutate(d.dev_name);
                  }}
                  className="rounded p-1.5 text-slate-500 hover:bg-red-50 hover:text-red-600"
                  title="Remove developer"
                >
                  <Trash2 size={15} />
                </button>
              </div>
            ))}
            {!devs.length && <p className="px-4 py-8 text-center text-sm text-slate-500">No developers mapped yet.</p>}
          </div>

          <div className="space-y-3 border-t border-slate-200 p-4">
            <Field label="Name *" value={newDev.dev_name} onChange={(v) => setNewDev({ ...newDev, dev_name: v })} />
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
              <Field label="Slack ID" value={newDev.slack_id} onChange={(v) => setNewDev({ ...newDev, slack_id: v })} />
              <Field label="GitHub username" value={newDev.github_username} onChange={(v) => setNewDev({ ...newDev, github_username: v })} />
            </div>
            <Button onClick={() => addDev.mutate()} disabled={!newDev.dev_name || addDev.isPending} className="w-full">
              <Plus size={14} /> Add developer
            </Button>
          </div>
        </Panel>
      </div>
    </div>
  );
}

function Info({ label, value, mono, link }: { label: string; value: string; mono?: boolean; link?: string }) {
  const content = link && link !== "-" ? (
    <a href={link} target="_blank" rel="noopener noreferrer" className="text-blue-700 hover:underline">
      {value}
    </a>
  ) : (
    <span className={mono ? "font-mono text-xs" : ""}>{value}</span>
  );

  return (
    <div className="min-w-0">
      <div className="text-xs font-semibold uppercase text-slate-500">{label}</div>
      <div className="mt-1 truncate text-slate-800">{content}</div>
    </div>
  );
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-semibold text-slate-600">{label}</span>
      <input value={value} onChange={(e) => onChange(e.target.value)} className={inputClass} />
    </label>
  );
}

function skillLabel(filename: string) {
  const base = filename.replace(/\.md$/i, "");
  const known: Record<string, string> = {
    javascript: "JavaScript",
    typescript: "TypeScript",
    reactjs: "ReactJS",
    nodejs: "NodeJS",
    python: "Python",
    dotnet: ".NET",
  };
  return known[base.toLowerCase()] || base.replace(/[_-]+/g, " ").replace(/\b\w/g, (m) => m.toUpperCase());
}

function normalizeSkill(value: string) {
  return value.replace(/\.md$/i, "").replace(/[^a-z0-9]/gi, "").toLowerCase();
}
