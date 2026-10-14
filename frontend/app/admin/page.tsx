"use client";

import { useEffect } from "react";

export default function AdminRedirectPage() {
  useEffect(() => {
    window.location.href =
      "http://127.0.0.1:8000/admin/";
  }, []);

  return (
    <main className="loading-page">
      Abriendo administración...
    </main>
  );
}