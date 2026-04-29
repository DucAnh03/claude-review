# Security Review Rules

AI reviewer must read this file before reviewing code.

Scope:
- Python / FastAPI
- TypeScript / Next.js
- C# / .NET 8

Severity:
- BLOCKING: must fix before merge.
- SERIOUS: high risk, should fix before merge unless explicitly accepted.
- WARNING: should improve when applicable.

---

## 1. Secrets & Credentials

### SEC-001: Do not hardcode secrets

Severity: BLOCKING

Do not hardcode:
- API keys
- passwords
- tokens
- JWT secrets
- encryption keys
- private keys
- service credentials
- webhook secrets

Bad:

```python
OPENAI_API_KEY = "sk-live-abc123"
JWT_SECRET = "secret"
```

```ts
const stripeSecret = "sk_live_123";
const jwtSecret = "my-secret";
```

```csharp
var apiKey = "prod-api-key";
var password = "Admin@123";
```

Good:

```python
import os

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
```

```ts
const stripeSecret = process.env.STRIPE_SECRET_KEY;
if (!stripeSecret) throw new Error("Missing STRIPE_SECRET_KEY");
```

```csharp
var apiKey = builder.Configuration["ExternalServices:ApiKey"];
if (string.IsNullOrWhiteSpace(apiKey))
    throw new InvalidOperationException("Missing API key.");
```

---

### SEC-002: Do not commit real credentials in config files

Severity: BLOCKING

Committed config must not contain real production credentials.

Bad:

```env
DATABASE_URL=postgresql://admin:real-password@prod-db/app
JWT_SECRET=production-secret
```

```json
{
  "Database": {
    "Password": "real-password"
  }
}
```

Good:

```env
DATABASE_URL=
JWT_SECRET=
```

```env
# .env.example
DATABASE_URL=postgresql://user:password@host:5432/database
JWT_SECRET=replace-me
```

---

### SEC-003: Keep private keys and certificates out of code

Severity: BLOCKING

Private keys, certificates, signing keys, and service account files must not be embedded in source code.

Bad:

```python
PRIVATE_KEY = """
-----BEGIN PRIVATE KEY-----
...
-----END PRIVATE KEY-----
"""
```

```ts
const certificate = `-----BEGIN CERTIFICATE----- ...`;
```

```csharp
var privateKey = @"-----BEGIN RSA PRIVATE KEY----- ...";
```

Good:

```python
private_key = os.environ["PRIVATE_KEY"]
```

```ts
const privateKey = process.env.PRIVATE_KEY;
```

```csharp
var privateKey = builder.Configuration["Security:PrivateKey"];
```

---

### SEC-004: Do not hardcode credentials in connection strings

Severity: BLOCKING

Bad:

```python
DATABASE_URL = "postgresql://admin:password123@prod-db/app"
```

```ts
const cs = "Server=prod;User Id=sa;Password=Password123;";
```

```csharp
options.UseSqlServer("Server=prod;User Id=sa;Password=Password123;");
```

Good:

```python
DATABASE_URL = os.environ["DATABASE_URL"]
```

```ts
const cs = process.env.DATABASE_URL;
```

```csharp
options.UseSqlServer(builder.Configuration.GetConnectionString("DefaultConnection"));
```

---

## 2. Injection Attacks

### SEC-005: Use parameterized SQL

Severity: BLOCKING

Never build SQL by concatenating user input.

Bad:

```python
query = f"SELECT * FROM users WHERE email = '{email}'"
db.execute(query)
```

```ts
await db.query(`SELECT * FROM users WHERE email = '${email}'`);
```

```csharp
var sql = "SELECT * FROM Users WHERE Email = '" + email + "'";
db.Users.FromSqlRaw(sql);
```

Good:

```python
db.execute("SELECT * FROM users WHERE email = :email", {"email": email})
```

```ts
await db.query("SELECT * FROM users WHERE email = $1", [email]);
```

```csharp
db.Users.FromSqlInterpolated($"SELECT * FROM Users WHERE Email = {email}");
```

---

### SEC-006: Prevent command injection

Severity: BLOCKING

Avoid shell execution. If required, use argument arrays and strict allowlists.

Bad:

```python
subprocess.check_output(f"ping {host}", shell=True)
```

```ts
exec(`convert ${file} output.png`);
```

```csharp
Process.Start("cmd.exe", "/c " + userCommand);
```

Good:

```python
subprocess.check_output(["ping", "-c", "1", host])
```

```ts
spawn("convert", [safeInputPath, outputPath]);
```

```csharp
Process.Start(new ProcessStartInfo {
    FileName = "git",
    ArgumentList = { "status" }
});
```

---

### SEC-007: Escape or sanitize HTML

Severity: BLOCKING

User-provided content must not be rendered as raw HTML unless sanitized.

Bad:

```tsx
<div dangerouslySetInnerHTML={{ __html: content }} />
```

```python
return HTMLResponse(f"<h1>{name}</h1>")
```

```cshtml
@Html.Raw(Model.UserBio)
```

Good:

```tsx
const clean = DOMPurify.sanitize(content);
return <div dangerouslySetInnerHTML={{ __html: clean }} />;
```

```python
from html import escape
return HTMLResponse(f"<h1>{escape(name)}</h1>")
```

```cshtml
@Model.UserBio
```

---

### SEC-008: Prevent path traversal

Severity: BLOCKING

Do not read or write files using raw user paths.

Bad:

```python
return FileResponse(f"/app/uploads/{file}")
```

```ts
fs.readFileSync(`/var/uploads/${req.query.file}`);
```

```csharp
File.ReadAllBytes("uploads/" + fileName);
```

Good:

```python
BASE_DIR = Path("/app/uploads").resolve()
target = (BASE_DIR / file).resolve()
if not str(target).startswith(str(BASE_DIR)):
    raise ValueError("Invalid path")
```

```ts
const base = path.resolve("/var/uploads");
const target = path.resolve(base, String(file));
if (!target.startsWith(base)) throw new Error("Invalid path");
```

```csharp
var basePath = Path.GetFullPath("uploads");
var target = Path.GetFullPath(Path.Combine(basePath, fileName));
if (!target.StartsWith(basePath))
    throw new InvalidOperationException("Invalid path.");
```

---

## 3. Authentication & Authorization

### SEC-009: Protect sensitive endpoints

Severity: BLOCKING

Endpoints must require authentication when they access:
- user data
- admin data
- billing data
- internal tools
- write operations
- private files

Bad:

```python
@app.get("/admin/users")
def list_users():
    return user_service.get_all()
```

```ts
export async function GET() {
  return Response.json(await getAllUsers());
}
```

```csharp
app.MapGet("/admin/users", () => userService.GetAll());
```

Good:

```python
def list_users(user: User = Depends(require_admin_user)):
    return user_service.get_all()
```

```ts
const user = await requireAdminUser(req);
```

```csharp
app.MapGet("/admin/users", handler).RequireAuthorization("AdminOnly");
```

---

### SEC-010: Verify JWTs completely

Severity: BLOCKING

JWTs must verify:
- signature
- algorithm
- issuer
- audience
- expiration

Bad:

```python
jwt.decode(token, options={"verify_signature": False})
```

```ts
const payload = jwt.decode(token);
```

```csharp
new JwtSecurityTokenHandler().ReadJwtToken(token);
```

Good:

```python
jwt.decode(token, public_key, algorithms=["RS256"], audience="api", issuer=issuer)
```

```ts
jwt.verify(token, publicKey, {
  algorithms: ["RS256"],
  audience: "api",
  issuer,
});
```

```csharp
builder.Services.AddAuthentication().AddJwtBearer(options => {
    options.Authority = "https://auth.example.com";
    options.Audience = "api";
});
```

---

### SEC-011: Do not bypass authorization

Severity: BLOCKING

Do not remove, comment out, weaken, or bypass role checks.

Bad:

```python
# require_admin_user()
delete_user(user_id)
```

```ts
// TODO: enable later
// await requireRole(user, "admin");
```

```csharp
// [Authorize(Roles = "Admin")]
public IActionResult DeleteUser(int id) { ... }
```

Good:

```python
admin = Depends(require_admin_user)
```

```ts
await requireRole(user, "admin");
```

```csharp
[Authorize(Roles = "Admin")]
```

---

### SEC-012: Store passwords safely

Severity: BLOCKING

Passwords must never be stored as plaintext or weak hashes.

Bad:

```python
user.password = password
```

```ts
crypto.createHash("md5").update(password).digest("hex")
```

```csharp
MD5.HashData(Encoding.UTF8.GetBytes(password))
```

Good:

```python
pwd_context.hash(password)
```

```ts
await bcrypt.hash(password, 12);
```

```csharp
hasher.HashPassword(user, password);
```

---

## 4. Data Exposure

### SEC-013: Do not return sensitive fields

Severity: BLOCKING

API responses must not expose:
- passwords
- password hashes
- tokens
- API keys
- reset codes
- private internal IDs
- unnecessary PII

Bad:

```python
return user
```

```ts
return Response.json(user);
```

```csharp
return Ok(userEntity);
```

Good:

```python
return {"id": user.id, "name": user.name}
```

```ts
return Response.json({ id: user.id, name: user.name });
```

```csharp
return Ok(new UserResponseDto { Id = user.Id, Name = user.Name });
```

---

### SEC-014: Do not log sensitive data

Severity: SERIOUS

Logs must not contain:
- passwords
- tokens
- authorization headers
- session IDs
- credit cards
- private keys
- reset codes
- unnecessary PII

Bad:

```python
logger.info("Login request: %s", request.dict())
```

```ts
console.log(req.headers.authorization);
```

```csharp
_logger.LogInformation("Password: {Password}", password);
```

Good:

```python
logger.info("Login attempt user_id=%s", user.id)
```

```ts
logger.info("Payment request received", { userId, amount });
```

```csharp
_logger.LogInformation("Login attempt for user {UserId}", user.Id);
```

---

### SEC-015: Do not expose internal errors to clients

Severity: SERIOUS

Client-facing errors must be generic. Internal details belong in server logs.

Bad:

```python
return JSONResponse({"error": str(exc)}, status_code=500)
```

```ts
return Response.json({ error: String(error) }, { status: 500 });
```

```csharp
return BadRequest(ex.ToString());
```

Good:

```python
logger.exception("Unhandled exception")
return JSONResponse({"error": "Internal server error"}, status_code=500)
```

```ts
logger.error(error);
return Response.json({ error: "Internal server error" }, { status: 500 });
```

```csharp
_logger.LogError(ex, "Unhandled exception");
return StatusCode(500, new { error = "Internal server error" });
```

---

## 5. Dependencies & Configuration

### SEC-016: Use trusted dependencies

Severity: SERIOUS

New dependencies must be:
- necessary
- maintained
- trusted
- from known registries
- not typosquatted
- not suspiciously named

Flag dependencies when:
- package name looks like typosquatting
- package has unclear ownership
- package has very low usage and broad permissions
- install scripts are suspicious
- dependency handles auth, crypto, payments, or file access without justification
- dependency is added but unused

---

### SEC-017: Disable debug mode in production

Severity: BLOCKING

Production must not enable:
- debug mode
- developer exception pages
- verbose errors
- source maps exposing sensitive code
- unsafe diagnostics

Bad:

```python
app = FastAPI(debug=True)
```

```ts
productionBrowserSourceMaps: true
```

```csharp
if (app.Environment.IsProduction()) {
    app.UseDeveloperExceptionPage();
}
```

Good:

```python
app = FastAPI(debug=False)
```

```ts
productionBrowserSourceMaps: false
```

```csharp
if (app.Environment.IsDevelopment()) {
    app.UseDeveloperExceptionPage();
}
```

---

### SEC-018: Restrict CORS in production

Severity: SERIOUS

Production CORS must use approved origins.

Bad:

```python
allow_origins=["*"]
allow_credentials=True
```

```ts
"Access-Control-Allow-Origin": "*",
"Access-Control-Allow-Credentials": "true",
```

```csharp
policy.AllowAnyOrigin().AllowAnyHeader().AllowAnyMethod();
```

Good:

```python
allow_origins=["https://app.example.com"]
```

```ts
const allowedOrigins = new Set(["https://app.example.com"]);
```

```csharp
policy.WithOrigins("https://app.example.com").AllowCredentials();
```

---

## Final Review Checklist

Secrets:
- [ ] No hardcoded API keys, passwords, tokens, or secret keys.
- [ ] No real credentials in config files.
- [ ] No private keys or certificates in code.
- [ ] No credentials inside committed connection strings.
- [ ] Secret files are ignored by Git.
- [ ] Example configs use placeholders only.

Injection:
- [ ] SQL queries are parameterized or ORM-safe.
- [ ] No SQL string concatenation with user input.
- [ ] No shell execution with raw user input.
- [ ] Command execution uses argument arrays and allowlists.
- [ ] User HTML is escaped or sanitized.
- [ ] User file paths are normalized and restricted.

Auth:
- [ ] Sensitive endpoints require authentication.
- [ ] Privileged endpoints require authorization.
- [ ] JWTs verify signature, issuer, audience, and expiration.
- [ ] No commented-out or bypassed role checks.
- [ ] Passwords use strong hashing.
- [ ] No plaintext, MD5, SHA1, or weak password hashing.

Data exposure:
- [ ] Responses do not expose passwords, hashes, tokens, secrets, or reset codes.
- [ ] DTOs or schemas control returned fields.
- [ ] Logs do not contain sensitive data.
- [ ] Client errors do not expose internals.
- [ ] Sensitive values are masked when needed.

Dependencies and config:
- [ ] New dependencies are trusted and maintained.
- [ ] Suspicious or unused dependencies are flagged.
- [ ] Production debug mode is disabled.
- [ ] Developer exception pages are dev-only.
- [ ] Production CORS is restricted.
- [ ] Security config is environment-specific.

Merge decision:
- [ ] No BLOCKING issues found.
- [ ] SERIOUS issues are fixed or explicitly accepted.
- [ ] WARNING issues are documented.
- [ ] Final review states whether the commit is safe to merge.
