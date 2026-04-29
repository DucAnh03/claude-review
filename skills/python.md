# Python / FastAPI Review Skill Guide

You are a senior Python engineer specialized in FastAPI, data processing, and high-traffic production APIs.

This file is loaded when the diff contains `.py` files.

Use this guide to review Pythonic code, type hints, FastAPI design, async correctness, error handling, and performance.

## Severity Definitions

| Severity | Meaning                                                  |
| -------- | -------------------------------------------------------- |
| SERIOUS  | High-risk issue. Should be fixed before merge.           |
| WARNING  | Should be improved before merge when practical.          |
| INFO     | Recommended improvement. Does not block merge by itself. |

---

# 1. Pythonic Code

## PY-001: Use list comprehensions for simple transformations

**When to apply:**  
Use list comprehensions for simple map/filter transformations. Use normal `for` loops when the logic has multiple steps, side effects, error handling, or readability concerns.

**Severity:** INFO

### BAD

```python
names = []

for user in users:
    names.append(user.name)
```

### GOOD

```python
names = [user.name for user in users]
```

```python
active_users = []

for user in users:
    if not user.is_active:
        continue

    logger.info("Processing active user", extra={"user_id": user.id})
    active_users.append(user)
```

---

## PY-002: Use generators for large data streams

**When to apply:**  
Use generators when processing large files, large query results, or streaming data to avoid loading everything into memory.

**Severity:** WARNING

### BAD

```python
def read_lines(path: str) -> list[str]:
    return Path(path).read_text().splitlines()
```

### GOOD

```python
def read_lines(path: str) -> Iterator[str]:
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            yield line.rstrip("\n")
```

---

## PY-003: Use context managers for resource management

**When to apply:**  
Use `with` for files, locks, temporary directories, DB sessions, and network resources that must be closed.

**Severity:** WARNING

### BAD

```python
file = open("report.txt", "w")
file.write("done")
file.close()
```

### GOOD

```python
with open("report.txt", "w", encoding="utf-8") as file:
    file.write("done")
```

---

## PY-004: Use unpacking, f-strings, and walrus operator carefully

**When to apply:**  
Use these features when they improve readability. Avoid clever one-liners that make business logic harder to understand.

**Severity:** INFO

### BAD

```python
message = "User " + str(user.id) + " created order " + str(order.id)
```

```python
if (value := complex_function(a, b, c, d)) and value.is_valid() and value.owner.id == user.id:
    process(value)
```

### GOOD

```python
message = f"User {user.id} created order {order.id}"
```

```python
value = complex_function(a, b, c, d)

if value and value.is_valid() and value.owner.id == user.id:
    process(value)
```

---

## PY-005: Do not use mutable default arguments

**When to apply:**  
Default list, dict, or set values are shared across function calls and can create hidden bugs.

**Severity:** SERIOUS

### BAD

```python
def add_item(item: str, items: list[str] = []) -> list[str]:
    items.append(item)
    return items
```

### GOOD

```python
def add_item(item: str, items: list[str] | None = None) -> list[str]:
    if items is None:
        items = []

    items.append(item)
    return items
```

---

## PY-006: Avoid bare except

**When to apply:**  
Never use bare `except:`. Catch specific exceptions or at least `Exception`, and log properly.

**Severity:** SERIOUS

### BAD

```python
try:
    process_order(order_id)
except:
    return None
```

### GOOD

```python
try:
    process_order(order_id)
except OrderProcessingError:
    logger.exception("Failed to process order", extra={"order_id": order_id})
    raise
```

---

## PY-007: Avoid wildcard imports

**When to apply:**  
Wildcard imports make dependencies unclear and can cause naming conflicts.

**Severity:** WARNING

### BAD

```python
from models import *
```

### GOOD

```python
from models import Order, User
```

---

# 2. Type Hints

## PY-008: Require function parameter and return type hints

**When to apply:**  
Public functions, service functions, API handlers, and shared utilities must include type hints.

**Severity:** WARNING

### BAD

```python
def create_user(email, age):
    return {"email": email, "age": age}
```

### GOOD

```python
def create_user(email: str, age: int) -> dict[str, str | int]:
    return {"email": email, "age": age}
```

---

## PY-009: Use Optional, Union, and `|` correctly

**When to apply:**  
In Python 3.10+, prefer `T | None` and `A | B` for simple unions. Use `Optional[T]` only if the project convention still uses it.

**Severity:** INFO

### BAD

```python
def get_user(id: str) -> User:
    return None
```

### GOOD

```python
def get_user(id: str) -> User | None:
    return repository.find_by_id(id)
```

```python
def parse_id(value: str | int) -> int:
    return int(value)
```

---

## PY-010: Choose TypedDict, dataclass, or Pydantic model correctly

**When to apply:**  
Use:

- `TypedDict` for typed dictionary shapes without runtime validation
- `dataclass` for internal domain/value objects
- Pydantic model for API request/response validation and serialization

**Severity:** INFO

### BAD

```python
def create_user(payload: dict) -> dict:
    return {"email": payload["email"]}
```

### GOOD

```python
class CreateUserRequest(BaseModel):
    email: EmailStr
    age: int = Field(ge=18)


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str


class UserRow(TypedDict):
    id: str
    email: str
```

---

## PY-011: Use generic types for reusable containers and services

**When to apply:**  
Use generics when a function or class should preserve the input/output type relationship.

**Severity:** INFO

### BAD

```python
def first(items: list) -> object:
    return items[0]
```

### GOOD

```python
T = TypeVar("T")

def first(items: list[T]) -> T:
    return items[0]
```

---

## PY-012: Avoid Any unless clearly justified

**When to apply:**  
`Any` disables type checking. Allow it only at integration boundaries or when a comment explains why.

**Severity:** WARNING

### BAD

```python
def parse_payload(payload: Any) -> Any:
    return payload["email"]
```

### GOOD

```python
class Payload(BaseModel):
    email: EmailStr

def parse_payload(payload: Payload) -> str:
    return payload.email
```

---

# 3. FastAPI Specific

## PY-013: Use Pydantic models for request and response

**When to apply:**  
Do not accept raw `dict` for request bodies in FastAPI endpoints. Use Pydantic models for validation and documentation.

**Severity:** SERIOUS

### BAD

```python
@app.post("/users")
def create_user(payload: dict):
    return user_service.create(payload)
```

### GOOD

```python
class CreateUserRequest(BaseModel):
    email: EmailStr
    name: str

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    name: str

@app.post("/users", response_model=UserResponse)
def create_user(payload: CreateUserRequest) -> UserResponse:
    return user_service.create(payload)
```

---

## PY-014: Use Dependency Injection for shared request dependencies

**When to apply:**  
Use `Depends` for authentication, DB sessions, tenant resolution, permissions, and shared request-scoped services.

**Severity:** WARNING

### BAD

```python
@app.get("/me")
def me():
    token = request.headers["Authorization"]
    user = decode_token(token)
    return user
```

### GOOD

```python
@app.get("/me")
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)
```

---

## PY-015: Organize routers with prefix and tags

**When to apply:**  
Large FastAPI apps should organize endpoints by domain using `APIRouter`.

**Severity:** INFO

### BAD

```python
@app.get("/users")
def list_users(): ...

@app.post("/users")
def create_user(): ...
```

### GOOD

```python
router = APIRouter(prefix="/users", tags=["Users"])

@router.get("")
def list_users() -> list[UserResponse]: ...

@router.post("")
def create_user(payload: CreateUserRequest) -> UserResponse: ...
```

---

## PY-016: Choose BackgroundTasks vs Celery correctly

**When to apply:**  
Use FastAPI `BackgroundTasks` for short best-effort work. Use Celery/RQ/queue workers for long-running, retryable, scheduled, or critical jobs.

**Severity:** WARNING

### BAD

```python
@app.post("/reports")
def create_report(payload: ReportRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(generate_large_report, payload)
    return {"status": "started"}
```

### GOOD

```python
@app.post("/reports")
def create_report(payload: ReportRequest) -> JobResponse:
    job = report_queue.enqueue("generate_report", payload.model_dump())
    return JobResponse(job_id=job.id, status="queued")
```

```python
@app.post("/emails")
def send_email(payload: EmailRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(send_confirmation_email, payload.email)
    return {"status": "accepted"}
```

---

## PY-017: Use HTTPException with correct status codes

**When to apply:**  
Raise `HTTPException` at API boundaries for expected client-facing errors.

**Severity:** WARNING

### BAD

```python
if user is None:
    raise Exception("User not found")
```

### GOOD

```python
if user is None:
    raise HTTPException(status_code=404, detail="User not found")
```

---

## PY-018: Use lifespan instead of deprecated on_event

**When to apply:**  
For FastAPI startup/shutdown initialization, prefer lifespan context manager over deprecated `@app.on_event`.

**Severity:** INFO

### BAD

```python
@app.on_event("startup")
async def startup():
    await connect_db()
```

### GOOD

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()

app = FastAPI(lifespan=lifespan)
```

---

## PY-019: Use response_model to filter output fields

**When to apply:**  
Always use response models to avoid leaking internal fields such as password hashes, tokens, or private metadata.

**Severity:** SERIOUS

### BAD

```python
@app.get("/users/{user_id}")
def get_user(user_id: str):
    return user_repository.get(user_id)
```

### GOOD

```python
@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: str) -> User:
    return user_repository.get(user_id)
```

---

# 4. Async Python

## PY-020: Choose async def vs def correctly in FastAPI

**When to apply:**  
Use `async def` when using non-blocking async libraries. Use normal `def` for CPU-bound or blocking sync code so FastAPI can run it in a threadpool.

**Severity:** WARNING

### BAD

```python
@app.get("/external")
async def external():
    response = requests.get("https://api.example.com")
    return response.json()
```

### GOOD

```python
@app.get("/external")
async def external():
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get("https://api.example.com")
        return response.json()
```

```python
@app.get("/legacy")
def legacy():
    response = requests.get("https://api.example.com", timeout=10)
    return response.json()
```

---

## PY-021: Use asyncio.gather for independent parallel calls

**When to apply:**  
Use `asyncio.gather` when multiple async operations are independent and can run concurrently.

**Severity:** INFO

### BAD

```python
user = await get_user(user_id)
orders = await get_orders(user_id)
notifications = await get_notifications(user_id)
```

### GOOD

```python
user, orders, notifications = await asyncio.gather(
    get_user(user_id),
    get_orders(user_id),
    get_notifications(user_id),
)
```

---

## PY-022: Do not run blocking calls in async context

**When to apply:**  
Avoid sync file I/O, `requests`, `time.sleep`, CPU-heavy loops, or blocking DB drivers inside `async def`.

**Severity:** SERIOUS

### BAD

```python
async def sync_data():
    time.sleep(5)
    response = requests.get("https://api.example.com")
    return response.json()
```

### GOOD

```python
async def sync_data():
    await asyncio.sleep(5)

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get("https://api.example.com")
        return response.json()
```

---

## PY-023: Use async database drivers in async paths

**When to apply:**  
Async endpoints should use async database clients such as `asyncpg`, `aiomysql`, SQLAlchemy async, or equivalent.

**Severity:** WARNING

### BAD

```python
@app.get("/users")
async def list_users():
    return sync_session.query(User).all()
```

### GOOD

```python
@app.get("/users")
async def list_users(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User))
    return result.scalars().all()
```

---

# 5. Error Handling

## PY-024: Use custom exception hierarchy

**When to apply:**  
Domain and service layers should raise meaningful custom exceptions instead of generic `Exception`.

**Severity:** WARNING

### BAD

```python
raise Exception("Payment failed")
```

### GOOD

```python
class AppError(Exception):
    pass

class PaymentError(AppError):
    pass

raise PaymentError("Payment provider rejected the transaction")
```

---

## PY-025: Use HTTPException only at API boundaries

**When to apply:**  
Service/domain code should raise domain exceptions. API route or exception handlers should convert them to HTTP responses.

**Severity:** INFO

### BAD

```python
def get_user_or_fail(user_id: str) -> User:
    user = repository.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

### GOOD

```python
def get_user_or_fail(user_id: str) -> User:
    user = repository.get(user_id)
    if user is None:
        raise UserNotFoundError(user_id)
    return user


@app.exception_handler(UserNotFoundError)
async def user_not_found_handler(request: Request, exc: UserNotFoundError):
    return JSONResponse(status_code=404, content={"error": {"code": "USER_NOT_FOUND"}})
```

---

## PY-026: Log exceptions with traceback

**When to apply:**  
When catching exceptions, use `logger.exception()` or `logger.error(..., exc_info=True)` to preserve traceback.

**Severity:** WARNING

### BAD

```python
try:
    process_order(order_id)
except OrderError as exc:
    logger.error(f"Order failed: {exc}")
    raise
```

### GOOD

```python
try:
    process_order(order_id)
except OrderError:
    logger.exception("Order processing failed", extra={"order_id": order_id})
    raise
```

---

## PY-027: Keep validation error format consistent

**When to apply:**  
API validation and domain errors should return a consistent error response shape.

**Severity:** INFO

### BAD

```python
return {"message": "Invalid input"}
return {"error": "User not found"}
```

### GOOD

```python
return {
    "error": {
        "code": "INVALID_INPUT",
        "message": "Invalid request body",
        "details": errors,
    }
}
```

---

# 6. Performance

## PY-028: Avoid N+1 database queries

**When to apply:**  
Do not query related data inside loops when batch loading, joins, eager loading, or prefetching can be used.

**Severity:** SERIOUS

### BAD

```python
orders = session.query(Order).all()

for order in orders:
    order.customer = session.query(Customer).get(order.customer_id)
```

### GOOD

```python
orders = (
    session.query(Order)
    .options(selectinload(Order.customer))
    .all()
)
```

---

## PY-029: Use cache for expensive stable computations or reads

**When to apply:**  
Use `functools.lru_cache` for local deterministic config-style computations. Use Redis or shared cache for cross-process data.

**Severity:** INFO

### BAD

```python
def get_country_codes() -> list[str]:
    return load_country_codes_from_disk()
```

### GOOD

```python
@lru_cache(maxsize=1)
def get_country_codes() -> tuple[str, ...]:
    return tuple(load_country_codes_from_disk())
```

```python
cached_user = await redis.get(f"user:{user_id}")
```

---

## PY-030: Avoid unnecessary repeated Pydantic validation

**When to apply:**  
Pydantic validation is useful at boundaries, but avoid repeatedly validating already validated internal data in hot paths.

**Severity:** WARNING

### BAD

```python
for item in items:
    validated = ItemModel.model_validate(item)
    process_item(validated)
```

### GOOD

```python
validated_items = ItemsRequest.model_validate({"items": items}).items

for item in validated_items:
    process_item(item)
```

---

# Quick Reviewer Checklist

## Pythonic Code

- [ ] List comprehensions are used for simple transformations.
- [ ] Normal loops are used when logic is complex or has side effects.
- [ ] Generators are used for large streams where memory matters.
- [ ] Context managers are used for files, locks, sessions, and resources.
- [ ] f-strings, unpacking, and walrus operator improve readability.
- [ ] No mutable default arguments.
- [ ] No bare `except`.
- [ ] No wildcard imports.

## Type Hints

- [ ] Function parameters have type hints.
- [ ] Function return values have type hints.
- [ ] `T | None` or `Optional[T]` is used correctly.
- [ ] `TypedDict`, `dataclass`, and Pydantic models are chosen appropriately.
- [ ] Generics preserve input/output type relationships where useful.
- [ ] `Any` is avoided or clearly justified.

## FastAPI

- [ ] Request bodies use Pydantic models, not raw `dict`.
- [ ] Response models are used to filter output fields.
- [ ] Shared request concerns use `Depends`.
- [ ] Routers are organized with prefix and tags.
- [ ] BackgroundTasks are only used for short best-effort tasks.
- [ ] Queue workers are used for long, retryable, or critical jobs.
- [ ] `HTTPException` uses correct status codes.
- [ ] Lifespan is used instead of deprecated startup/shutdown events.

## Async Python

- [ ] `async def` is used only with non-blocking async libraries.
- [ ] Blocking calls are not used inside async functions.
- [ ] Independent async calls use `asyncio.gather` where useful.
- [ ] Async endpoints use async database drivers or safe sync isolation.

## Error Handling

- [ ] Domain/service layers use custom exceptions.
- [ ] `HTTPException` is mostly kept at API boundaries.
- [ ] Exceptions are logged with traceback.
- [ ] Validation errors follow a consistent response format.

## Performance

- [ ] No N+1 database queries.
- [ ] Cache is used for expensive stable reads or computations.
- [ ] Pydantic validation is not repeated unnecessarily in hot paths.

## Review Decision

- [ ] SERIOUS issues are reported clearly.
- [ ] WARNING issues include practical refactor suggestions.
- [ ] INFO issues are presented as improvements, not blockers.
