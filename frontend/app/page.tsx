"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "../lib/session";

export default function HomePage() {
  const router = useRouter();
  const { estado } = useSession();

  useEffect(() => {
    if (estado === "autenticado") router.replace("/dashboard");
    if (estado === "anonimo") router.replace("/login");
  }, [estado, router]);

  return <p className="cargando">Cargando…</p>;
}
