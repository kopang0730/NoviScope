import { useEffect, useState } from "react";
import { getAgentAssignments } from "../api/agent-assignments";
import { getErrorMessage } from "../api/client";
import { getProviders } from "../api/providers";
import type { AgentAssignment, Provider } from "../api/types";
import { useAuth } from "../auth/auth-context";

export type ProviderReadinessData = {
  readonly assignments: readonly AgentAssignment[];
  readonly error: string | null;
  readonly loaded: boolean;
  readonly loading: boolean;
  readonly providers: readonly Provider[];
};

export function useProviderReadinessData(): ProviderReadinessData {
  const { currentUser } = useAuth();
  const [assignments, setAssignments] = useState<AgentAssignment[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [providers, setProviders] = useState<Provider[]>([]);

  useEffect(() => {
    if (!currentUser) {
      setAssignments([]);
      setError(null);
      setLoaded(false);
      setLoading(false);
      setProviders([]);
      return;
    }

    let active = true;
    setError(null);
    setLoaded(false);
    setLoading(true);

    void Promise.all([getProviders(), getAgentAssignments()])
      .then(([nextProviders, nextAssignments]) => {
        if (!active) {
          return;
        }
        setAssignments(nextAssignments);
        setProviders(nextProviders);
        setLoaded(true);
      })
      .catch((nextError) => {
        if (!active) {
          return;
        }
        setError(getErrorMessage(nextError));
        setLoaded(true);
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [currentUser]);

  return { assignments, error, loaded, loading, providers };
}
