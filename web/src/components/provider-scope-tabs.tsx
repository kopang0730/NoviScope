import type { Provider } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { filterProviders, type ProviderScopeTab } from "../lib/provider-settings-view";

type ProviderScopeTabsProps = {
  readonly activeScope: ProviderScopeTab;
  readonly onChange: (scope: ProviderScopeTab) => void;
  readonly providers: readonly Provider[];
};

const scopeTabs = ["shared", "personal"] as const;

export function ProviderScopeTabs({
  activeScope,
  onChange,
  providers,
}: ProviderScopeTabsProps) {
  const { t } = useI18n();

  return (
    <div
      aria-label={t("providerScopeTabsLabel")}
      className="grid grid-cols-2 gap-1 rounded-lg border border-slate-200 bg-slate-50 p-1"
      role="tablist"
    >
      {scopeTabs.map((scope) => {
        const isActive = activeScope === scope;
        const count = filterProviders(providers, scope).length;
        return (
          <button
            aria-selected={isActive}
            className={[
              "min-h-11 rounded-md px-3 text-sm font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500",
              isActive
                ? "bg-teal-600 text-white shadow-sm"
                : "bg-white text-slate-700 hover:text-slate-950",
            ].join(" ")}
            key={scope}
            onClick={() => onChange(scope)}
            role="tab"
            type="button"
          >
            {scope === "shared" ? t("scopeShared") : t("scopePersonal")} ({count})
          </button>
        );
      })}
    </div>
  );
}
