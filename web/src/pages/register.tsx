import type { FormEvent } from "react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { loginUser, registerUser } from "../api/auth";
import { getErrorMessage } from "../api/client";
import { useAuth } from "../auth/auth-context";
import { Button } from "../components/button";
import { Card, CardHeading } from "../components/card";
import { Input } from "../components/input";

export function RegisterPage() {
  const navigate = useNavigate();
  const { setAuthenticatedUser } = useAuth();
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
      <CardHeading description="Use an invite code created by an administrator to create your account." title="Register" />
      <div className="mt-4 flex gap-2 text-sm">
        <Link className="rounded-lg px-3 py-2 text-slate-600 hover:bg-slate-100 hover:text-slate-900" to="/login">
          Login
        </Link>
        <span className="rounded-lg bg-teal-50 px-3 py-2 font-medium text-teal-700">Register</span>
      </div>
      <form className="mt-6 space-y-4" onSubmit={(event) => void handleSubmit(event)}>
        <Input label="Invite Code" onChange={(event) => setInviteCode(event.target.value)} required value={inviteCode} />
        <Input autoComplete="name" label="Display Name" onChange={(event) => setDisplayName(event.target.value)} required value={displayName} />
        <Input autoComplete="email" label="Email" onChange={(event) => setEmail(event.target.value)} required type="email" value={email} />
        <Input
          autoComplete="new-password"
          hint="Use at least eight characters."
          label="Password"
          minLength={8}
          onChange={(event) => setPassword(event.target.value)}
          required
          type="password"
          value={password}
        />
        {error ? <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p> : null}
        <Button className="w-full" loading={submitting} type="submit">
          Create Account
        </Button>
      </form>
    </Card>
  );
}
