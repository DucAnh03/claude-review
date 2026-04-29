# Error Handling Review Rules

You are a senior backend engineer focused on production reliability and observability.

This file is used by an automated AI code reviewer after reading `security.md`.

Applicable tech stack:

- Python / FastAPI
- TypeScript / Next.js
- C# / .NET 8

## Severity Definitions

| Severity | Meaning |
|---|---|
| SERIOUS | Risky for production reliability. Should be fixed before merge. |
| WARNING | Should be improved, but may be acceptable for simple or low-risk code. |

> Note: If the code is simple and the task description gives a valid reason, the AI reviewer may downgrade severity from **SERIOUS** to **WARNING**.

---

# 1. Try/Catch

## ERR-001: Do not catch broad exceptions without logging

**Description:**  
Broad catches such as `Exception`, `Error`, or generic `catch` must log useful context or handle the error properly.

**Severity:** SERIOUS

### BAD

```python
try:
    process_order(order_id)
except Exception:
    return {"status": "failed"}
```

```typescript
try {
  await processOrder(orderId);
} catch {
  return Response.json({ status: "failed" });
}
```

```csharp
try
{
    ProcessOrder(orderId);
}
catch (Exception)
{
    return BadRequest();
}
```

### GOOD

```python
try:
    process_order(order_id)
except Exception:
    logger.exception("Failed to process order", extra={"order_id": order_id})
    raise
```

```typescript
try {
  await processOrder(orderId);
} catch (error) {
  logger.error({ error, orderId }, "Failed to process order");
  throw error;
}
```

```csharp
try
{
    ProcessOrder(orderId);
}
catch (Exception ex)
{
    _logger.LogError(ex, "Failed to process order {OrderId}", orderId);
    throw;
}
```

---

## ERR-002: Do not use empty catch blocks

**Description:**  
Empty catch blocks hide production failures and make debugging difficult.

**Severity:** SERIOUS

### BAD

```python
try:
    send_email()
except Exception:
    pass
```

```typescript
try {
  await sendEmail();
} catch (error) {}
```

```csharp
try
{
    SendEmail();
}
catch
{
}
```

### GOOD

```python
try:
    send_email()
except EmailError as exc:
    logger.warning("Email sending failed", extra={"error": str(exc)})
```

```typescript
try {
  await sendEmail();
} catch (error) {
  logger.warn({ error }, "Email sending failed");
}
```

```csharp
try
{
    SendEmail();
}
catch (EmailException ex)
{
    _logger.LogWarning(ex, "Email sending failed");
}
```

---

## ERR-003: Do not only console.log an error without handling it

**Description:**  
Logging alone is not enough if the function continues in an invalid state. The code must rethrow, return a controlled error, or recover safely.

**Severity:** SERIOUS

### BAD

```typescript
try {
  await chargeCard();
} catch (error) {
  console.log(error);
}
```

```python
try:
    charge_card()
except Exception as exc:
    print(exc)
```

```csharp
try
{
    ChargeCard();
}
catch (Exception ex)
{
    Console.WriteLine(ex);
}
```

### GOOD

```typescript
try {
  await chargeCard();
} catch (error) {
  logger.error({ error }, "Payment failed");
  return Response.json({ error: "Payment failed" }, { status: 502 });
}
```

```python
try:
    charge_card()
except PaymentError:
    logger.exception("Payment failed")
    raise HTTPException(status_code=502, detail="Payment failed")
```

```csharp
try
{
    ChargeCard();
}
catch (PaymentException ex)
{
    _logger.LogError(ex, "Payment failed");
    return StatusCode(502, "Payment failed");
}
```

---

## ERR-004: Catch expected errors in async workflows

**Description:**  
Async request handlers, jobs, or background tasks should handle expected failures instead of allowing uncontrolled crashes.

**Severity:** SERIOUS

### BAD

```python
@app.post("/sync")
async def sync():
    result = await external_sync()
    return result
```

```typescript
export async function POST() {
  const result = await externalSync();
  return Response.json(result);
}
```

```csharp
app.MapPost("/sync", async () =>
{
    var result = await ExternalSync();
    return Results.Ok(result);
});
```

### GOOD

```python
@app.post("/sync")
async def sync():
    try:
        return await external_sync()
    except ExternalServiceError:
        logger.exception("External sync failed")
        raise HTTPException(status_code=502, detail="Sync failed")
```

```typescript
export async function POST() {
  try {
    const result = await externalSync();
    return Response.json(result);
  } catch (error) {
    logger.error({ error }, "External sync failed");
    return Response.json({ error: "Sync failed" }, { status: 502 });
  }
}
```

```csharp
app.MapPost("/sync", async () =>
{
    try
    {
        var result = await ExternalSync();
        return Results.Ok(result);
    }
    catch (ExternalServiceException ex)
    {
        logger.LogError(ex, "External sync failed");
        return Results.StatusCode(502);
    }
});
```

---

# 2. Async Error Handling

## ERR-005: Handle Promise rejections

**Description:**  
Promises must be awaited or handled with `.catch()` to avoid unhandled promise rejections.

**Severity:** SERIOUS

### BAD

```typescript
sendEmail(user.email);
```

### GOOD

```typescript
await sendEmail(user.email);
```

```typescript
sendEmail(user.email).catch((error) => {
  logger.error({ error, userId: user.id }, "Failed to send email");
});
```

---

## ERR-006: Avoid unhandled background task failures

**Description:**  
Fire-and-forget tasks must have explicit error handling.

**Severity:** SERIOUS

### BAD

```python
asyncio.create_task(sync_data())
```

```csharp
_ = SyncDataAsync();
```

### GOOD

```python
async def safe_sync_data():
    try:
        await sync_data()
    except Exception:
        logger.exception("Background sync failed")

asyncio.create_task(safe_sync_data())
```

```csharp
_ = Task.Run(async () =>
{
    try
    {
        await SyncDataAsync();
    }
    catch (Exception ex)
    {
        logger.LogError(ex, "Background sync failed");
    }
});
```

---

## ERR-007: Handle race conditions in concurrent code

**Description:**  
Concurrent updates must use transactions, locks, optimistic concurrency, or idempotency checks where needed.

**Severity:** SERIOUS

### BAD

```typescript
const balance = await getBalance(userId);
await updateBalance(userId, balance - amount);
```

```python
stock = product.stock
product.stock = stock - quantity
db.commit()
```

### GOOD

```typescript
await db.transaction(async (tx) => {
  await tx.decrementBalance(userId, amount);
});
```

```python
with db.begin():
    product = get_product_for_update(product_id)
    product.stock -= quantity
```

---

# 3. Input Validation

## ERR-008: Validate request body before processing

**Description:**  
API endpoints must validate request payloads before using them.

**Severity:** SERIOUS

### BAD

```typescript
const body = await req.json();
await createUser(body.email, body.age);
```

```python
@app.post("/users")
def create_user(body: dict):
    return service.create_user(body["email"])
```

### GOOD

```typescript
const schema = z.object({
  email: z.string().email(),
  age: z.number().int().min(18),
});

const body = schema.parse(await req.json());
```

```python
class CreateUserRequest(BaseModel):
    email: EmailStr
    age: int = Field(ge=18)

@app.post("/users")
def create_user(body: CreateUserRequest):
    return service.create_user(body.email)
```

```csharp
public record CreateUserRequest(
    [Required, EmailAddress] string Email,
    [Range(18, 120)] int Age
);
```

---

## ERR-009: Check null or undefined before accessing properties

**Description:**  
Code must guard nullable objects before reading nested properties.

**Severity:** SERIOUS

### BAD

```typescript
const city = user.profile.address.city;
```

```python
city = user.profile.address.city
```

```csharp
var city = user.Profile.Address.City;
```

### GOOD

```typescript
const city = user?.profile?.address?.city;
if (!city) throw new Error("Missing city");
```

```python
if not user or not user.profile or not user.profile.address:
    raise ValueError("Missing address")
```

```csharp
if (user?.Profile?.Address is null)
{
    throw new InvalidOperationException("Missing address");
}
```

---

## ERR-010: Validate type, range, and format

**Description:**  
Input must be checked for expected type, allowed range, and valid format.

**Severity:** SERIOUS

### BAD

```typescript
const pageSize = Number(req.nextUrl.searchParams.get("pageSize"));
return getItems(pageSize);
```

### GOOD

```typescript
const pageSize = Number(req.nextUrl.searchParams.get("pageSize"));

if (!Number.isInteger(pageSize) || pageSize < 1 || pageSize > 100) {
  return Response.json({ error: "Invalid pageSize" }, { status: 400 });
}
```

---

## ERR-011: Check array bounds before access

**Description:**  
Array or list access must handle empty arrays and invalid indexes.

**Severity:** WARNING

### BAD

```python
first_item = items[0]
```

```typescript
const firstItem = items[0].name;
```

```csharp
var firstItem = items[0];
```

### GOOD

```python
if not items:
    return None
first_item = items[0]
```

```typescript
const firstItem = items[0];
if (!firstItem) return null;
```

```csharp
if (items.Count == 0)
{
    return null;
}
```

---

# 4. External Service Calls

## ERR-012: Set timeout for external HTTP calls

**Description:**  
Third-party HTTP calls must define a timeout to avoid hanging production requests.

**Severity:** SERIOUS

### BAD

```python
requests.get(url)
```

```typescript
await fetch(url);
```

```csharp
await httpClient.GetAsync(url);
```

### GOOD

```python
requests.get(url, timeout=10)
```

```typescript
const controller = new AbortController();
const timeout = setTimeout(() => controller.abort(), 10000);

try {
  await fetch(url, { signal: controller.signal });
} finally {
  clearTimeout(timeout);
}
```

```csharp
httpClient.Timeout = TimeSpan.FromSeconds(10);
await httpClient.GetAsync(url);
```

---

## ERR-013: Handle network errors from external services

**Description:**  
Network failures must be caught and converted into controlled responses or retryable errors.

**Severity:** SERIOUS

### BAD

```typescript
const response = await fetch(paymentUrl);
return await response.json();
```

### GOOD

```typescript
try {
  const response = await fetch(paymentUrl);

  if (!response.ok) {
    throw new Error(`Payment API failed: ${response.status}`);
  }

  return await response.json();
} catch (error) {
  logger.error({ error }, "Payment API request failed");
  throw new ExternalServiceError("Payment service unavailable");
}
```

---

## ERR-014: Add retry logic for transient errors

**Description:**  
Transient failures such as HTTP 429, 502, 503, 504, or temporary network errors should use bounded retry with backoff.

**Severity:** WARNING

### BAD

```python
response = requests.post(url, json=payload)
```

### GOOD

```python
for attempt in range(3):
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code not in [429, 502, 503, 504]:
            break
    except requests.RequestException:
        logger.warning("Retryable request failed", extra={"attempt": attempt + 1})
```

---

## ERR-015: Handle database connection errors

**Description:**  
Database queries should handle connection failures and avoid exposing raw database errors to clients.

**Severity:** SERIOUS

### BAD

```python
@app.get("/orders")
def orders():
    return db.query(Order).all()
```

### GOOD

```python
@app.get("/orders")
def orders():
    try:
        return db.query(Order).all()
    except DatabaseError:
        logger.exception("Database query failed")
        raise HTTPException(status_code=503, detail="Service unavailable")
```

---

# 5. Logging & Observability

## ERR-016: Log production errors with useful context

**Description:**  
Errors must be logged with enough context to diagnose the issue.

**Severity:** SERIOUS

### BAD

```typescript
logger.error("Failed");
```

### GOOD

```typescript
logger.error(
  { requestId, userId, orderId, error },
  "Failed to create order"
);
```

---

## ERR-017: Use a proper logger instead of print or console.log

**Description:**  
Production code should use structured logging instead of `print()`, `console.log()`, or `Console.WriteLine()`.

**Severity:** WARNING

### BAD

```python
print("error", error)
```

```typescript
console.log("error", error);
```

```csharp
Console.WriteLine(error);
```

### GOOD

```python
logger.exception("Operation failed")
```

```typescript
logger.error({ error }, "Operation failed");
```

```csharp
_logger.LogError(ex, "Operation failed");
```

---

## ERR-018: Include error code or error type

**Description:**  
Errors should have a stable code or type so they can be grouped in logs, monitoring, and API responses.

**Severity:** WARNING

### BAD

```json
{
  "error": "Something went wrong"
}
```

### GOOD

```json
{
  "error": {
    "code": "PAYMENT_PROVIDER_UNAVAILABLE",
    "message": "Payment service is temporarily unavailable"
  }
}
```

---

# 6. Edge Cases

## ERR-019: Guard division by zero

**Description:**  
Division must check that the denominator is not zero.

**Severity:** SERIOUS

### BAD

```typescript
const rate = successCount / totalCount;
```

### GOOD

```typescript
const rate = totalCount === 0 ? 0 : successCount / totalCount;
```

---

## ERR-020: Handle empty lists and arrays

**Description:**  
Code should explicitly handle empty collections when calculating, filtering, or selecting values.

**Severity:** WARNING

### BAD

```python
average = sum(scores) / len(scores)
```

### GOOD

```python
average = 0 if not scores else sum(scores) / len(scores)
```

---

## ERR-021: Avoid null object references

**Description:**  
Objects that may be missing must be checked before use.

**Severity:** SERIOUS

### BAD

```csharp
var email = user.Email.ToLower();
```

### GOOD

```csharp
if (user is null || string.IsNullOrWhiteSpace(user.Email))
{
    throw new InvalidOperationException("Missing user email");
}

var email = user.Email.ToLowerInvariant();
```

---

## ERR-022: Specify timezone when handling datetime

**Description:**  
Datetime logic must use explicit timezone-aware values, especially for expiration, scheduling, billing, and audit logs.

**Severity:** WARNING

### BAD

```python
expires_at = datetime.now() + timedelta(hours=1)
```

```typescript
const expiresAt = new Date();
```

```csharp
var expiresAt = DateTime.Now.AddHours(1);
```

### GOOD

```python
expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
```

```typescript
const expiresAt = new Date(Date.now() + 60 * 60 * 1000);
```

```csharp
var expiresAt = DateTimeOffset.UtcNow.AddHours(1);
```

---

# AI Reviewer Checklist

Use this checklist for every commit review.

## Try/Catch

- [ ] No broad catch without logging.
- [ ] No empty catch block.
- [ ] No `console.log`, `print`, or `Console.WriteLine` as the only error handling.
- [ ] Expected async failures are caught and handled.

## Async Error Handling

- [ ] Promises are awaited or have `.catch()`.
- [ ] Fire-and-forget tasks have explicit error handling.
- [ ] No unhandled promise rejection risk.
- [ ] Concurrent updates handle race conditions where relevant.

## Input Validation

- [ ] Request body is validated before processing.
- [ ] Null or undefined values are checked before property access.
- [ ] Input type, range, and format are validated.
- [ ] Array/list access handles empty collections and invalid indexes.

## External Service Calls

- [ ] Third-party HTTP calls have timeout.
- [ ] Network errors are handled.
- [ ] Retry logic exists for transient errors where appropriate.
- [ ] Database connection/query errors are handled safely.

## Logging & Observability

- [ ] Production errors are logged.
- [ ] Logs include useful context such as request id, user id, resource id, or operation name.
- [ ] Proper logger is used instead of print or console logging.
- [ ] Errors include stable error code or error type.

## Edge Cases

- [ ] Division by zero is guarded.
- [ ] Empty lists or arrays are handled.
- [ ] Null object references are guarded.
- [ ] Datetime logic uses explicit timezone where needed.

## Review Decision

- [ ] SERIOUS issues are reported clearly.
- [ ] WARNING issues include recommended improvements.
- [ ] Severity was downgraded only when the task description provides a valid reason.
- [ ] Final review states whether the commit is safe to merge.
