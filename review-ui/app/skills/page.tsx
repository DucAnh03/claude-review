"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getSkill, getSkills, saveSkill, deleteSkill } from "@/lib/api";
import { Button, cx, PageHeader, Panel, SectionHeader, textareaClass } from "@/components/ui";
import { FileText, Plus, Save, Trash2 } from "lucide-react";

const DEFAULT_CONTENT = (name: string) => `# ${name} Skill Guidelines

## Overview
Describe what this skill covers and when it applies.

## Best Practices
- Practice 1
- Practice 2

## Common Issues to Flag
- Issue 1
- Issue 2

## Review Checklist
- [ ] Check 1
- [ ] Check 2
`;

export default function SkillsPage() {
  const qc = useQueryClient();
  const { data: skills = [] } = useQuery({ queryKey: ["skills"], queryFn: getSkills });
  const [selected, setSelected] = useState<string | null>(null);
  const [content, setContent] = useState("");
  const [saved, setSaved] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [newName, setNewName] = useState("");
  const [nameError, setNameError] = useState("");

  const { data: skillContent, isLoading: loadingContent } = useQuery({
    queryKey: ["skill-content", selected],
    queryFn: () => getSkill(selected!),
    enabled: !!selected,
  });

  useEffect(() => {
    if (!skillContent) return;
    setContent(skillContent.content);
    setSaved(false);
  }, [skillContent]);

  const save = useMutation({
    mutationFn: () => saveSkill(selected!, content),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["skills"] });
      setSaved(true);
    },
  });

  const del = useMutation({
    mutationFn: (filename: string) => deleteSkill(filename),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["skills"] });
      setSelected(null);
      setContent("");
    },
  });

  const createSkill = useMutation({
    mutationFn: (filename: string) =>
      saveSkill(filename, DEFAULT_CONTENT(filename.replace(".md", ""))),
    onSuccess: (_, filename) => {
      qc.invalidateQueries({ queryKey: ["skills"] });
      setSelected(filename);
      setShowNew(false);
      setNewName("");
      setNameError("");
      setSaved(false);
    },
    onError: (e: Error) => setNameError(e.message),
  });

  function handleCreate() {
    let name = newName.trim().toLowerCase().replace(/\s+/g, "_");
    if (!name) { setNameError("Nhập tên skill"); return; }
    if (!name.endsWith(".md")) name = name + ".md";
    if (!/^[a-z0-9_\-]+\.md$/.test(name)) {
      setNameError("Chỉ dùng chữ thường, số, _ hoặc -");
      return;
    }
    if (skills.some(s => s.filename === name)) {
      setNameError("Skill này đã tồn tại");
      return;
    }
    createSkill.mutate(name);
  }

  return (
    <div className="space-y-5 pb-8">
      <PageHeader
        title="Skills"
        description="Tạo và chỉnh sửa skill guidelines — Claude sẽ đọc khi review."
        actions={
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => { setShowNew(true); setNameError(""); }}>
              <Plus size={14} /> New skill
            </Button>
            {selected && (
              <Button onClick={() => save.mutate()} disabled={save.isPending || loadingContent}>
                <Save size={14} /> {save.isPending ? "Saving..." : "Save"}
              </Button>
            )}
          </div>
        }
      />

      <div className="grid gap-5 px-5 xl:grid-cols-[280px_minmax(0,1fr)]">
        {/* File list */}
        <Panel className="h-[calc(100vh-150px)] overflow-hidden">
          <SectionHeader title="Skill files" description={`${skills.length} files`} />
          <div className="h-[calc(100%-57px)] overflow-y-auto">
            {skills.map((s) => (
              <div
                key={s.filename}
                className={cx(
                  "group flex items-center gap-2 border-b border-slate-100 px-4 py-3 text-sm",
                  selected === s.filename ? "bg-blue-50" : "hover:bg-slate-50",
                )}
              >
                <button
                  onClick={() => { setSelected(s.filename); setSaved(false); }}
                  className="flex min-w-0 flex-1 items-center gap-2 text-left"
                >
                  <FileText size={15} className={cx("shrink-0", selected === s.filename ? "text-blue-600" : "text-slate-400")} />
                  <span className={cx("truncate font-medium", selected === s.filename ? "text-blue-700" : "text-slate-700")}>
                    {s.filename}
                  </span>
                </button>
                <button
                  onClick={() => { if (confirm(`Xóa "${s.filename}"?`)) del.mutate(s.filename); }}
                  className="hidden rounded p-1 text-slate-400 hover:bg-red-50 hover:text-red-600 group-hover:block"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            ))}
            {skills.length === 0 && (
              <p className="px-4 py-8 text-center text-sm text-slate-500">
                Chưa có skill nào. Bấm <strong>New skill</strong> để tạo.
              </p>
            )}
          </div>
        </Panel>

        {/* Editor */}
        <Panel className="h-[calc(100vh-150px)] overflow-hidden">
          <SectionHeader
            title={selected || "Chọn hoặc tạo skill"}
            description={saved ? "Đã lưu!" : selected ? "Markdown editor — Claude sẽ đọc file này khi review" : "Chọn file ở bên trái hoặc tạo skill mới"}
          />
          {selected ? (
            <textarea
              value={content}
              onChange={(e) => { setContent(e.target.value); setSaved(false); }}
              className={`${textareaClass} h-[calc(100%-57px)] resize-none rounded-none border-0 font-mono leading-6 focus:ring-0`}
              disabled={loadingContent}
              placeholder="Nhập nội dung skill guidelines..."
            />
          ) : (
            <div className="flex h-[calc(100%-57px)] flex-col items-center justify-center gap-3 text-slate-500">
              <FileText size={32} className="text-slate-300" />
              <p className="text-sm">Chọn file ở bên trái để chỉnh sửa</p>
              <Button variant="secondary" onClick={() => { setShowNew(true); setNameError(""); }}>
                <Plus size={14} /> Tạo skill mới
              </Button>
            </div>
          )}
        </Panel>
      </div>

      {/* New skill modal */}
      {showNew && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4">
          <div className="w-full max-w-sm rounded-lg border border-slate-200 bg-white shadow-xl">
            <div className="border-b border-slate-200 px-5 py-4">
              <h2 className="text-base font-semibold text-slate-950">Tạo skill mới</h2>
              <p className="mt-1 text-sm text-slate-500">Tên skill sẽ là tên file .md trong thư mục <code>skills/</code></p>
            </div>
            <div className="space-y-4 px-5 py-4">
              <div>
                <label className="mb-1 block text-xs font-semibold text-slate-600">Tên skill</label>
                <div className="flex items-center gap-1">
                  <input
                    autoFocus
                    value={newName}
                    onChange={(e) => { setNewName(e.target.value); setNameError(""); }}
                    onKeyDown={(e) => e.key === "Enter" && handleCreate()}
                    placeholder="vd: golang, vue, aws"
                    className="flex-1 rounded border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                  />
                  <span className="text-sm text-slate-400">.md</span>
                </div>
                {nameError && <p className="mt-1 text-xs text-red-600">{nameError}</p>}
                <p className="mt-1 text-xs text-slate-400">Chỉ dùng chữ thường, số, _ hoặc -</p>
              </div>
            </div>
            <div className="flex justify-end gap-2 border-t border-slate-200 px-5 py-3">
              <Button variant="secondary" onClick={() => { setShowNew(false); setNewName(""); setNameError(""); }}>
                Hủy
              </Button>
              <Button onClick={handleCreate} disabled={createSkill.isPending}>
                {createSkill.isPending ? "Đang tạo..." : "Tạo"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
