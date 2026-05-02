"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BookOpen,
  ChevronDown,
  FileText,
  GitBranch,
  LayoutDashboard,
  Play,
  Search,
  Settings,
  Sparkles,
} from "lucide-react";
import { cx } from "@/components/ui";

const links = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/repos", label: "Repositories", icon: GitBranch },
  { href: "/reviews", label: "Reviews", icon: FileText },
  { href: "/skills", label: "Skills", icon: BookOpen },
  { href: "/trigger", label: "Run review", icon: Play },
];

export default function Nav() {
  const path = usePathname();

  return (
    <>
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 border-r border-slate-200 bg-white md:flex md:flex-col">
        <div className="flex h-14 items-center gap-2 border-b border-slate-200 px-4">
          <div className="flex h-8 w-8 items-center justify-center rounded bg-blue-600 text-white">
            <Sparkles size={17} />
          </div>
          <div className="min-w-0">
            <div className="truncate text-sm font-semibold text-slate-950">Claude Flow</div>
            <div className="truncate text-xs text-slate-500">Code review workspace</div>
          </div>
        </div>

        <div className="border-b border-slate-200 px-3 py-3">
          <button className="flex h-9 w-full items-center justify-between rounded border border-slate-300 bg-slate-50 px-3 text-left text-sm text-slate-700 hover:bg-white">
            <span className="truncate">Review System</span>
            <ChevronDown size={15} className="text-slate-500" />
          </button>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-3">
          {links.map(({ href, label, icon: Icon }) => {
            const active = href === "/" ? path === "/" : path.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={cx(
                  "flex h-9 items-center gap-2 rounded px-3 text-sm font-medium transition-colors",
                  active ? "bg-blue-50 text-blue-700" : "text-slate-700 hover:bg-slate-100 hover:text-slate-950",
                )}
              >
                <Icon size={16} />
                <span className="truncate">{label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-slate-200 p-3">
          <div className="rounded border border-slate-200 bg-slate-50 p-3">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-700">
              <Settings size={14} />
              Local backend
            </div>
            <p className="mt-1 text-xs leading-5 text-slate-500">FastAPI through Cloudflare Tunnel</p>
          </div>
        </div>
      </aside>

      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white md:hidden">
        <div className="flex h-14 items-center justify-between px-4">
          <Link href="/" className="flex items-center gap-2 text-sm font-semibold text-slate-950">
            <span className="flex h-8 w-8 items-center justify-center rounded bg-blue-600 text-white">
              <Sparkles size={16} />
            </span>
            Claude Flow
          </Link>
          <Link href="/trigger" className="rounded bg-blue-600 p-2 text-white">
            <Play size={16} />
          </Link>
        </div>
        <div className="flex gap-1 overflow-x-auto px-2 pb-2">
          {links.slice(0, 4).map(({ href, label, icon: Icon }) => {
            const active = href === "/" ? path === "/" : path.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={cx(
                  "flex h-8 shrink-0 items-center gap-1.5 rounded px-2.5 text-xs font-medium",
                  active ? "bg-blue-50 text-blue-700" : "text-slate-600",
                )}
              >
                <Icon size={14} />
                {label}
              </Link>
            );
          })}
        </div>
      </header>

      <div className="hidden h-14 items-center justify-between border-b border-slate-200 bg-white px-5 md:fixed md:left-64 md:right-0 md:top-0 md:z-20 md:flex">
        <div className="flex h-8 w-80 max-w-full items-center gap-2 rounded border border-slate-300 bg-slate-50 px-2.5 text-sm text-slate-500">
          <Search size={15} />
          Search reviews, repos, skills
        </div>
        <Link
          href="/trigger"
          className="inline-flex h-8 items-center gap-1.5 rounded bg-blue-600 px-3 text-sm font-medium text-white hover:bg-blue-700"
        >
          <Play size={15} />
          Create review
        </Link>
      </div>
    </>
  );
}
