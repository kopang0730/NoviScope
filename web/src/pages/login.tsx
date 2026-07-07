import type { FormEvent } from "react";
import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { loginUser } from "../api/auth";
import { getErrorMessage } from "../api/client";
import { useAuth } from "../auth/auth-context";
import { Button } from "../components/button";
import { Card, CardHeading } from "../components/card";
import { Input } from "../components/input";
import { useI18n } from "../i18n/i18n-context";
import { readRedirectPath } from "../lib/auth-redirect";

export function LoginPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { authError, setAuthenticatedUser } = useAuth();
  const { t } = useI18n();
  const redirectPath = readRedirectPath(location.state);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const user = await loginUser({ email, password });
      setAuthenticatedUser(user);
      navigate(redirectPath, { replace: true });
    } catch (submitError) {
      setError(submitError instanceof Error ? getErrorMessage(submitError) : "Unexpected error");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <CardHeading description={t("loginDescription")} title={t("login")} />
      {redirectPath !== "/" ? (
        <p className="mt-4 rounded-lg border border-teal-200 bg-teal-50 px-3 py-2 text-sm text-teal-800">
          {t("loginRedirectNotice")}
        </p>
      ) : null}
      <div className="mt-4 flex gap-2 text-sm">
        <span className="rounded-lg bg-teal-50 px-3 py-2 font-medium text-teal-700">{t("login")}</span>
        <Link className="rounded-lg px-3 py-2 text-slate-600 hover:bg-slate-100 hover:text-slate-900" to="/register">
          {t("register")}
        </Link>
      </div>
      <form className="mt-6 space-y-4" onSubmit={(event) => void handleSubmit(event)}>
        <Input autoComplete="email" label={t("email")} onChange={(event) => setEmail(event.target.value)} required type="email" value={email} />
        <Input
          autoComplete="current-password"
          label={t("password")}
          onChange={(event) => setPassword(event.target.value)}
          required
          type="password"
          value={password}
        />
        {error ? <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p> : null}
        {authError ? <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">{authError}</p> : null}
        <Button className="w-full" loading={submitting} type="submit">
          {t("signIn")}
        </Button>
      </form>
    </Card>
  );
}
