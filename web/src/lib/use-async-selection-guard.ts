import { useCallback, useEffect, useRef } from "react";

export function useAsyncSelectionGuard(selectionKey: string | null) {
  const mountedRef = useRef(false);
  const currentSelectionRef = useRef(selectionKey);
  currentSelectionRef.current = selectionKey;

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  return useCallback(
    () => mountedRef.current && currentSelectionRef.current === selectionKey,
    [selectionKey],
  );
}
