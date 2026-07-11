import type { ProviderConnectionTestResult } from "../api/providers";
import type { Provider, User } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { canManageProvider } from "../lib/provider-form";
import { formatDateTime, labelFromEnum } from "../lib/format";
import type { ProviderScopeTab } from "../lib/provider-settings-view";
import { Badge } from "./badge";
import { Button } from "./button";
import { Card, CardHeading } from "./card";
import { MobileStack, Table, TableCell, TableHead } from "./table";

type ProviderListCardProps = {
  readonly currentUser: User | null;
  readonly loading: boolean;
  readonly loadingError: string | null;
  readonly onEdit: (provider: Provider) => void;
  readonly onTest: (provider: Provider) => void;
  readonly providers: readonly Provider[];
  readonly scope: ProviderScopeTab;
  readonly testResults: Readonly<Record<string, ProviderConnectionTestResult>>;
  readonly testingProviderId: string | null;
};

function statusTone(provider: Provider) {
  return provider.is_active ? "green" : "gray";
}

function ProviderTestResult({ result }: { readonly result: ProviderConnectionTestResult | undefined }) {
  const { t } = useI18n();
  if (!result) {
    return null;
  }

  return (
    <p className={["mt-2 rounded-lg border px-3 py-2 text-xs", result.ok ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-amber-200 bg-amber-50 text-amber-800"].join(" ")}>
      {result.ok ? t("providerTestPassed") : t("providerTestFailed")}: {result.message}
    </p>
  );
}

function ProviderActions({
  currentUser,
  onEdit,
  onTest,
  provider,
  testingProviderId,
}: {
  readonly currentUser: User | null;
  readonly onEdit: (provider: Provider) => void;
  readonly onTest: (provider: Provider) => void;
  readonly provider: Provider;
  readonly testingProviderId: string | null;
}) {
  const { t } = useI18n();

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button loading={testingProviderId === provider.id} onClick={() => onTest(provider)} size="sm" variant="secondary">
        {t("providerTest")}
      </Button>
      {canManageProvider(provider, currentUser) ? (
        <Button onClick={() => onEdit(provider)} size="sm" variant="secondary">
          {t("providerEdit")}
        </Button>
      ) : (
        <span className="text-sm text-slate-600">{t("providerViewOnly")}</span>
      )}
    </div>
  );
}

export function ProviderListCard({
  currentUser,
  loading,
  loadingError,
  onEdit,
  onTest,
  providers,
  scope,
  testResults,
  testingProviderId,
}: ProviderListCardProps) {
  const { t } = useI18n();
  const title =
    scope === "shared"
      ? t("providerSharedCredentialsTitle")
      : t("providerPersonalCredentialsTitle");

  return (
    <Card aria-label={title} className="min-w-0">
      <CardHeading
        description={
          scope === "shared"
            ? t("providerSharedDefaultsDescription")
            : t("providerPersonalOverrideDescription")
        }
        title={title}
      />
      {!currentUser ? (
        <p className="mt-4 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">
          {t("providerSignInPrompt")}
        </p>
      ) : null}
      {loadingError ? <p className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{loadingError}</p> : null}
      {loading ? <p className="mt-4 text-sm text-slate-500">{t("loadingProviderData")}</p> : null}
      {!loading && providers.length === 0 ? (
        <p className="mt-4 rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500">
          {t("noProvidersAvailable")}
        </p>
      ) : null}
      {providers.length > 0 ? (
        <>
          <Table className="mt-4 min-w-[760px]">
            <thead>
              <tr>
                <TableHead>{t("tableName")}</TableHead>
                <TableHead>{t("tableKind")}</TableHead>
                <TableHead>{t("tableModel")}</TableHead>
                <TableHead>{t("tableStatus")}</TableHead>
                <TableHead>{t("providerActions")}</TableHead>
              </tr>
            </thead>
            <tbody>
              {providers.map((provider) => (
                <tr key={provider.id}>
                  <TableCell className="min-w-[190px]">
                    <div className="font-medium text-slate-900">{provider.name}</div>
                    <div className="mt-1 text-xs text-slate-500">{provider.base_url}</div>
                    <ProviderTestResult result={testResults[provider.id]} />
                  </TableCell>
                  <TableCell className="min-w-[120px]">{labelFromEnum(provider.kind)}</TableCell>
                  <TableCell className="min-w-[130px]">{provider.default_model}</TableCell>
                  <TableCell>
                    <Badge tone={statusTone(provider)}>{provider.is_active ? t("providerActive") : t("providerInactive")}</Badge>
                    <p className="mt-2 text-xs text-slate-500">
                      {t("updated")} {formatDateTime(provider.updated_at)}
                    </p>
                  </TableCell>
                  <TableCell>
                    <ProviderActions currentUser={currentUser} onEdit={onEdit} onTest={onTest} provider={provider} testingProviderId={testingProviderId} />
                  </TableCell>
                </tr>
              ))}
            </tbody>
          </Table>
          <MobileStack>
            {providers.map((provider) => (
              <div className="rounded-lg border border-slate-200 bg-white p-4" key={provider.id}>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-medium text-slate-900">{provider.name}</p>
                    <p className="mt-1 text-sm text-slate-500">{provider.default_model}</p>
                  </div>
                  <Badge tone={statusTone(provider)}>{provider.is_active ? t("providerActive") : t("providerInactive")}</Badge>
                </div>
                <p className="mt-3 text-sm text-slate-600">{provider.base_url}</p>
                <p className="mt-3 text-xs text-slate-500">
                  {t("updated")} {formatDateTime(provider.updated_at)}
                </p>
                <ProviderTestResult result={testResults[provider.id]} />
                <div className="mt-4">
                  <ProviderActions currentUser={currentUser} onEdit={onEdit} onTest={onTest} provider={provider} testingProviderId={testingProviderId} />
                </div>
              </div>
            ))}
          </MobileStack>
        </>
      ) : null}
    </Card>
  );
}
