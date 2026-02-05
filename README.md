# Micro Foods Market

A Docker Compose based microservice backend for a mini grocery store system built with Flask and SQLite.  
Services: **users**, **products**, **search**, **orders**, **logs**.

## Table of Contents
- Overview
- Services and Ports
- Tech Stack
- How It Works
- Setup and Run
- API Summary
- Example Requests
- Project Structure
- Notes
- License

## Overview
This project implements a microservice architecture where each service owns its own SQLite database and exposes a small HTTP API. Services communicate over HTTP on a shared Docker network.

## Services and Ports
| Service | Container Name | Port | Database |
|---|---|---:|---|
| User Management | `user` | 9000 | `user.db` |
| Product Management | `products` | 9001 | `products.db` |
| Product Search | `search` | 9002 | - |
| Ordering | `orders` | 9003 | - |
| Logging | `logs` | 9004 | `logs.db` |

## Tech Stack
- Python + Flask
- SQLite (`sqlite3`)
- Docker + Docker Compose
- `requests` for service to service HTTP calls
- JWT authentication

## How It Works
- Users register and log in through the **user** service
- Login returns a JWT used to authorize requests to other services
- Employees can create and edit products via the **products** service
- The **search** service supports searching by product name or category and includes `last_mod` sourced from the **logs** service
- The **orders** service accepts an order list, validates products and quantities, and returns a total cost
- The **logs** service records successful actions and allows authorized viewing

## Setup and Run

### Prerequisites
- Docker
- Docker Compose

### Build and start
From the repository root (where `compose.yaml` is located):

```bash
docker compose build
docker compose up
```

### Stop
```bash
docker compose down
```

## API Summary

### User Service (9000)
- `POST /create_user`
  - Form params: `first_name`, `last_name`, `username`, `email_address`, `employee` (bool), `password`, `salt`
- `POST /login`
  - Form params: `username`, `password`
  - Returns: `{ "status": <code>, "jwt": "<token>" }`

### Products Service (9001)
- `POST /create_product` (employee only)
  - Form params: `name`, `price`, `category`
- `POST /edit_product` (employee only)
  - Form params: `name` plus one of `new_price` or `new_category`

### Search Service (9002)
- `GET /search`
  - Query param: exactly one of `product_name` or `category`
  - Returns: `{ "status": <code>, "data": [ ... ] }`

### Orders Service (9003)
- `POST /order`
  - JSON body: `{ "order": [ { "product": "<name>", "quantity": <int> }, ... ] }`
  - Returns: `{ "status": <code>, "cost": <total_or_NULL> }`

### Logs Service (9004)
- `GET /view_log` (authorized)
  - Query param: exactly one of `username` or `product`
  - Returns: `{ "status": <code>, "data": { "1": {...}, "2": {...} } }` or `"NULL"`

### Clear Endpoint (all services)
- `GET /clear`
  - Clears that service database and resets state

## Example Requests

> These examples mirror the test harness behavior:
> - Requests use `127.0.0.1` (not `localhost`)
> - Auth is sent via the `Authorization` header as a JWT
> - `/order` sends the `order` field as **form data** whose value is a JSON string

### Clear all services
```bash
curl http://127.0.0.1:9000/clear
curl http://127.0.0.1:9001/clear
curl http://127.0.0.1:9002/clear
curl http://127.0.0.1:9003/clear
curl http://127.0.0.1:9004/clear
```

### Create users (employee and non-employee)
```bash
# Employee user: jdo
curl -X POST http://127.0.0.1:9000/create_user \
  -d "first_name=john" \
  -d "last_name=doe" \
  -d "username=jdo" \
  -d "email_address=jdo@example.com" \
  -d "password=Examplepassword1" \
  -d "employee=True" \
  -d "salt=FE8x1gO+7z0B"

# Non-employee user: griff
curl -X POST http://127.0.0.1:9000/create_user \
  -d "first_name=peter" \
  -d "last_name=griffin" \
  -d "username=griff" \
  -d "email_address=griff@example.com" \
  -d "password=Examplepassword2" \
  -d "employee=False" \
  -d "salt=xaxkRSzNPnP4"
```

### Login and capture a JWT
```bash
# Login as the employee user (jdo)
curl -X POST http://127.0.0.1:9000/login \
  -d "username=jdo" \
  -d "password=Examplepassword1"
```

Copy the `jwt` from the response and export it:
```bash
export JWT="<paste-jwt-here>"
```

### Create products (employee only)
```bash
curl -X POST http://127.0.0.1:9001/create_product \
  -H "Authorization: Bearer $JWT" \
  -d "name=eggs" \
  -d "price=3.99" \
  -d "category=dairy"

curl -X POST http://127.0.0.1:9001/create_product \
  -H "Authorization: Bearer $JWT" \
  -d "name=cheese" \
  -d "price=5.99" \
  -d "category=dairy"
```

### Edit a product (employee only)
```bash
curl -X POST http://127.0.0.1:9001/edit_product \
  -H "Authorization: Bearer $JWT" \
  -d "name=eggs" \
  -d "new_price=3.98"
```

### Search products
Search by **name**:
```bash
curl "http://127.0.0.1:9002/search?product_name=eggs" \
  -H "Authorization: Bearer $JWT"
```

Search by **category**:
```bash
curl "http://127.0.0.1:9002/search?category=dairy" \
  -H "Authorization: Bearer $JWT"
```

### Place an order
> Test cases send the `order` parameter as form data whose value is a JSON string.

Single-item order:
```bash
curl -X POST http://127.0.0.1:9003/order \
  -H "Authorization: Bearer $JWT" \
  --data-urlencode 'order=[{"product":"cheese","quantity":1}]'
```

Multi-quantity example:
```bash
curl -X POST http://127.0.0.1:9003/order \
  -H "Authorization: Bearer $JWT" \
  --data-urlencode 'order=[{"product":"cheese","quantity":3}]'
```

### View logs (authorized)
View logs for a **user**:
```bash
curl "http://127.0.0.1:9004/view_log?username=jdo" \
  -H "Authorization: Bearer $JWT"
```

View logs for a **product**:
```bash
curl "http://127.0.0.1:9004/view_log?product=eggs" \
  -H "Authorization: Bearer $JWT"
```

## Project Structure
```text
.
├── compose.yaml
├── key.txt
├── user/
│   ├── app.py
│   ├── users.sql
│   └── Dockerfile.users
├── products/
│   ├── app.py
│   ├── products.sql
│   └── Dockerfile.products
├── search/
│   ├── app.py
│   └── Dockerfile.search
├── orders/
│   ├── app.py
│   └── Dockerfile.order
└── logs/
    ├── app.py
    ├── logs.sql
    └── Dockerfile.logs
```

## Notes
- Use parameterized SQL queries to avoid SQL injection
- JWT payload should only include the username
- Each service owns its database and initializes tables on startup (and via `/clear`)
- `key.txt` stores the JWT signing key used by the user service and other services for verification

## License
Proprietary. All rights reserved. See `LICENSE`.
