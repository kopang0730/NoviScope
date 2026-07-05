import type { FormEvent } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { getErrorMessage } from "../api/client";
import { createInvite, getInvites } from "../api/invites";
import type { InviteCode, InviteStatus } from "../api/types";
import { useAuth } from "../auth/auth-context";
import { Badge, type BadgeTone } from "../components/badge";
import { Button } from "../components/button";
import { Card, CardHeading } from "../components/card";
import { Input } from "../components/input";
import { MobileStack, Table, TableCell, TableHead } from "../components/table";
import { useI18n } from "../i18n/i18n-context";
import { formatDateTime, labelFromEnum } from "../lib/format";

function randomHex(length: number) {
  const bytes = new Uint8Array(Math.ceil(length / 2));
  if (globalThis.crypto?.getRandomValues) {
    globalThis.crypto.getRandomValues(bytes);
    return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("").slice(0, length);
  }

  return Math.random().toString(16).slice(2, 2 + length).padEnd(length, "0");
}

function generateInviteCode() {
  return `NS-${randomHex(8).toUpperCase()}`;
}

function statusTone(status: InviteStatus): BadgeTone {
  if (status === "active") {
    return "green";
  }

  if (status === "exhausted") {
    return "amber";
  }

  return "gray";
}

function formatOptionalDateTime(value: string | null, fallback: string) {
  return value ? formatDateTime(value) : fallback;
}

function InviteStatusBadge({ invite }: { readonly invite: InviteCode }) {
  return <Badge tone={statusTone(invite.status)}>{labelFromEnum(invite.status)}</Badge>;
}

function InviteCodeBlock({ invite }: { readonly invite: InviteCode }) {
  return (
    <div className="min-w-0">
      <code className="inline-block max-w-full break-all rounded-md bg-slate-100 px-2 py-1 text-sm font-semibold text-slate-900">
        {invite.code}
      </code>
      <p className="mt-2 break-all text-xs text-slate-500">{invite.id}</p>
    </div>
  );
}

export function AdminInvitesPage() {
  const { currentUser } = useAuth();
  const { t } = useI18n();
  const [invites, setInvites] = useState<InviteCode[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingError, setLoadingError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [createdMessage, setCreatedMessage] = useState<string | null>(null);
  const [code, setCode] = useState(generateInviteCode);
  const [maxUses, setMaxUses] = useState("1");
  const [expiresAtLocal, setExpiresAtLocal] = useState("");

  const isAdmin = currentUser?.role === "admin";
  const activeCount = useMemo(() => invites.filter((invite) => invite.status === "active").length, [invites]);
  const totalCapacity = useMemo(
    () => invites.reduce((total, invite) => total + Math.max(invite.max_uses - invite.used_count, 0), 0),
    [invites],
  );

  const loadInvites = useCallback(async () => {
    if (!isAdmin) {
      setInvites([]);
      setLoading(false);
      setLoadingError(null);
      return;
    }

    setLoading(true);
    setLoadingError(null);
    try {
      setInvites(await getInvites());
    } catch (error) {
      setLoadingError(getErrorMessage(error));
    } finally {
      setLoading(false);
    }
  }, [isAdmin]);

  useEffect(() => {
    void loadInvites();
  }, [loadInvites]);

  function handleGenerateCode() {
    setCode(generateInviteCode());
    setCreatedMessage(null);
    setSubmitError(null);
  }

  async function handleCreateInvite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitError(null);
    setCreatedMessage(null);

    const normalizedCode = code.trim();
    const parsedMaxUses = Number(maxUses);
    if (!Number.isInteger(parsedMaxUses) || parsedMaxUses < 1) {
      setSubmitError(t("inviteMaxUsesInvalid"));
      return;
    }

    const expiresAt = expiresAtLocal ? new Date(expiresAtLocal) : null;
    if (expiresAt && Number.isNaN(expiresAt.getTime())) {
      setSubmitError(t("inviteExpiresAtInvalid"));
      return;
    }

    setSubmitting(true);
    try {
      await createInvite({
        code: normalizedCode,
        expires_at: expiresAt ? expiresAt.toISOString() : null,
        max_uses: parsedMaxUses,
      });
      setCode(generateInviteCode());
      setExpiresAtLocal("");
      setMaxUses("1");
      setCreatedMessage(t("inviteCreated"));
      await loadInvites();
    } catch (error) {
      setSubmitError(getErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  }

  if (!isAdmin) {
    return (
      <Card>
        <CardHeading description={t("inviteManagementDescription")} title={t("inviteManagementTitle")} />
        <p className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          {t("inviteAdminOnly")}
        </p>
      </Card>
    );
  }

  return (
    <div className="grid gap-4 2xl:grid-cols-[minmax(0,1.3fr)_minmax(340px,0.7fr)]">
      <Card>
        <CardHeading description={t("inviteListDescription")} title={t("inviteManagementTitle")} />

        <div className="mt-5 grid gap-3 sm:grid-cols-3">
          <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
            <p className="text-xs font-medium uppercase tracking-[0.08em] text-slate-500">{t("inviteTotal")}</p>
            <p className="mt-1 text-2xl font-semibold text-slate-950">{invites.length}</p>
          </div>
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3">
            <p className="text-xs font-medium uppercase tracking-[0.08em] text-emerald-700">{t("inviteActive")}</p>
            <p className="mt-1 text-2xl font-semibold text-emerald-950">{activeCount}</p>
          </div>
          <div className="rounded-lg border border-sky-200 bg-sky-50 px-4 py-3">
            <p className="text-xs font-medium uppercase tracking-[0.08em] text-sky-700">{t("inviteRemainingUses")}</p>
            <p className="mt-1 text-2xl font-semibold text-sky-950">{totalCapacity}</p>
          </div>
        </div>

        {loadingError ? <p className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{loadingError}</p> : null}
        {loading ? <p className="mt-4 text-sm text-slate-500">{t("inviteLoading")}</p> : null}
        {!loading && invites.length === 0 ? (
          <p className="mt-4 rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500">
            {t("inviteNoInvites")}
          </p>
        ) : null}

        {invites.length > 0 ? (
          <>
            <Table className="mt-4 min-w-[860px]">
              <thead>
                <tr>
                  <TableHead>{t("inviteCodeField")}</TableHead>
                  <TableHead>{t("inviteStatus")}</TableHead>
                  <TableHead>{t("inviteUses")}</TableHead>
                  <TableHead>{t("inviteExpires")}</TableHead>
                  <TableHead>{t("inviteCreatedAt")}</TableHead>
                  <TableHead>{t("inviteUpdatedAt")}</TableHead>
                </tr>
              </thead>
              <tbody>
                {invites.map((invite) => (
                  <tr key={invite.id}>
                    <TableCell className="min-w-[190px]">
                      <InviteCodeBlock invite={invite} />
                    </TableCell>
                    <TableCell>
                      <InviteStatusBadge invite={invite} />
                    </TableCell>
                    <TableCell>
                      {invite.used_count} / {invite.max_uses}
                    </TableCell>
                    <TableCell>{formatOptionalDateTime(invite.expires_at, t("inviteNeverExpires"))}</TableCell>
                    <TableCell>{formatDateTime(invite.created_at)}</TableCell>
                    <TableCell>{formatDateTime(invite.updated_at)}</TableCell>
                  </tr>
                ))}
              </tbody>
            </Table>

            <MobileStack>
              {invites.map((invite) => (
                <div className="rounded-lg border border-slate-200 bg-white p-4" key={invite.id}>
                  <div className="flex items-start justify-between gap-3">
                    <InviteCodeBlock invite={invite} />
                    <InviteStatusBadge invite={invite} />
                  </div>
                  <dl className="mt-4 grid gap-3 text-sm text-slate-600">
                    <div className="flex items-center justify-between gap-3">
                      <dt className="text-slate-500">{t("inviteUses")}</dt>
                      <dd className="font-medium text-slate-900">
                        {invite.used_count} / {invite.max_uses}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-slate-500">{t("inviteExpires")}</dt>
                      <dd className="mt-1 font-medium text-slate-900">{formatOptionalDateTime(invite.expires_at, t("inviteNeverExpires"))}</dd>
                    </div>
                    <div>
                      <dt className="text-slate-500">{t("inviteUpdatedAt")}</dt>
                      <dd className="mt-1 font-medium text-slate-900">{formatDateTime(invite.updated_at)}</dd>
                    </div>
                  </dl>
                </div>
              ))}
            </MobileStack>
          </>
        ) : null}
      </Card>

      <Card>
        <CardHeading description={t("inviteCreateDescription")} title={t("inviteCreateTitle")} />
        <form className="mt-6 space-y-4" onSubmit={(event) => void handleCreateInvite(event)}>
          <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto]">
            <Input
              label={t("inviteCodeField")}
              onChange={(event) => setCode(event.target.value)}
              placeholder={t("inviteCodePlaceholder")}
              required
              value={code}
            />
            <div className="flex items-end">
              <Button className="w-full" onClick={handleGenerateCode} type="button" variant="secondary">
                {t("inviteGenerateCode")}
              </Button>
            </div>
          </div>
          <Input
            label={t("inviteMaxUses")}
            min={1}
            onChange={(event) => setMaxUses(event.target.value)}
            required
            type="number"
            value={maxUses}
          />
          <Input
            hint={t("inviteExpiresAtHint")}
            label={t("inviteExpiresAt")}
            onChange={(event) => setExpiresAtLocal(event.target.value)}
            type="datetime-local"
            value={expiresAtLocal}
          />
          {submitError ? <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{submitError}</p> : null}
          {createdMessage ? <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{createdMessage}</p> : null}
          <Button className="w-full" loading={submitting} type="submit">
            {t("inviteCreate")}
          </Button>
        </form>
      </Card>
    </div>
  );
}
