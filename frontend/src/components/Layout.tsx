import { useState } from "react";
import { NavLink, Navigate, Outlet } from "react-router";
import { useAuth } from "../app/auth";
import type { Role } from "../types";
import { NotificationBell } from "./NotificationBell";
import { Button, Spinner, useToast } from "./ui";

const NAV: { to: string; label: string; min: Role }[] = [
  { to: "/dashboard", label: "Dashboard", min: "ADMIN" },
  { to: "/notices", label: "Notice Board", min: "VIEWER" },
  { to: "/notices/new/edit", label: "Create Notice", min: "NOTICE_EDITOR" },
  { to: "/employees", label: "Employees", min: "ADMIN" },
  { to: "/departments", label: "Departments", min: "ADMIN" },
  { to: "/email-history", label: "Email History", min: "ADMIN" },
  { to: "/expiry", label: "Expiry Tracker", min: "ADMIN" },
  { to: "/templates", label: "Templates", min: "ADMIN" },
  { to: "/settings", label: "Settings", min: "ADMIN" },
];

export function Layout() {
  const { user, loading, can, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const toast = useToast();
  if (loading) return <Spinner />;
  if (!user) return <Navigate to="/login" replace />;
  return (
    <div className="min-h-screen md:flex">
      <header className="flex items-center justify-between bg-black px-4 py-3 text-white md:hidden">
        <span className="font-semibold">Notice Board</span>
        <button aria-expanded={open} aria-controls="sidebar" onClick={() => setOpen(!open)} className="rounded-full px-3 py-1 hover:bg-white/10">
          Menu
        </button>
      </header>
      <aside
        id="sidebar"
        className={`${open ? "block" : "hidden"} w-full shrink-0 bg-tile text-white md:block md:min-h-screen md:w-60`}
      >
        <div className="hidden px-4 py-5 md:block">
          <img src="/logo.jpg" alt="Shangri La Tours" className="w-full rounded-[11px] bg-white p-1.5" />
          <div className="mt-2 text-center text-xs text-[#cccccc]">Employee Notice Board</div>
        </div>
        <nav aria-label="Main" className="space-y-0.5 px-2 pb-4">
          {NAV.filter((n) => can(n.min)).map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `block rounded-[11px] px-3 py-2 text-sm ${isActive ? "bg-white/15 font-semibold text-white" : "text-[#cccccc] hover:bg-white/10"}`
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-white/10 px-4 py-3 text-xs md:mt-auto">
          <div className="truncate font-semibold">{user.name}</div>
          <div className="truncate text-[#cccccc]">{user.role.replace("_", " ")}</div>
          <Button
            variant="ghost"
            className="mt-2 !px-0 !text-[#2997ff] hover:!bg-transparent"
            onClick={() => logout().catch(() => toast("error", "Logout failed"))}
          >
            Sign out
          </Button>
        </div>
      </aside>
      <main className="min-w-0 flex-1 p-4 md:p-8">
        {can("ADMIN") && (
          <div className="mb-2 flex justify-end">
            <NotificationBell />
          </div>
        )}
        <Outlet />
      </main>
    </div>
  );
}
