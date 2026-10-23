import Disponibilidad from "./Disponibilidad";

/** Columna verde del login y el registro: qué es PC Stock y qué hay disponible. */
export default function PanelAcceso() {
  return (
    <aside className="acceso-panel">
      <div>
        <p className="nombre">PC Stock</p>
        <p className="lema">
          Inventario y ventas de piezas de computador, nuevas y reacondicionadas.
        </p>
      </div>
      <Disponibilidad />
    </aside>
  );
}
