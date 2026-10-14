export type Product = {
  id: number;
  name: string;
  category: string;
  brand: string;
  price: number;
  stock: number;
  status: "Disponible" | "Stock bajo" | "Agotado";
};

export const products: Product[] = [
  {
    id: 1,
    name: "Procesador Ryzen 5 5600G",
    category: "Procesadores",
    brand: "AMD",
    price: 145,
    stock: 12,
    status: "Disponible"
  },
  {
    id: 2,
    name: "Memoria RAM 16GB DDR4",
    category: "Memorias RAM",
    brand: "Kingston",
    price: 48,
    stock: 4,
    status: "Stock bajo"
  },
  {
    id: 3,
    name: "SSD NVMe 1TB",
    category: "Almacenamiento",
    brand: "Western Digital",
    price: 75,
    stock: 8,
    status: "Disponible"
  },
  {
    id: 4,
    name: "Tarjeta gráfica RTX 4060",
    category: "Tarjetas gráficas",
    brand: "NVIDIA",
    price: 320,
    stock: 0,
    status: "Agotado"
  },
  {
    id: 5,
    name: "Fuente de poder 650W",
    category: "Fuentes de poder",
    brand: "Corsair",
    price: 85,
    stock: 6,
    status: "Disponible"
  }
];

export const sales = [
  {
    id: "V-001",
    customer: "Carlos Mendoza",
    date: "2026-10-06",
    total: 193,
    status: "Completada"
  },
  {
    id: "V-002",
    customer: "Ana Torres",
    date: "2026-10-05",
    total: 320,
    status: "Completada"
  },
  {
    id: "V-003",
    customer: "Luis Ramírez",
    date: "2026-10-04",
    total: 85,
    status: "Pendiente"
  }
];