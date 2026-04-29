# TypeScript Review Skill Guide

You are a senior TypeScript engineer with 8 years of experience building large-scale production applications.

This file is loaded when the diff contains `.ts` or `.tsx` files.

Use this guide to review TypeScript quality, maintainability, correctness, and production readiness.

## Severity Definitions

| Severity | Meaning                                                   |
| -------- | --------------------------------------------------------- |
| SERIOUS  | High-risk TypeScript issue. Should be fixed before merge. |
| WARNING  | Should be improved before merge when practical.           |
| INFO     | Recommended improvement. Does not block merge by itself.  |

---

# 1. Type System

## TS-001: Choose `type` vs `interface` consistently

**When to apply:**  
Use `interface` for object shapes intended to be extended or implemented.  
Use `type` for unions, intersections, mapped types, utility types, and function aliases.  
Within one project, follow the existing convention unless there is a clear reason.

**Severity:** INFO

### BAD

```typescript
interface UserId = string;

type AdminUser extends User = {
  permissions: string[];
};
```

### GOOD

```typescript
type UserId = string;

interface AdminUser extends User {
  permissions: string[];
}

type ApiResult<T> =
  | { success: true; data: T }
  | { success: false; error: string };
```

---

## TS-002: Use generic constraints correctly

**When to apply:**  
Use generic constraints when a function needs specific fields or behavior from a generic type.

**Severity:** WARNING

### BAD

```typescript
function getId<T>(item: T): string {
  return item.id;
}
```

### GOOD

```typescript
function getId<T extends { id: string }>(item: T): string {
  return item.id;
}
```

---

## TS-003: Use utility types intentionally

**When to apply:**  
Use utility types to express transformations clearly:

- `Partial<T>`: some fields are optional
- `Pick<T, K>`: only selected fields are needed
- `Omit<T, K>`: remove fields from a type
- `Record<K, V>`: key-value map with known key/value types

**Severity:** INFO

### BAD

```typescript
type UpdateUserInput = {
  name?: string;
  email?: string;
  role?: string;
};

type PublicUser = {
  id: string;
  name: string;
  email: string;
};
```

### GOOD

```typescript
type UpdateUserInput = Partial<Pick<User, "name" | "email" | "role">>;

type PublicUser = Omit<User, "passwordHash" | "accessToken">;

type UserRoleMap = Record<string, "admin" | "member" | "guest">;
```

---

## TS-004: Use discriminated unions for states and variants

**When to apply:**  
Use discriminated unions when data can be one of several known shapes.

**Severity:** WARNING

### BAD

```typescript
type PaymentState = {
  status: string;
  transactionId?: string;
  errorMessage?: string;
};
```

### GOOD

```typescript
type PaymentState =
  | { status: "pending" }
  | { status: "paid"; transactionId: string }
  | { status: "failed"; errorMessage: string };

function renderPayment(state: PaymentState): string {
  switch (state.status) {
    case "pending":
      return "Payment pending";
    case "paid":
      return `Paid: ${state.transactionId}`;
    case "failed":
      return state.errorMessage;
  }
}
```

---

## TS-005: Avoid `any`

**When to apply:**  
Flag every `any` unless the code clearly explains why it is unavoidable.

**Severity:** WARNING

### BAD

```typescript
function parseUser(payload: any) {
  return payload.email.toLowerCase();
}
```

### GOOD

```typescript
type UserPayload = {
  email: string;
};

function parseUser(payload: UserPayload): string {
  return payload.email.toLowerCase();
}
```

---

## TS-006: Guard `unknown` before use

**When to apply:**  
Use `unknown` for untrusted input, but always narrow it before reading properties.

**Severity:** SERIOUS

### BAD

```typescript
function handleError(error: unknown) {
  logger.error(error.message);
}
```

### GOOD

```typescript
function handleError(error: unknown) {
  if (error instanceof Error) {
    logger.error(error.message);
    return;
  }

  logger.error("Unknown error");
}
```

---

## TS-007: Avoid unjustified type assertions

**When to apply:**  
Avoid `as SomeType` when the code has not validated the actual runtime shape.

**Severity:** WARNING

### BAD

```typescript
const user = JSON.parse(body) as User;
return user.email.toLowerCase();
```

### GOOD

```typescript
const parsed = userSchema.parse(JSON.parse(body));
return parsed.email.toLowerCase();
```

---

## TS-008: Prefer optional chaining over unsafe non-null assertion

**When to apply:**  
Use optional chaining when a value may be null or undefined. Avoid `!` unless the value is guaranteed by framework behavior or prior validation.

**Severity:** WARNING

### BAD

```typescript
const city = user.profile!.address!.city;
```

### GOOD

```typescript
const city = user.profile?.address?.city;

if (!city) {
  throw new Error("Missing city");
}
```

---

# 2. Functions & Classes

## TS-009: Separate pure functions from side effects

**When to apply:**  
Pure functions should not mutate input, call external services, access global state, or write logs. Side effects should be explicit.

**Severity:** INFO

### BAD

```typescript
function calculateTotal(order: Order): number {
  logger.info("Calculating total");
  order.total = order.items.reduce((sum, item) => sum + item.price, 0);
  return order.total;
}
```

### GOOD

```typescript
function calculateTotal(items: OrderItem[]): number {
  return items.reduce((sum, item) => sum + item.price, 0);
}

function updateOrderTotal(order: Order): Order {
  return { ...order, total: calculateTotal(order.items) };
}
```

---

## TS-010: Use function overloading only when signatures are meaningfully different

**When to apply:**  
Use overloads when the return type depends on the input type. Avoid overloads for simple optional parameters.

**Severity:** INFO

### BAD

```typescript
function findUser(id?: string): User | User[] {
  if (id) return getUser(id);
  return getUsers();
}
```

### GOOD

```typescript
function findUser(id: string): User;
function findUser(): User[];
function findUser(id?: string): User | User[] {
  return id ? getUser(id) : getUsers();
}
```

---

## TS-011: Use access modifiers intentionally

**When to apply:**  
Use `private` for internal implementation, `protected` for subclass extension points, and `public` for external API.

**Severity:** INFO

### BAD

```typescript
class PaymentService {
  apiKey: string;

  buildHeaders() {
    return { Authorization: `Bearer ${this.apiKey}` };
  }
}
```

### GOOD

```typescript
class PaymentService {
  public constructor(private readonly apiKey: string) {}

  private buildHeaders(): Record<string, string> {
    return { Authorization: `Bearer ${this.apiKey}` };
  }
}
```

---

## TS-012: Choose abstract class vs interface correctly

**When to apply:**  
Use `interface` for contracts without implementation.  
Use `abstract class` when shared behavior or protected helpers are required.

**Severity:** INFO

### BAD

```typescript
abstract class UserRepository {
  abstract findById(id: string): Promise<User | null>;
}
```

### GOOD

```typescript
interface UserRepository {
  findById(id: string): Promise<User | null>;
}

abstract class BaseRepository {
  protected buildLimit(limit: number): number {
    return Math.min(limit, 100);
  }

  abstract findMany(limit: number): Promise<unknown[]>;
}
```

---

## TS-013: Use decorator pattern for cross-cutting behavior

**When to apply:**  
Use decorator pattern when adding behavior such as logging, caching, metrics, or retry without changing the core implementation.

**Severity:** INFO

### BAD

```typescript
class UserService {
  async getUser(id: string): Promise<User> {
    logger.info({ id }, "Getting user");
    const user = await this.repository.findById(id);
    metrics.increment("user.get");
    return user;
  }
}
```

### GOOD

```typescript
class UserServiceWithMetrics implements UserService {
  constructor(private readonly inner: UserService) {}

  async getUser(id: string): Promise<User> {
    logger.info({ id }, "Getting user");
    const user = await this.inner.getUser(id);
    metrics.increment("user.get");
    return user;
  }
}
```

---

# 3. Async Patterns

## TS-014: Prefer async/await for readable async flow

**When to apply:**  
Use `async/await` for multi-step async logic. Promise chains are acceptable for short transformations.

**Severity:** INFO

### BAD

```typescript
return getUser(id)
  .then((user) => getOrders(user.id))
  .then((orders) => buildResponse(orders))
  .catch((error) => handleError(error));
```

### GOOD

```typescript
try {
  const user = await getUser(id);
  const orders = await getOrders(user.id);
  return buildResponse(orders);
} catch (error) {
  return handleError(error);
}
```

---

## TS-015: Choose `Promise.all` vs `Promise.allSettled` correctly

**When to apply:**  
Use `Promise.all` when all operations must succeed.  
Use `Promise.allSettled` when partial success is acceptable.

**Severity:** WARNING

### BAD

```typescript
const results = await Promise.all([
  sendEmail(user),
  sendSlackMessage(user),
  sendSms(user),
]);
```

### GOOD

```typescript
const results = await Promise.allSettled([
  sendEmail(user),
  sendSlackMessage(user),
  sendSms(user),
]);

const failedTasks = results.filter((result) => result.status === "rejected");
```

---

## TS-016: Propagate async errors intentionally

**When to apply:**  
Async functions should either handle errors locally or let them bubble up with context. Do not swallow errors.

**Severity:** SERIOUS

### BAD

```typescript
async function syncUser(id: string): Promise<void> {
  try {
    await externalSync(id);
  } catch (error) {
    console.log(error);
  }
}
```

### GOOD

```typescript
async function syncUser(id: string): Promise<void> {
  try {
    await externalSync(id);
  } catch (error) {
    logger.error({ error, id }, "User sync failed");
    throw new SyncUserError(id);
  }
}
```

---

## TS-017: Use AbortController for cancellable requests

**When to apply:**  
Use `AbortController` for external requests, search requests, long-running client actions, or route-dependent fetches.

**Severity:** WARNING

### BAD

```typescript
const response = await fetch(url);
return response.json();
```

### GOOD

```typescript
const controller = new AbortController();
const timeout = setTimeout(() => controller.abort(), 10000);

try {
  const response = await fetch(url, { signal: controller.signal });
  return await response.json();
} finally {
  clearTimeout(timeout);
}
```

---

# 4. Module & Import

## TS-018: Use barrel exports carefully

**When to apply:**  
Use `index.ts` for stable public module APIs. Avoid large barrel files that re-export everything and create circular dependencies.

**Severity:** INFO

### BAD

```typescript
// index.ts
export * from "./user-service";
export * from "./order-service";
export * from "./payment-service";
export * from "./internal/debug-helper";
```

### GOOD

```typescript
// index.ts
export { UserService } from "./user-service";
export type { User } from "./user-types";
```

---

## TS-019: Detect and avoid circular dependencies

**When to apply:**  
Flag imports where module A imports B and B imports A, directly or indirectly.

**Severity:** WARNING

### BAD

```typescript
// user-service.ts
import { createOrder } from "./order-service";

// order-service.ts
import { getUser } from "./user-service";
```

### GOOD

```typescript
// user-service.ts
import type { Order } from "./order-types";

// order-service.ts
import type { User } from "./user-types";
```

---

## TS-020: Prefer path alias for deep imports

**When to apply:**  
Use configured aliases for deep cross-module imports. Relative imports are fine for nearby files.

**Severity:** INFO

### BAD

```typescript
import { Button } from "../../../../components/ui/button";
```

### GOOD

```typescript
import { Button } from "@/components/ui/button";
```

---

## TS-021: Use tree-shaking friendly exports

**When to apply:**  
Prefer named exports for shared modules. Avoid exporting large objects that force importing unnecessary code.

**Severity:** INFO

### BAD

```typescript
export default {
  UserService,
  OrderService,
  PaymentService,
};
```

### GOOD

```typescript
export { UserService } from "./user-service";
export { OrderService } from "./order-service";
export { PaymentService } from "./payment-service";
```

---

# 5. Performance Patterns

## TS-022: Avoid unnecessary re-computation

**When to apply:**  
Avoid repeated expensive calculations inside loops, React render paths, or frequently called functions.

**Severity:** WARNING

### BAD

```typescript
const visibleUsers = users.filter((user) => expensiveCheck(user));
const activeVisibleUsers = visibleUsers.filter((user) => expensiveCheck(user));
```

### GOOD

```typescript
const checkedUsers = users.map((user) => ({
  user,
  isVisible: expensiveCheck(user),
}));

const visibleUsers = checkedUsers.filter((item) => item.isVisible);
```

---

## TS-023: Use `import type` for type-only imports

**When to apply:**  
Use `import type` when importing only TypeScript types. This helps avoid unnecessary runtime dependencies and supports cleaner bundling.

**Severity:** INFO

### BAD

```typescript
import { User } from "@/types/user";
```

### GOOD

```typescript
import type { User } from "@/types/user";
```

---

## TS-024: Use const assertion to narrow literal types

**When to apply:**  
Use `as const` for fixed configuration values, route names, status lists, and literal maps.

**Severity:** INFO

### BAD

```typescript
const ROLES = ["admin", "member", "guest"];

function hasRole(role: string) {
  return ROLES.includes(role);
}
```

### GOOD

```typescript
const ROLES = ["admin", "member", "guest"] as const;

type Role = (typeof ROLES)[number];

function hasRole(role: string): role is Role {
  return ROLES.includes(role as Role);
}
```

---

# Quick Reviewer Checklist

## Type System

- [ ] `type` and `interface` are used consistently and appropriately.
- [ ] Generic constraints are used when generic values require specific fields.
- [ ] Utility types are used intentionally, not to hide unclear models.
- [ ] Discriminated unions are used for known variants or state machines.
- [ ] `any` is avoided or clearly justified.
- [ ] `unknown` is guarded before use.
- [ ] Type assertions are validated or justified.
- [ ] Optional chaining is preferred over unsafe non-null assertion.

## Functions & Classes

- [ ] Pure functions do not mutate inputs or perform side effects.
- [ ] Side effects are explicit and isolated.
- [ ] Function overloads are used only when signatures are meaningfully different.
- [ ] Access modifiers are intentional.
- [ ] Interface vs abstract class choice is appropriate.
- [ ] Decorator pattern is considered for cross-cutting behavior.

## Async Patterns

- [ ] `async/await` is preferred for multi-step async logic.
- [ ] `Promise.all` is used when all tasks must succeed.
- [ ] `Promise.allSettled` is used when partial success is acceptable.
- [ ] Async errors are handled or propagated with context.
- [ ] `AbortController` is used for cancellable or timeout-sensitive requests.

## Module & Import

- [ ] Barrel exports are not too broad.
- [ ] Circular dependencies are avoided.
- [ ] Path aliases are used for deep imports when configured.
- [ ] Named exports are preferred for tree-shaking.
- [ ] Type-only imports use `import type`.

## Performance

- [ ] Expensive calculations are not repeated unnecessarily.
- [ ] Type-only dependencies are not imported at runtime.
- [ ] Fixed literal values use `as const` where useful.

## Review Decision

- [ ] SERIOUS issues are clearly reported.
- [ ] WARNING issues include practical refactor suggestions.
- [ ] INFO issues are presented as improvements, not blockers.
