import type { FormEvent } from "react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { loginUser, registerUser } from "../api/auth";
import { getErrorMessage } from "../api/client";
import { useAuth } from "../auth/auth-context";
import { Button } from "../components/button";
import { Card, CardHeading } from "../components/card";
import { Input } from "../components/input";
import { useI18n } from "../i18n/i18n-context";

export function RegisterPage() {
  const navigate = useNavigate();
  const { setAuthenticatedUser } = useAuth();
  const { t } = useI18n();
  const [inviteCode, setInviteCode] = useState("");
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      await registerUser({
        display_name: displayName,
        email,
        invite_code: inviteCode,
        password,
      });
      const user = await loginUser({ email, password });
      setAuthenticatedUser(user);
      navigate("/", { replace: true });
    } catch (submitError) {
      setError(getErrorMessage(submitError));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <CardHeading description={t("registerDescription")} title={t("register")} />
      <div className="mt-4 flex gap-2 text-sm">
        <Link className="rounded-lg px-3 py-2 text-slate-600 hover:bg-slate-100 hover:text-slate-900" to="/login">
          {t("login")}
        </Link>
        <span className="rounded-lg bg-teal-50 px-3 py-2 font-medium text-teal-700">{t("register")}</span>
      </div>
      <form className="mt-6 space-y-4" onSubmit={(event) => void handleSubmit(event)}>
        <Input label={t("inviteCode")} onChange={(event) => setInviteCode(event.target.value)} required value={inviteCode} />
        <Input autoComplete="name" label={t("displayName")} onChange={(event) => setDisplayName(event.target.value)} required value={displayName} />
        <Input autoComplete="email" label={t("email")} onChange={(event) => setEmail(event.target.value)} required type="email" value={email} />
        <Input
          autoComplete="new-password"
          hint={t("passwordHint")}
          label={t("password")}
          minLength={8}
          onChange={(event) => setPassword(event.target.value)}
          required
          type="password"
          value={password}
        />
        {error ? <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p> : null}
        <Button className="w-full" loading={submitting} type="submit">
          {t("createAccount")}
        </Button>
      </form>
    </Card>
  );
}
