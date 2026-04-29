# Code Style Review Rules
You are a senior engineer writing coding conventions for a Vietnamese software outsourcing company.
Context:
- Team size: 5-15 engineers per project
- Clients: Japan, United States, Australia
- Goal: readable, maintainable, reviewable production code
This file is read after `security.md` and `error-handling.md`.
Tech stack:
- Python / FastAPI
- TypeScript / Next.js 14 App Router
- C# / .NET 8 Clean Architecture
## Severity Definitions
| Severity | Meaning |
|---|---|
| WARNING | Should be fixed before merge when practical. |
| INFO | Recommended improvement. Does not block merge by itself. |
> Style issues must never override security or error-handling verdicts.
---
# 1. Naming Convention
## STYLE-001: Follow language naming conventions
**Description:**  
Use `camelCase` for JS/TS variables/functions, `snake_case` for Python variables/functions, and `PascalCase` for C# public methods/classes.
**Severity:** WARNING
### BAD
```typescript
const user_name = "John";
function get_user_profile() {}
```
```python
userName = "John"
def GetUserProfile(): pass
```
### GOOD
```typescript
const userName = "John";
function getUserProfile() {}
```
```python
user_name = "John"
def get_user_profile(): pass
```
---
## STYLE-002: Use PascalCase for classes and interfaces
**Description:**  
Classes and interfaces must use PascalCase.
**Severity:** WARNING
### BAD
```typescript
interface user_profile {}
class order_service {}
```
### GOOD
```typescript
interface UserProfile {}
class OrderService {}
```
---
## STYLE-003: Use UPPER_SNAKE_CASE for constants
**Description:**  
Constants should use UPPER_SNAKE_CASE.
**Severity:** INFO
### BAD
```typescript
const maxRetryCount = 3;
```
### GOOD
```typescript
const MAX_RETRY_COUNT = 3;
```
---
## STYLE-004: Boolean names must start with is, has, can, or should
**Description:**  
Boolean variables must clearly indicate true/false meaning.
**Severity:** WARNING
### BAD
```typescript
const active = user.status === "active";
```
### GOOD
```typescript
const isActive = user.status === "active";
```
---
## STYLE-005: Use meaningful names
**Description:**  
Avoid vague names such as `a`, `b`, `x`, `temp`, `data`, and `result`, unless the scope is very small and obvious.
**Severity:** WARNING
### BAD
```typescript
const data = await getData();
const result = data.filter((x) => x.active);
```
### GOOD
```typescript
const users = await getUsers();
const activeUsers = users.filter((user) => user.isActive);
```
---
## STYLE-006: Avoid unclear abbreviations
**Description:**  
Do not use abbreviations unless they are common: `id`, `url`, `api`, `dto`, `vm`.
**Severity:** INFO
### BAD
```typescript
const usrAddr = user.address;
```
### GOOD
```typescript
const userAddress = user.address;
```
---
# 2. Function Design
## STYLE-007: Keep functions short
**Description:**  
Functions longer than 50 lines are hard to review and should be split.
**Severity:** WARNING
### BAD
```typescript
async function createOrder() {
  // validate, price, inventory, payment, email, reporting...
}
```
### GOOD
```typescript
async function createOrder() {
  const request = validateOrderRequest();
  const order = await saveOrder(request);
  await chargePayment(order);
}
```
---
## STYLE-008: Keep one responsibility per function
**Description:**  
A function should do one clear thing. Avoid mixing validation, persistence, formatting, and external calls.
**Severity:** WARNING
### BAD
```python
def create_user(request):
    validate_email(request["email"])
    user = save_user(request)
    send_welcome_email(user)
    return format_response(user)
```
### GOOD
```python
def create_user(request: CreateUserRequest) -> UserResponse:
    validate_create_user_request(request)
    user = save_user(request)
    return to_user_response(user)
```
---
## STYLE-009: Replace magic numbers with constants or enums
**Description:**  
Numbers with business meaning must be named.
**Severity:** INFO
### BAD
```typescript
if (retryCount > 3) throw new Error("Too many retries");
```
### GOOD
```typescript
const MAX_RETRY_COUNT = 3;
if (retryCount > MAX_RETRY_COUNT) throw new Error("Too many retries");
```
---
## STYLE-010: Avoid too many parameters
**Description:**  
Functions with more than 4 parameters should usually use an object, DTO, or request model.
**Severity:** WARNING
### BAD
```typescript
function createUser(name: string, email: string, age: number, role: string, city: string) {}
```
### GOOD
```typescript
type CreateUserInput = { name: string; email: string; age: number; role: string; city: string };
function createUser(input: CreateUserInput) {}
```
---
## STYLE-011: Remove dead code
**Description:**  
Unused functions, variables, imports, and commented-out code should be removed.
**Severity:** WARNING
### BAD
```typescript
const unusedValue = calculateValue();
// await oldCreateOrder();
```
### GOOD
```typescript
await createOrder();
```
---
# 3. Comment & Documentation
## STYLE-012: Explain complex business logic with comments
**Description:**  
Complex domain rules should include comments explaining why the logic exists.
**Severity:** INFO
### BAD
```typescript
if (country === "JP" && total > 10000) fee = 0;
```
### GOOD
```typescript
// Contract rule JP-B2B-2024: free handling above 10,000 JPY.
if (country === "JP" && total > 10000) fee = 0;
```
---
## STYLE-013: Avoid comments that only repeat the code
**Description:**  
Comments should explain why, not obvious what.
**Severity:** INFO
### BAD
```typescript
// Increment count by 1
count += 1;
```
### GOOD
```typescript
// Used to decide whether account lockout is required.
failedLoginCount += 1;
```
---
## STYLE-014: TODO comments must include ticket or issue reference
**Description:**  
TODO comments without ownership or ticket references are hard to track.
**Severity:** INFO
### BAD
```typescript
// TODO: fix this later
```
### GOOD
```typescript
// TODO(PROJ-123): Replace temporary payment adapter.
```
---
## STYLE-015: Document public APIs and shared functions
**Description:**  
Public functions, exported modules, API handlers, and shared utilities should have JSDoc, docstring, or XML comments when behavior is not obvious.
**Severity:** INFO
### BAD
```typescript
export function calculatePenalty(daysLate: number): number {
  return daysLate * 5;
}
```
### GOOD
```typescript
/** Calculates late payment penalty based on the client contract. */
export function calculatePenalty(daysLate: number): number {
  return daysLate * DAILY_PENALTY_AMOUNT;
}
```
---
# 4. Code Structure
## STYLE-016: Organize imports
**Description:**  
Imports should be grouped and sorted consistently: standard/library imports, third-party imports, then internal imports.
**Severity:** INFO
### BAD
```typescript
import UserCard from "@/components/UserCard";
import fs from "fs";
import React from "react";
```
### GOOD
```typescript
import fs from "fs";
import React from "react";
import UserCard from "@/components/UserCard";
```
---
## STYLE-017: Split files longer than 300 lines
**Description:**  
Files longer than 300 lines should be reviewed for splitting into modules, components, services, or helpers.
**Severity:** WARNING
### BAD
```text
order-service.ts contains validation, pricing, payment, email, reporting, and 500 lines.
```
### GOOD
```text
order-service.ts
order-validation.ts
order-pricing.ts
payment-service.ts
```
---
## STYLE-018: Avoid circular dependencies
**Description:**  
Circular dependencies make code harder to test, maintain, and deploy.
**Severity:** WARNING
### BAD
```text
user-service.ts imports order-service.ts
order-service.ts imports user-service.ts
```
### GOOD
```text
user-service.ts imports shared/user-types.ts
order-service.ts imports shared/user-types.ts
```
---
## STYLE-019: Move hardcoded strings to constants or config
**Description:**  
Repeated business strings, route names, status values, and provider names should be constants, enums, or config.
**Severity:** INFO
### BAD
```typescript
if (order.status === "WAITING_FOR_PAYMENT") {}
```
### GOOD
```typescript
const ORDER_STATUS_WAITING_FOR_PAYMENT = "WAITING_FOR_PAYMENT";
```
---
# 5. TypeScript Specific Rules
## STYLE-020: Avoid `any`
**Description:**  
`any` disables type safety and should be flagged every time.
**Severity:** WARNING
### BAD
```typescript
function createUser(payload: any) {
  return payload.email;
}
```
### GOOD
```typescript
type CreateUserPayload = { email: string };
function createUser(payload: CreateUserPayload) {
  return payload.email;
}
```
---
## STYLE-021: Public functions should declare return type
**Description:**  
Exported functions and public utilities should have explicit return types.
**Severity:** INFO
### BAD
```typescript
export function getUserName(user: User) {
  return user.name;
}
```
### GOOD
```typescript
export function getUserName(user: User): string {
  return user.name;
}
```
---
## STYLE-022: Avoid unjustified type assertions
**Description:**  
Type assertions using `as` should be avoided unless there is validation or a clear reason.
**Severity:** WARNING
### BAD
```typescript
const user = payload as User;
```
### GOOD
```typescript
const user = userSchema.parse(payload);
```
---
## STYLE-023: Use interface or type consistently
**Description:**  
A project should consistently use either `interface` or `type` for object shapes unless there is a good reason.
**Severity:** INFO
### BAD
```typescript
interface User { id: string }
type Order = { id: string };
```
### GOOD
```typescript
type User = { id: string };
type Order = { id: string };
```
---
# 6. Python Specific Rules
## STYLE-024: Add type hints
**Description:**  
Python functions should include type hints for parameters and return values.
**Severity:** WARNING
### BAD
```python
def create_user(email, age):
    return {"email": email, "age": age}
```
### GOOD
```python
def create_user(email: str, age: int) -> dict:
    return {"email": email, "age": age}
```
---
## STYLE-025: Do not use mutable default arguments
**Description:**  
Mutable default arguments are shared across function calls and may create hidden bugs.
**Severity:** WARNING
### BAD
```python
def add_item(item: str, items: list[str] = []): pass
```
### GOOD
```python
def add_item(item: str, items: list[str] | None = None) -> list[str]: pass
```
---
## STYLE-026: Avoid wildcard imports
**Description:**  
Wildcard imports make dependencies unclear and may cause naming conflicts.
**Severity:** WARNING
### BAD
```python
from models import *
```
### GOOD
```python
from models import User, Order
```
---
# 7. C# Specific Rules
## STYLE-027: Use async/await correctly
**Description:**  
Do not block async code using `.Result`, `.Wait()`, or `GetAwaiter().GetResult()`.
**Severity:** WARNING
### BAD
```csharp
var user = userService.GetUserAsync(id).Result;
```
### GOOD
```csharp
var user = await userService.GetUserAsync(id);
```
---
## STYLE-028: Dispose IDisposable resources
**Description:**  
Objects implementing `IDisposable` or `IAsyncDisposable` must be disposed correctly.
**Severity:** WARNING
### BAD
```csharp
var stream = File.OpenRead(path);
Process(stream);
```
### GOOD
```csharp
using var stream = File.OpenRead(path);
Process(stream);
```
---
## STYLE-029: Use constants or enums instead of magic strings
**Description:**  
Business strings in C# should be constants, enums, or value objects.
**Severity:** INFO
### BAD
```csharp
if (order.Status == "Completed") SendReceipt(order);
```
### GOOD
```csharp
if (order.Status == OrderStatus.Completed) SendReceipt(order);
```
---
# AI Reviewer Checklist
## Naming
- [ ] JS/TS variables and functions use camelCase.
- [ ] Python variables and functions use snake_case.
- [ ] C# public methods/classes use PascalCase where appropriate.
- [ ] Classes and interfaces use PascalCase.
- [ ] Constants use UPPER_SNAKE_CASE.
- [ ] Boolean variables start with is, has, can, or should.
- [ ] Names are meaningful and not vague.
- [ ] Unclear abbreviations are avoided.
## Design, Comments, Structure
- [ ] Functions longer than 50 lines are reported.
- [ ] Functions generally have one responsibility.
- [ ] Magic numbers are replaced with constants or enums.
- [ ] Functions with more than 4 parameters use object/DTO/request model where appropriate.
- [ ] Dead code and unused declarations are removed.
- [ ] Complex business logic explains why.
- [ ] Obvious comments are avoided.
- [ ] TODO comments include ticket or issue reference.
- [ ] Public APIs/shared utilities have documentation when needed.
- [ ] Imports are grouped and sorted consistently.
- [ ] Files longer than 300 lines are reviewed for splitting.
- [ ] Circular dependencies are avoided.
- [ ] Repeated hardcoded strings are moved to constants, enums, or config.
## Language-Specific Rules
- [ ] TypeScript: `any` is not used unless clearly justified.
- [ ] TypeScript: public functions have explicit return types.
- [ ] TypeScript: type assertions using `as` are validated or justified.
- [ ] TypeScript: `interface` and `type` usage is consistent.
- [ ] Python: function parameters and return values have type hints.
- [ ] Python: no mutable default arguments are used.
- [ ] Python: no wildcard imports are used.
- [ ] C#: async code does not use `.Result`, `.Wait()`, or `GetAwaiter().GetResult()`.
- [ ] C#: disposable resources are disposed.
- [ ] C#: magic strings are replaced with constants or enums.
## Review Decision
- [ ] WARNING issues are reported with clear recommendations.
- [ ] INFO issues are reported as improvements, not blockers.
- [ ] Style issues do not override security or error-handling verdicts.
