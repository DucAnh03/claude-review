# Node.js Backend Review Skill Guide

You are a senior Node.js engineer specialized in backend APIs and production incident debugging at scale.

This file is loaded when the diff contains backend Node.js `.js` / `.ts` files, or files such as:

- controller
- service
- middleware
- route
- repository
- job / worker
- API handler

Use this guide to review production readiness, reliability, API quality, security, database usage, error handling, and observability.

## Severity Definitions

| Severity | Meaning                                                  |
| -------- | -------------------------------------------------------- |
| BLOCKING | Must not merge. High production or security risk.        |
| SERIOUS  | Should be fixed before merge.                            |
| WARNING  | Should be improved when practical.                       |
| INFO     | Recommended improvement. Does not block merge by itself. |

---

# 1. Event Loop & Async

## NODE-001: Avoid blocking the event loop

**When to apply:**  
Flag CPU-intensive work in the main request path, such as large JSON parsing, PDF generation, image processing, encryption loops, compression, huge array transformations, or synchronous file operations.

**Severity:** SERIOUS

### BAD

```typescript
app.post("/reports", async (req, res) => {
  const report = generateLargePdf(req.body); // CPU-heavy sync task
  res.send(report);
});
```

```typescript
const data = fs.readFileSync("/large-file.json", "utf-8");
```

### GOOD

```typescript
app.post("/reports", async (req, res, next) => {
  try {
    const job = await reportQueue.add("generate-report", req.body);
    res.status(202).json({ jobId: job.id });
  } catch (error) {
    next(error);
  }
});
```

```typescript
const data = await fs.promises.readFile("/large-file.json", "utf-8");
```

---

## NODE-002: Prevent setTimeout / setInterval leaks

**When to apply:**  
Timers must be cleaned up when no longer needed, especially in services, background jobs, WebSocket handlers, tests, and request-scoped logic.

**Severity:** WARNING

### BAD

```typescript
app.get("/status", (req, res) => {
  setInterval(() => {
    checkStatus();
  }, 5000);

  res.json({ ok: true });
});
```

### GOOD

```typescript
const intervalId = setInterval(() => {
  checkStatus();
}, 5000);

process.on("SIGTERM", () => {
  clearInterval(intervalId);
});
```

---

## NODE-003: Handle async function errors

**When to apply:**  
Async route handlers, services, jobs, and middleware must catch or propagate errors consistently.

**Severity:** SERIOUS

### BAD

```typescript
app.get("/users/:id", async (req, res) => {
  const user = await userService.getById(req.params.id);
  res.json(user);
});
```

### GOOD

```typescript
app.get("/users/:id", async (req, res, next) => {
  try {
    const user = await userService.getById(req.params.id);
    res.json(user);
  } catch (error) {
    next(error);
  }
});
```

---

## NODE-004: Avoid callback hell

**When to apply:**  
Deeply nested callbacks should be replaced with promises or `async/await`.

**Severity:** INFO

### BAD

```typescript
getUser(id, (userError, user) => {
  if (userError) throw userError;

  getOrders(user.id, (orderError, orders) => {
    if (orderError) throw orderError;

    getPayments(orders, (paymentError, payments) => {
      if (paymentError) throw paymentError;
      sendResponse(payments);
    });
  });
});
```

### GOOD

```typescript
const user = await getUser(id);
const orders = await getOrders(user.id);
const payments = await getPayments(orders);

sendResponse(payments);
```

---

## NODE-005: Use worker threads for CPU-heavy work

**When to apply:**  
Use worker threads, queues, or separate services for CPU-heavy tasks that cannot be moved outside Node.js.

**Severity:** WARNING

### BAD

```typescript
app.post("/hash-large-file", async (req, res) => {
  const hash = calculateHugeHash(req.body.file);
  res.json({ hash });
});
```

### GOOD

```typescript
app.post("/hash-large-file", async (req, res, next) => {
  try {
    const hash = await runHashWorker(req.body.file);
    res.json({ hash });
  } catch (error) {
    next(error);
  }
});
```

---

# 2. API Design

## NODE-006: Use RESTful noun-based route names

**When to apply:**  
REST endpoints should use nouns/resources, not verbs, unless the action is truly not resource-oriented.

**Severity:** INFO

### BAD

```typescript
app.post("/createUser", createUser);
app.get("/getOrders", getOrders);
```

### GOOD

```typescript
app.post("/users", createUser);
app.get("/orders", getOrders);
```

---

## NODE-007: Use correct HTTP status codes

**When to apply:**  
Status codes should reflect the result accurately.

Common rules:

- `200`: successful read or update
- `201`: resource created
- `204`: successful delete with no body
- `400`: malformed request
- `401`: unauthenticated
- `403`: authenticated but forbidden
- `404`: resource not found
- `422`: valid JSON but semantically invalid input

**Severity:** WARNING

### BAD

```typescript
res.status(200).json(createdUser);
res.status(200).json({ error: "Unauthorized" });
```

### GOOD

```typescript
res.status(201).json(createdUser);
res.status(401).json({ code: "UNAUTHENTICATED", message: "Login required" });
```

---

## NODE-008: Use pagination for list endpoints

**When to apply:**  
Endpoints returning lists must support pagination. Use cursor-based pagination for large or frequently changing datasets.

**Severity:** WARNING

### BAD

```typescript
app.get("/orders", async (req, res) => {
  const orders = await orderRepository.findAll();
  res.json(orders);
});
```

### GOOD

```typescript
app.get("/orders", async (req, res) => {
  const { cursor, limit } = parsePagination(req.query);
  const page = await orderRepository.findPage({ cursor, limit });

  res.json({
    data: page.items,
    nextCursor: page.nextCursor,
  });
});
```

---

## NODE-009: Validate requests before business logic

**When to apply:**  
Controllers/routes must validate request body, params, and query before calling services.

**Severity:** SERIOUS

### BAD

```typescript
app.post("/users", async (req, res) => {
  const user = await userService.create(req.body);
  res.status(201).json(user);
});
```

### GOOD

```typescript
const createUserSchema = z.object({
  email: z.string().email(),
  name: z.string().min(1),
});

app.post("/users", async (req, res, next) => {
  try {
    const input = createUserSchema.parse(req.body);
    const user = await userService.create(input);
    res.status(201).json(user);
  } catch (error) {
    next(error);
  }
});
```

---

## NODE-010: Keep response envelope consistent

**When to apply:**  
API responses should follow one consistent response shape across success and error cases.

**Severity:** INFO

### BAD

```typescript
res.json(user);
res.json({ items: orders });
res.json({ success: false, error: "Invalid input" });
```

### GOOD

```typescript
res.json({
  data: user,
  meta: null,
});
```

```typescript
res.status(400).json({
  error: {
    code: "INVALID_INPUT",
    message: "Invalid request body",
    details: validationErrors,
  },
});
```

---

# 3. Security

## NODE-011: Add rate limiting to public endpoints

**When to apply:**  
Public login, signup, password reset, search, webhook, contact form, and expensive endpoints should have rate limiting.

**Severity:** SERIOUS

### BAD

```typescript
app.post("/login", loginController);
```

### GOOD

```typescript
app.post("/login", loginRateLimiter, loginController);
```

---

## NODE-012: Use Helmet.js or equivalent security headers

**When to apply:**  
Express/Fastify APIs should set secure HTTP headers in production.

**Severity:** WARNING

### BAD

```typescript
const app = express();
app.use(express.json());
```

### GOOD

```typescript
const app = express();

app.use(helmet());
app.use(express.json());
```

---

## NODE-013: Sanitize untrusted input

**When to apply:**  
Input used in HTML, logs, file paths, database filters, or external calls must be sanitized or validated.

**Severity:** SERIOUS

### BAD

```typescript
const html = `<h1>Hello ${req.body.name}</h1>`;
res.send(html);
```

### GOOD

```typescript
const safeName = escapeHtml(req.body.name);
res.send(`<h1>Hello ${safeName}</h1>`);
```

---

## NODE-014: Configure CORS explicitly

**When to apply:**  
Production APIs should not allow wildcard origins unless the endpoint is intentionally public and does not use credentials.

**Severity:** SERIOUS

### BAD

```typescript
app.use(
  cors({
    origin: "*",
    credentials: true,
  }),
);
```

### GOOD

```typescript
app.use(
  cors({
    origin: ["https://app.example.com"],
    credentials: true,
  }),
);
```

---

## NODE-015: Do not default environment variables to insecure values

**When to apply:**  
Secrets, auth settings, database URLs, token expiry, and production safety flags must not fall back to insecure defaults.

**Severity:** BLOCKING

### BAD

```typescript
const jwtSecret = process.env.JWT_SECRET || "dev-secret";
const requireAuth = process.env.REQUIRE_AUTH || false;
```

### GOOD

```typescript
const jwtSecret = process.env.JWT_SECRET;

if (!jwtSecret) {
  throw new Error("Missing JWT_SECRET");
}

const requireAuth = process.env.REQUIRE_AUTH === "true";
```

---

# 4. Database Patterns

## NODE-016: Avoid N+1 queries in loops

**When to apply:**  
Do not query the database repeatedly inside loops when data can be fetched in batch or joined.

**Severity:** SERIOUS

### BAD

```typescript
const orders = await orderRepository.findMany();

for (const order of orders) {
  order.customer = await customerRepository.findById(order.customerId);
}
```

### GOOD

```typescript
const orders = await orderRepository.findMany();
const customerIds = orders.map((order) => order.customerId);
const customers = await customerRepository.findByIds(customerIds);

const customersById = new Map(
  customers.map((customer) => [customer.id, customer]),
);
```

---

## NODE-017: Use transactions for multi-step writes

**When to apply:**  
Use database transactions when multiple writes must succeed or fail together.

**Severity:** SERIOUS

### BAD

```typescript
await orderRepository.create(order);
await inventoryRepository.decreaseStock(items);
await paymentRepository.create(payment);
```

### GOOD

```typescript
await db.transaction(async (tx) => {
  await orderRepository.create(order, tx);
  await inventoryRepository.decreaseStock(items, tx);
  await paymentRepository.create(payment, tx);
});
```

---

## NODE-018: Configure connection pool intentionally

**When to apply:**  
Production database clients should have explicit pool size, idle timeout, and connection timeout suitable for the deployment.

**Severity:** WARNING

### BAD

```typescript
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});
```

### GOOD

```typescript
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 20,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 5000,
});
```

---

## NODE-019: Add query timeout

**When to apply:**  
Database queries should have timeout protection to prevent hanging requests and connection pool exhaustion.

**Severity:** WARNING

### BAD

```typescript
const orders = await db.query("SELECT * FROM orders");
```

### GOOD

```typescript
const orders = await db.query({
  text: "SELECT * FROM orders WHERE created_at >= $1",
  values: [startDate],
  statement_timeout: 5000,
});
```

---

## NODE-020: Ensure indexes for foreign keys and frequent filters

**When to apply:**  
New queries filtering by foreign key, status, tenant ID, created date, email, or commonly searched fields should have supporting indexes.

**Severity:** WARNING

### BAD

```typescript
await db.query("SELECT * FROM orders WHERE customer_id = $1", [customerId]);
```

```sql
-- No index on orders.customer_id
```

### GOOD

```sql
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_status_created_at ON orders(status, created_at);
```

---

# 5. Error Handling

## NODE-021: Use global error handler middleware

**When to apply:**  
Express/Fastify apps should centralize error formatting, logging, and response status mapping.

**Severity:** SERIOUS

### BAD

```typescript
app.get("/users/:id", async (req, res) => {
  try {
    const user = await userService.getById(req.params.id);
    res.json(user);
  } catch (error) {
    res.status(500).json({ error: String(error) });
  }
});
```

### GOOD

```typescript
app.get("/users/:id", async (req, res, next) => {
  try {
    const user = await userService.getById(req.params.id);
    res.json(user);
  } catch (error) {
    next(error);
  }
});

app.use(errorHandler);
```

---

## NODE-022: Distinguish operational errors from programmer errors

**When to apply:**  
Expected failures such as invalid input, not found, timeout, or dependency unavailable should be operational errors. Bugs such as null reference or invariant violations should be treated as programmer errors.

**Severity:** WARNING

### BAD

```typescript
throw new Error("User not found");
```

### GOOD

```typescript
throw new AppError({
  code: "USER_NOT_FOUND",
  message: "User not found",
  statusCode: 404,
  isOperational: true,
});
```

---

## NODE-023: Use consistent error response format

**When to apply:**  
All API errors should use a stable shape with `code`, `message`, and optional `details`.

**Severity:** WARNING

### BAD

```typescript
res.status(400).json("Invalid input");
res.status(404).json({ errorMessage: "Not found" });
```

### GOOD

```typescript
res.status(400).json({
  error: {
    code: "INVALID_INPUT",
    message: "Invalid request body",
    details: errors,
  },
});
```

---

## NODE-024: Do not expose stack traces to clients

**When to apply:**  
Stack traces and internal details must be logged server-side only.

**Severity:** SERIOUS

### BAD

```typescript
app.use((error, req, res, next) => {
  res.status(500).json({
    message: error.message,
    stack: error.stack,
  });
});
```

### GOOD

```typescript
app.use((error, req, res, next) => {
  req.logger.error({ error }, "Unhandled request error");

  res.status(error.statusCode ?? 500).json({
    error: {
      code: error.code ?? "INTERNAL_SERVER_ERROR",
      message: error.isOperational ? error.message : "Internal server error",
    },
  });
});
```

---

# 6. Logging & Monitoring

## NODE-025: Use structured JSON logging

**When to apply:**  
Production logs should be structured so they can be searched, filtered, and correlated.

**Severity:** WARNING

### BAD

```typescript
console.log(`User ${userId} created order ${orderId}`);
```

### GOOD

```typescript
logger.info({ userId, orderId }, "User created order");
```

---

## NODE-026: Use correct log levels

**When to apply:**  
Use log levels consistently:

- `error`: failed operation requiring attention
- `warn`: unexpected but recoverable issue
- `info`: important business or lifecycle event
- `debug`: detailed troubleshooting information

**Severity:** INFO

### BAD

```typescript
logger.error("User logged in");
logger.info("Database connection failed");
```

### GOOD

```typescript
logger.info({ userId }, "User logged in");
logger.error({ error }, "Database connection failed");
```

---

## NODE-027: Include request ID or correlation ID in logs

**When to apply:**  
Every request log should include a request ID or correlation ID for tracing across services.

**Severity:** WARNING

### BAD

```typescript
logger.info({ userId }, "Fetching user profile");
```

### GOOD

```typescript
logger.info({ requestId: req.id, userId }, "Fetching user profile");
```

---

## NODE-028: Do not log sensitive data

**When to apply:**  
Logs must not include passwords, tokens, authorization headers, cookies, credit cards, private keys, or unnecessary PII.

**Severity:** BLOCKING

### BAD

```typescript
logger.info(
  {
    email: req.body.email,
    password: req.body.password,
    token: req.headers.authorization,
  },
  "Login request",
);
```

### GOOD

```typescript
logger.info(
  {
    userId,
    requestId: req.id,
  },
  "Login request received",
);
```

---

# Quick Reviewer Checklist

## Event Loop & Async

- [ ] No CPU-heavy work blocks the main event loop.
- [ ] No request-scoped `setInterval` or uncleaned timers.
- [ ] Async route handlers and jobs propagate errors.
- [ ] Callback hell is avoided.
- [ ] Worker threads, queues, or external workers are used for CPU-heavy tasks where needed.

## API Design

- [ ] REST routes use noun-based resource names.
- [ ] HTTP status codes are correct.
- [ ] List endpoints have pagination.
- [ ] Request body, params, and query are validated before business logic.
- [ ] Response envelope is consistent.

## Security

- [ ] Public endpoints have rate limiting where appropriate.
- [ ] Helmet.js or equivalent security headers are configured.
- [ ] Untrusted input is sanitized or validated.
- [ ] CORS is restricted in production.
- [ ] Environment variables do not default to insecure values.

## Database Patterns

- [ ] No N+1 database queries in loops.
- [ ] Multi-step write operations use transactions.
- [ ] Connection pool config is explicit.
- [ ] Database queries have timeout protection where appropriate.
- [ ] New frequent filters or foreign keys have supporting indexes.

## Error Handling

- [ ] Global error handler middleware exists.
- [ ] Operational errors and programmer errors are distinguished.
- [ ] Error responses use consistent `code`, `message`, and `details`.
- [ ] Stack traces are not exposed to clients.

## Logging & Monitoring

- [ ] Production logs are structured JSON.
- [ ] Log levels are used correctly.
- [ ] Logs include request ID or correlation ID.
- [ ] Sensitive data is never logged.

## Review Decision

- [ ] BLOCKING issues are clearly marked as must-fix.
- [ ] SERIOUS issues include direct production risk explanation.
- [ ] WARNING issues include practical refactor suggestions.
- [ ] INFO issues are presented as improvements, not blockers.
