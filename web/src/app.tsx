import type { ReactNode } from "react";
import { NavLink, Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./auth/auth-context";
import { buttonClassName } from "./components/button";
import { Card } from "./components/card";
import { LanguageToggle } from "./components/language-toggle";
import { useI18n } from "./i18n/i18n-context";
import { CanvasWorkspacePage } from "./pages/canvas-workspace";
import { CreateQuestPage } from "./pages/create-quest";
import { LoginPage } from "./pages/login";
import { ProviderSettingsPage } from "./pages/provider-settings";
import { QuestListPage } from "./pages/quest-list";
import { RegisterPage } from "./pages/register";
import { StageDetailPage } from "./pages/stage-detail";

function navLinkClassName(isActive: boolean) {
  return [
    "rounded-lg px-3 py-2 text-sm font-medium transition",
    isActive
      ? "bg-teal-600 text-white shadow-sm"
      : "text-slate-700 hover:bg-slate-100 hover:text-slate-900",
  ].join(" ");
}

function WorkspaceLayout() {
  const { currentUser, authError, authReady, logout } = useAuth();
  const { t } = useI18n();

  return (
    <div className="min-h-screen bg-canvas text-ink">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-[1440px] flex-col items-start gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:gap-4 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-teal-100 text-xl font-semibold text-teal-700">
              N
            </div>
            <div>
              <p className="text-lg font-semibold">NoviScope</p>
              <p className="text-xs text-slate-500">{t("workspaceSubtitle")}</p>
            </div>
          </div>
          <div className="flex min-w-0 flex-wrap items-center gap-3 self-stretch sm:self-auto sm:justify-end">
            <LanguageToggle />
            <div className="min-w-0 text-left sm:text-right">
              <p className="text-sm font-medium text-slate-800">
                {currentUser?.display_name ?? t("guest")}
              </p>
              <p className="break-all text-xs text-slate-500 sm:max-w-none">
                {currentUser?.email ?? (authReady ? t("signInPrompt") : t("checkingSession"))}
              </p>
            </div>
            {currentUser ? (
              <button className={buttonClassName({ variant: "secondary", size: "sm" })} onClick={() => void logout()} type="button">
                {t("logout")}
              </button>
            ) : (
              <div className="flex gap-2">
                <NavLink className={buttonClassName({ variant: "secondary", size: "sm" })} to="/login">
                  {t("login")}
                </NavLink>
                <NavLink className={buttonClassName({ variant: "primary", size: "sm" })} to="/register">
                  {t("register")}
                </NavLink>
              </div>
            )}
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1440px] gap-4 px-4 py-4 sm:px-6 lg:grid-cols-[220px_minmax(0,1fr)]">
        <aside className="h-fit rounded-lg border border-slate-200 bg-white p-3 shadow-panel">
          <nav className="flex flex-col gap-1 md:gap-2">
            <NavLink className={({ isActive }) => navLinkClassName(isActive)} to="/">
              {t("navQuests")}
            </NavLink>
            <NavLink className={({ isActive }) => navLinkClassName(isActive)} to="/canvas">
              {t("navCanvas")}
            </NavLink>
            <NavLink className={({ isActive }) => navLinkClassName(isActive)} to="/quests/new">
              {t("navNewQuest")}
            </NavLink>
            <NavLink className={({ isActive }) => navLinkClassName(isActive)} to="/providers">
              {t("navProviders")}
            </NavLink>
          </nav>
          <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 px-3 py-3 text-xs text-slate-600">
            <p className="font-medium text-slate-800">{t("labAlphaTitle")}</p>
            <p className="mt-1">{t("labAlphaDescription")}</p>
          </div>
        </aside>

        <main className="min-w-0 space-y-4">
          {authError ? (
            <Card className="border-amber-200 bg-amber-50">
              <p className="text-sm font-medium text-amber-900">{t("backendConnectionIssue")}</p>
              <p className="mt-1 text-sm text-amber-800">{authError}</p>
            </Card>
          ) : null}
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function AuthLayout({ children }: { children: ReactNode }) {
  const { currentUser } = useAuth();
  const { t } = useI18n();

  if (currentUser) {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="min-h-screen bg-canvas px-4 py-8 sm:px-6">
      <div className="mx-auto flex max-w-5xl flex-col gap-6 lg:grid lg:grid-cols-[1.1fr_0.9fr] lg:items-start">
        <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-panel sm:p-8">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-teal-100 text-xl font-semibold text-teal-700">
                N
              </div>
              <div>
                <p className="text-xl font-semibold text-slate-900">NoviScope</p>
                <p className="text-sm text-slate-500">{t("authWorkspaceSubtitle")}</p>
              </div>
            </div>
            <LanguageToggle />
          </div>
          <div className="mt-6 grid gap-4 text-sm text-slate-600 sm:grid-cols-3">
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <p className="font-medium text-slate-900">{t("authFeatureQuestTitle")}</p>
              <p className="mt-1">{t("authFeatureQuestDescription")}</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <p className="font-medium text-slate-900">{t("authFeatureProviderTitle")}</p>
              <p className="mt-1">{t("authFeatureProviderDescription")}</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <p className="font-medium text-slate-900">{t("authFeatureInviteTitle")}</p>
              <p className="mt-1">{t("authFeatureInviteDescription")}</p>
            </div>
          </div>
        </section>
        <div className="min-w-0">{children}</div>
      </div>
    </div>
  );
}

function ProtectedWorkspaceLayout() {
  const { authReady, currentUser } = useAuth();
  const { t } = useI18n();
  const location = useLocation();

  if (!authReady) {
    return (
      <div className="min-h-screen bg-canvas px-4 py-8 sm:px-6">
        <div className="mx-auto max-w-xl">
          <Card>
            <p className="text-sm font-medium text-slate-900">{t("checkingSession")}</p>
            <p className="mt-1 text-sm text-slate-600">{t("protectedSessionDescription")}</p>
          </Card>
        </div>
      </div>
    );
  }

  if (!currentUser) {
    return <Navigate replace state={{ from: `${location.pathname}${location.search}` }} to="/login" />;
  }

  return <WorkspaceLayout />;
}

export function App() {
  return (
    <Routes>
      <Route
        path="/login"
        element={
          <AuthLayout>
            <LoginPage />
          </AuthLayout>
        }
      />
      <Route
        path="/register"
        element={
          <AuthLayout>
            <RegisterPage />
          </AuthLayout>
        }
      />
      <Route element={<ProtectedWorkspaceLayout />}>
        <Route path="/" element={<QuestListPage />} />
        <Route path="/canvas" element={<CanvasWorkspacePage />} />
        <Route path="/quests/new" element={<CreateQuestPage />} />
        <Route path="/providers" element={<ProviderSettingsPage />} />
        <Route path="/stages/:stageId" element={<StageDetailPage />} />
        <Route path="*" element={<Navigate replace to="/" />} />
      </Route>
    </Routes>
  );
}
