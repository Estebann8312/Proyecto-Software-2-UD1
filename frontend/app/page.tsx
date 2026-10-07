"use client";

export default function DashboardPage() {
  return (
    <main className="app-layout">
      <aside className="sidebar">
        <nav className="navigation">
          <a className="active" href="#">
            <span>▦</span>
            Dashboard
          </a>

          <a href="#productos">
            <span>▣</span>
            Productos
          </a>

          <a href="#ventas">
            <span>▤</span>
            Ventas
          </a>

          <a href="#">
            <span>⚙</span>
            Configuración
          </a>
        </nav>

        <div className="sidebar-footer">
          <p>Sistema de inventario</p>
          <small>Versión 1.0.0</small>
        </div>
      </aside>

      <section className="content">
        <header className="topbar">
          <div>
            <p className="welcome">Bienvenido nuevamente</p>
            <h1>Dashboard</h1>
          </div>

          <div className="user-profile">
            <div className="avatar">AD</div>

            <div>
              <strong>Administrador</strong>
              <span>admin@pcstock.com</span>
            </div>
          </div>
        </header>
      </section>
    </main>
  );
}