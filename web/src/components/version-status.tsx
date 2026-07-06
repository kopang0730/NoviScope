import { useEffect, useState } from "react";
import { getErrorMessage } from "../api/client";
import { getAdminVersionInfo, getVersionInfo } from "../api/version";
import type { AdminVersionInfo, PublicVersionInfo, UserRole } from "../api/types";
import { useI18n } from "../i18n/i18n-context";

type VersionStatusState = {
  readonly adminError: string | null;
  readonly adminVersion: AdminVersionInfo | null;
  readonly publicError: string | null;
  readonly publicVersion: PublicVersionInfo | null;
};

function versionLabel(
  version: PublicVersionInfo,
  adminVersion: AdminVersionInfo | null,
  dirtyLabel: string,
) {
  const commit = adminVersion?.local_commit_short ? ` · ${adminVersion.local_commit_short}` : "";
  const dirty = adminVersion?.local_dirty ? ` ${dirtyLabel}` : "";
  return `v${version.app_version}${commit}${dirty}`;
}

function remoteStatusTitle(
  adminVersion: AdminVersionInfo | null,
  adminError: string | null,
  fallback: string,
) {
  if (adminVersion?.remote_commit_short) {
    return `GitHub ${adminVersion.github_branch}: ${adminVersion.remote_commit_short}`;
  }
  return adminVersion?.check_error ?? adminError ?? fallback;
}

export function VersionStatus({ userRole = null }: { readonly userRole?: UserRole | null }) {
  const { t } = useI18n();
  const [state, setState] = useState<VersionStatusState>({
    adminError: null,
    adminVersion: null,
    publicError: null,
    publicVersion: null,
  });

  useEffect(() => {
    let active = true;

    async function loadVersion() {
      try {
        const version = await getVersionInfo();
        if (active) {
          setState((current) => ({ ...current, publicError: null, publicVersion: version }));
        }
      } catch (error) {
        if (!(error instanceof Error)) {
          throw error;
        }
        if (active) {
          setState((current) => ({
            ...current,
            publicError: getErrorMessage(error),
            publicVersion: null,
          }));
        }
      }
    }

    void loadVersion();

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;

    async function loadAdminVersion() {
      if (userRole !== "admin") {
        setState((current) => ({ ...current, adminError: null, adminVersion: null }));
        return;
      }

      try {
        const version = await getAdminVersionInfo();
        if (active) {
          setState((current) => ({ ...current, adminError: null, adminVersion: version }));
        }
      } catch (error) {
        if (!(error instanceof Error)) {
          throw error;
        }
        if (active) {
          setState((current) => ({
            ...current,
            adminError: getErrorMessage(error),
            adminVersion: null,
          }));
        }
      }
    }

    void loadAdminVersion();

    return () => {
      active = false;
    };
  }, [userRole]);

  if (!state.publicVersion && !state.publicError) {
    return <p className="text-xs text-slate-400">{t("versionChecking")}</p>;
  }

  if (state.publicError || !state.publicVersion) {
    return (
      <p className="text-xs text-slate-400" title={state.publicError ?? undefined}>
        {t("versionUnavailable")}
      </p>
    );
  }

  const adminVersion = userRole === "admin" ? state.adminVersion : null;
  const title = userRole === "admin"
    ? remoteStatusTitle(adminVersion, state.adminError, t("versionAdminCheck"))
    : undefined;

  return (
    <div className="space-y-1">
      <p className="text-xs text-slate-500" title={title}>
        {versionLabel(state.publicVersion, adminVersion, t("versionDirty"))}
      </p>
      {userRole === "admin" && adminVersion?.update_available ? (
        <p className="rounded-md border border-amber-200 bg-amber-50 px-2 py-1 text-xs font-medium text-amber-800">
          {t("versionUpdateAvailable")}
        </p>
      ) : null}
    </div>
  );
}
