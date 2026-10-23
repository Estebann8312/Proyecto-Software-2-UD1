import AppShell from "../../components/AppShell";

/** Todas las rutas dentro de (app) exigen sesión y comparten la barra lateral. */
export default function LayoutApp({ children }: { children: React.ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
