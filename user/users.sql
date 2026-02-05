DROP TABLE IF EXISTS users;

CREATE TABLE users (
    username TEXT PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email_address TEXT NOT NULL,
    employee TEXT NOT NULL,
    password TEXT NOT NULL,
    salt TEXT NOT NULL
);