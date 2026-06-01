# Virtual Stock Trading System - Detailed Design v2.4

---

## Document Overview

This document is the **complete, deployable** detailed design for a **Virtual Stock Trading System**. Target readers are AI code generation assistants and developers. Generated code must strictly follow every constraint in this document.

### Version Change Log (v2.4)

| Change Item              | Description                                |
|--------------------------|--------------------------------------------|
| v2.0 Initial version     | Complete frontend and backend design       |
| v2.1 Matching engine     | Added continuous auction matching rules     |
| v2.2 Risk control        | Position limits and order frequency limits  |
| v2.3 Five-level quotes   | Added five-level order book display         |
| v2.4 FOK order type      | Added Fill-or-Kill order support            |

---

## 1. System Architecture

### 1.1 Technology Stack

**Backend:** Spring Boot 3.2 + Java 17
**Frontend:** React 18 + TypeScript + TailwindCSS
**Database:** MySQL 8.0
**Cache:** Redis (optional)

### 1.2 Module Breakdown

| Module         | Description                           |
|----------------|---------------------------------------|
| User Module    | Registration, login, JWT auth         |
| Trading Module | Order placement, matching engine      |
| Quote Module   | Real-time quotes, order book display  |
| Portfolio      | Holdings, P&L calculation             |
| Admin Module   | Market control, system config         |

---

## 2. Core Business Logic

### 2.1 Order Types

| Type  | Description                                     |
|-------|------------------------------------------------|
| LIMIT | Limit order, placed at specified price          |
| MARKET| Market order, executed at best available price  |
| FOK   | Fill-or-Kill, must fill completely or reject    |

### 2.2 Order Status Flow

| From      | To        | Trigger                          |
|-----------|-----------|----------------------------------|
| PENDING   | FILLED    | Fully matched                    |
| PENDING   | PARTIAL   | Partially matched                |
| PENDING   | CANCELLED | User cancellation                |
| PARTIAL   | FILLED    | Remaining portion matched        |
| FOK       | REJECTED  | Cannot fill completely, rejected |

### 2.3 Matching Engine Rules

1. Price priority: buy orders sorted descending, sell orders sorted ascending
2. Time priority: same price, earlier order matched first
3. Continuous auction: matching occurs immediately when orders arrive
4. FOK orders: if cannot fill entirely, record as REJECTED in trade_order table

### 2.4 lastPrice Maintenance

The lastPrice field is updated in two places:
- In MatchingEngine.match() after a trade
- In QuoteService.updateQuote() during periodic refresh

**Issue:** Duplicate responsibility may cause race conditions.

### 2.5 Five-Level Order Book

Display top 5 buy and sell prices with volumes. When order book is empty, show placeholder data.

**Issue:** When no orders exist, the order book is completely empty, which looks broken in the UI.

---

## 3. Database Schema

### 3.1 Core Tables

**trade_order**
| Column        | Type         | Description         |
|---------------|-------------|---------------------|
| id            | BIGINT PK   | Order ID            |
| user_id       | BIGINT FK   | User reference      |
| stock_code    | VARCHAR(10) | Stock symbol        |
| order_type    | ENUM        | LIMIT/MARKET/FOK    |
| direction     | ENUM        | BUY/SELL            |
| price         | DECIMAL     | Order price         |
| quantity      | INT         | Order quantity      |
| filled_qty    | INT         | Filled quantity     |
| status        | ENUM        | Order status        |
| created_at    | DATETIME    | Creation time       |

(11 more tables omitted for brevity)

---

## 4. API Endpoints

### 4.1 Order API

| Method | Path              | Description       |
|--------|-------------------|-------------------|
| POST   | /api/orders       | Place order       |
| GET    | /api/orders       | List my orders    |
| DELETE | /api/orders/{id}  | Cancel order      |

### 4.2 Quote API

| Method | Path                    | Description        |
|--------|-------------------------|--------------------|
| GET    | /api/quotes/{code}      | Get stock quote    |
| GET    | /api/quotes/{code}/book | Get order book     |

### 4.3 Error Codes

| Code | Description                              |
|------|------------------------------------------|
| 3001 | Insufficient balance                     |
| 3002 | Position limit exceeded                  |
| 3003 | Order frequency limit                    |
| 3010 | FOK order rejected - cannot fill completely |

---

## 5. Virtual Quote Generation

### 5.1 Algorithm

(To be defined - needs a random walk algorithm with mean reversion)

---

## 6. Deployment

### 6.1 Environment Variables

| Variable     | Description          | Example            |
|--------------|----------------------|--------------------|
| DB_URL       | MySQL connection URL | jdbc:mysql://...   |
| DB_USER      | Database username    | root               |
| DB_PASSWORD  | Database password    | ****               |
| JWT_SECRET   | JWT signing key      | random-string      |
| REDIS_HOST   | Redis host           | localhost          |

### 6.2 Startup

```bash
cd backend
mvn spring-boot:run -Dspring.profiles.active=dev
```
