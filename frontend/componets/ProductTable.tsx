"use client";

import { useMemo, useState } from "react";
import { Product } from "../lib/data";

type ProductTableProps = {
  products: Product[];
};

export default function ProductTable({ products }: ProductTableProps) {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("Todas");

  const categories = [
    "Todas",
    ...Array.from(new Set(products.map((product) => product.category)))
  ];

  const filteredProducts = useMemo(() => {
    return products.filter((product) => {
      const matchesSearch =
        product.name.toLowerCase().includes(search.toLowerCase()) ||
        product.brand.toLowerCase().includes(search.toLowerCase());

      const matchesCategory =
        category === "Todas" || product.category === category;

      return matchesSearch && matchesCategory;
    });
  }, [products, search, category]);

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>Productos</h2>
          <p>Gestiona el inventario disponible</p>
        </div>

        <button className="primary-button">+ Nuevo producto</button>
      </div>

      <div className="filters">
        <input
          type="text"
          placeholder="Buscar producto o marca..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />

        <select
          value={category}
          onChange={(event) => setCategory(event.target.value)}
        >
          {categories.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
      </div>

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Producto</th>
              <th>Categoría</th>
              <th>Marca</th>
              <th>Precio</th>
              <th>Stock</th>
              <th>Estado</th>
              <th>Acciones</th>
            </tr>
          </thead>

          <tbody>
            {filteredProducts.map((product) => (
              <tr key={product.id}>
                <td className="product-name">{product.name}</td>
                <td>{product.category}</td>
                <td>{product.brand}</td>
                <td>${product.price.toFixed(2)}</td>
                <td>{product.stock}</td>
                <td>
                  <span
                    className={`badge ${product.status
                      .toLowerCase()
                      .replace(" ", "-")}`}
                  >
                    {product.status}
                  </span>
                </td>
                <td>
                  <button className="action-button">Editar</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {filteredProducts.length === 0 && (
          <div className="empty-state">
            No se encontraron productos.
          </div>
        )}
      </div>
    </section>
  );
}