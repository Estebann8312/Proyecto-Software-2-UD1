"use client";

import {
  useEffect,
  useState,
} from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

import {
  isAuthenticated,
  logout,
} from "../../lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }

    setChecking(false);
  }, [router]);

  function handleLogout() {
    logout();
    router.replace("/login");
  }

  if (checking) {
    return (
      <main className="loading-page">
        Verificando sesión...
      </main>
    );
  }

  return (
    <main className="app-layout">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-logo">PC</div>

          <div>
            <strong>PC Stock</strong>
            <span>Clientes</span>
          </div>
        </div>

        <nav className="navigation">
          <Link
            className="active"
            href="/dashboard"
          >
            <span>▦</span>
            Inicio
          </Link>

          <Link href="/dashboard">
            <span>▣</span>
            Mis compras
          </Link>
        </nav>

        <div className="sidebar-footer">
          <button
            type="button"
            className="logout-button"
            onClick={handleLogout}
          >
            Cerrar sesión
          </button>

          <p>Sistema de ventas</p>
          <small>Versión 1.0.0</small>
        </div>
      </aside>

      <section className="content">
        <header className="topbar">
          <div>
            <p className="welcome">
              Bienvenido nuevamente
            </p>

            <h1>Mi cuenta</h1>
          </div>

          <div className="user-profile">
            <div className="avatar">CL</div>

            <div>
              <strong>Cliente</strong>
              <span>Cuenta activa</span>
            </div>
          </div>
        </header>

        <section className="stats-grid">
          <article className="stat-card">
            <div className="stat-icon blue">
              🛒
            </div>

            <div>
              <p className="stat-title">
                Mis compras
              </p>

              <h2>0</h2>

              <p className="stat-description">
                Compras registradas
              </p>
            </div>
          </article>

          <article className="stat-card">
            <div className="stat-icon green">
              ✓
            </div>

            <div>
              <p className="stat-title">
                Cuenta
              </p>

              <h2>Activa</h2>

              <p className="stat-description">
                Acceso habilitado
              </p>
            </div>
          </article>

          <article className="stat-card">
            <div className="stat-icon purple">
              ★
            </div>

            <div>
              <p className="stat-title">
                Estado
              </p>

              <h2>Cliente</h2>

              <p className="stat-description">
                Usuario comprador
              </p>
            </div>
          </article>
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>Bienvenido a PC Stock</h2>

              <p>
                Desde aquí podrás consultar tu
                información y tus compras.
              </p>
            </div>
          </div>

          <div className="empty-state">
            Todavía no tienes compras registradas.
          </div>
        </section>
      </section>
    </main>
  );
}