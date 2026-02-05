DROP TABLE IF EXISTS products;

CREATE TABLE products (
    name TEXT PRIMARY KEY,
    price REAL NOT NULL,
    category TEXT NOT NULL
);