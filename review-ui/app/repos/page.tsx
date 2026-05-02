"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { cloneRepo, createRepo, deleteRepo, getRepos } from "@/lib/api";
import { Button, inputClass, PageHeader, Panel, SectionHeader } from "@/components/ui";
import Link from "next/link";
import { ExternalLink, GitBranch, Plus, Trash2 } from "lucide-react";

type Mode = "manual" | "clone";

export default function ReposPage() {
  const qc = useQueryClient();
  const { data: repos = [], isLoading } = useQuery({ queryKey: ["repos"], queryFn: getRepos });
  const [showModal, setShowModal] = useState(false);
  const [mode, setMode] = useState<Mode>("clone");
  const [form, setForm] = useState({
    name: "",
    local_dir: "",
    github_url: "",
    github_token: "",
    description: "",
    parent_dir: "D:\\aaaaaaaaaaaaaaaaaaaaaaaaa",
  });
  const [error, setError] = useState("");

  const create = useMutation({
    mutationFn: async () => {
      if (mode === "clone") {
        await cloneRepo({
          github_url: form.github_url,
          parent_dir: form.parent_dir,
          name: form.name || undefined,
          github_token: form.github_token,
          description: form.description,
        });
      } else {
        await createRepo({
          name: form.name,
          local_dir: form.local_dir,
          description: form.description,
          github_url: form.github_url,
          github_token: form.github_token,
        });
      }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["repos"] });
      setShowModal(false);
      setError("");
    },
    onError: (e: Error) => setError(e.message),
  });

  const del = useMutation({
    mutationFn: (name: string) => deleteRepo(name),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["repos"] }),
  });

  return (
    <div className="space-y-5 pb-8">
      <PageHeader
        title="Repositories"
        description="Tracked local repos that the review worker can fetch, checkout, and analyze."
        actions={<Button onClick={() => setShowModal(true)}><Plus size={15} /> Add repo</Button>}
      />

      <div className="px-5">
        <Panel>
          <SectionHeader title="All repositories" description={`${repos.length} configured`} />
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase text-slate-500">
                <tr>
                  <th className="px-4 py-2">Name</th>
                  <th className="px-4 py-2">Local directory</th>
                  <th className="px-4 py-2">Description</th>
                  <th className="px-4 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {repos.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <GitBranch size={15} className="text-blue-600" />
                        <Link href={`/repos/${r.name}`} className="font-medium text-blue-700 hover:underline">
                          {r.name || "(unnamed)"}
                        </Link>
                      </div>
                    </td>
                    <td className="max-w-[420px] truncate px-4 py-3 font-mono text-xs text-slate-500">{r.local_dir}</td>
                    <td className="max-w-[300px] truncate px-4 py-3 text-slate-600">{r.description || "-"}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        {r.github_url && (
                          <a
                            href={r.github_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="rounded p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-950"
                            title="Open GitHub repository"
                          >
                            <ExternalLink size={15} />
                          </a>
                        )}
                        <button
                          onClick={() => {
                            if (confirm(`Delete repo "${r.name}"?`)) del.mutate(r.name);
                          }}
                          className="rounded p-1.5 text-slate-500 hover:bg-red-50 hover:text-red-600"
                          title="Delete repository"
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {isLoading && <p className="px-4 py-8 text-center text-sm text-slate-500">Loading repositories...</p>}
            {!isLoading && repos.length === 0 && <p className="px-4 py-8 text-center text-sm text-slate-500">No repos configured.</p>}
          </div>
        </Panel>
      </div>

      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4">
          <div className="w-full max-w-lg rounded border border-slate-200 bg-white shadow-xl">
            <div className="border-b border-slate-200 px-5 py-4">
              <h2 className="text-base font-semibold text-slate-950">Add repository</h2>
              <p className="mt-1 text-sm text-slate-500">Clone from GitHub or register an existing local path.</p>
            </div>
            <div className="space-y-4 px-5 py-4">
              <div className="inline-flex rounded border border-slate-300 bg-slate-100 p-0.5">
                {(["clone", "manual"] as Mode[]).map((m) => (
                  <button
                    key={m}
                    onClick={() => setMode(m)}
                    className={`h-7 rounded px-3 text-sm font-medium ${mode === m ? "bg-white text-blue-700 shadow-sm" : "text-slate-600 hover:text-slate-950"}`}
                  >
                    {m === "clone" ? "Clone" : "Manual path"}
                  </button>
                ))}
              </div>

              {mode === "clone" ? (
                <>
                  <Field label="GitHub URL *" value={form.github_url} onChange={(v) => setForm({ ...form, github_url: v })} placeholder="https://github.com/user/repo" />
                  <Field label="Parent directory *" value={form.parent_dir} onChange={(v) => setForm({ ...form, parent_dir: v })} placeholder="D:\\projects" />
                  <Field label="Repo name" value={form.name} onChange={(v) => setForm({ ...form, name: v })} placeholder="Auto from URL when empty" />
                  <Field label="GitHub token" value={form.github_token} onChange={(v) => setForm({ ...form, github_token: v })} placeholder="Private repos only" type="password" />
                </>
              ) : (
                <>
                  <Field label="Repo name *" value={form.name} onChange={(v) => setForm({ ...form, name: v })} />
                  <Field label="Local directory *" value={form.local_dir} onChange={(v) => setForm({ ...form, local_dir: v })} placeholder="D:\\projects\\myrepo" />
                  <Field label="GitHub URL" value={form.github_url} onChange={(v) => setForm({ ...form, github_url: v })} placeholder="https://github.com/..." />
                  <Field label="GitHub token" value={form.github_token} onChange={(v) => setForm({ ...form, github_token: v })} placeholder="Private repos only" type="password" />
                </>
              )}
              <Field label="Description" value={form.description} onChange={(v) => setForm({ ...form, description: v })} />

              {error && <p className="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
            </div>
            <div className="flex justify-end gap-2 border-t border-slate-200 px-5 py-3">
              <Button variant="secondary" onClick={() => { setShowModal(false); setError(""); }}>Cancel</Button>
              <Button onClick={() => create.mutate()} disabled={create.isPending}>
                {create.isPending ? "Working..." : mode === "clone" ? "Clone repo" : "Create repo"}
              </Button>
            </div>
          </div>
        </div>
      )}
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
