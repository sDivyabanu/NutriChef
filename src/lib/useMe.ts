"use client";

import { useEffect, useState } from "react";

export type Me = { id: string; full_name?: string | null } | null;

/** Current logged-in user (null when logged out, undefined while loading). */
export function useMe(): Me | undefined {
  const [me, setMe] = useState<Me | undefined>(undefined);
  useEffect(() => {
    let alive = true;
    fetch("/api/me")
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => alive && setMe(d?.user ?? null))
      .catch(() => alive && setMe(null));
    return () => {
      alive = false;
    };
  }, []);
  return me;
}
