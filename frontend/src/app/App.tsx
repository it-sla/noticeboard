import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import { Layout } from "../components/Layout";
import { Spinner, ToastProvider } from "../components/ui";
import { DashboardPage } from "../pages/DashboardPage";
import { DepartmentsPage } from "../pages/DepartmentsPage";
import { ExpiryPage } from "../pages/ExpiryPage";
import { EmailHistoryPage } from "../pages/EmailHistoryPage";
import { EmployeesPage } from "../pages/EmployeesPage";
import { LoginPage } from "../pages/LoginPage";
import { NoticeBoardPage } from "../pages/NoticeBoardPage";
import { NoticeDetailPage } from "../pages/NoticeDetailPage";
import { NoticeEditorPage } from "../pages/NoticeEditorPage";
import { SettingsPage } from "../pages/SettingsPage";
import { TemplatesPage } from "../pages/TemplatesPage";
import { AuthProvider, useAuth } from "./auth";
import type { Role } from "../types";
import type { ReactNode } from "react";

export const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
});

function Home() {
  const { can } = useAuth();
  return <Navigate to={can("ADMIN") ? "/dashboard" : "/notices"} replace />;
}

/** UI-level guard only; every endpoint is authorised again on the server. */
function Guard({ min, children }: { min: Role; children: ReactNode }) {
  const { can, loading } = useAuth();
  if (loading) return <Spinner />;
  return can(min) ? children : <Navigate to="/" replace />;
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route element={<Layout />}>
                <Route index element={<Home />} />
                <Route path="dashboard" element={<Guard min="ADMIN"><DashboardPage /></Guard>} />
                <Route path="notices" element={<NoticeBoardPage />} />
                <Route path="notices/:id/edit" element={<Guard min="NOTICE_EDITOR"><NoticeEditorPage /></Guard>} />
                <Route path="notices/:id" element={<NoticeDetailPage />} />
                <Route path="employees" element={<Guard min="ADMIN"><EmployeesPage /></Guard>} />
                <Route path="departments" element={<Guard min="ADMIN"><DepartmentsPage /></Guard>} />
                <Route path="email-history" element={<Guard min="ADMIN"><EmailHistoryPage /></Guard>} />
                <Route path="expiry" element={<Guard min="ADMIN"><ExpiryPage /></Guard>} />
                <Route path="templates" element={<Guard min="ADMIN"><TemplatesPage /></Guard>} />
                <Route path="settings" element={<Guard min="ADMIN"><SettingsPage /></Guard>} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </ToastProvider>
    </QueryClientProvider>
  );
}
