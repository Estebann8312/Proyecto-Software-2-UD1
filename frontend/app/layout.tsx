import type { Metadata } from "next";
import "./global.css";

export const metadata: Metadata = {
  title: "PC Stock",
  description: "Sistema de inventario y ventas de piezas de computador"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
