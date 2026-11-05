import type { Metadata } from "next";
import "./global.css";
import { SessionProvider } from "../lib/session";

export const metadata: Metadata = {
  title: "PC Stock",
  description: "Inventario y ventas de piezas de computador, nuevas y reacondicionadas.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body>
        <SessionProvider>{children}</SessionProvider>
      </body>
    </html>
  );
}
