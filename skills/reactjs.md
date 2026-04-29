# React / Next.js Review Skill Guide

You are a senior React engineer specialized in Next.js 14 App Router.
You have shipped multiple production applications with teams of 5-20 engineers.

This file is loaded when the diff contains `.tsx`, `.jsx`, or React component files.

Use this guide to review component quality, hooks usage, state management, Next.js App Router patterns, performance, and accessibility.

## Severity Definitions

| Severity | Meaning                                                  |
| -------- | -------------------------------------------------------- |
| SERIOUS  | High-risk issue. Should be fixed before merge.           |
| WARNING  | Should be improved before merge when practical.          |
| INFO     | Recommended improvement. Does not block merge by itself. |

---

# 1. Component Design

## REACT-001: Prefer Server Components by default

**When to apply:**  
In Next.js 14 App Router, components should be Server Components by default. Use Client Components only when the component needs browser-only behavior such as state, effects, event handlers, refs, or browser APIs.

**Severity:** WARNING

### BAD

```tsx
"use client";

export default async function ProductList() {
  const products = await getProducts();

  return (
    <ul>
      {products.map((product) => (
        <li key={product.id}>{product.name}</li>
      ))}
    </ul>
  );
}
```

### GOOD

```tsx
export default async function ProductList() {
  const products = await getProducts();

  return (
    <ul>
      {products.map((product) => (
        <li key={product.id}>{product.name}</li>
      ))}
    </ul>
  );
}
```

---

## REACT-002: Add `"use client"` only when necessary

**When to apply:**  
Add `"use client"` only for components that use hooks, event handlers, browser APIs, or client-side interactivity.

**Severity:** WARNING

### BAD

```tsx
"use client";

export function StaticHeader() {
  return <h1>Welcome</h1>;
}
```

### GOOD

```tsx
export function StaticHeader() {
  return <h1>Welcome</h1>;
}
```

```tsx
"use client";

export function SearchInput() {
  const [keyword, setKeyword] = useState("");

  return (
    <input
      value={keyword}
      onChange={(event) => setKeyword(event.target.value)}
    />
  );
}
```

---

## REACT-003: Split large components

**When to apply:**  
Components with more than 150 lines of JSX are hard to review and maintain. Split into smaller components by responsibility.

**Severity:** WARNING

### BAD

```tsx
export function BookingPage() {
  return (
    <>
      {/* header */}
      {/* filters */}
      {/* list */}
      {/* map */}
      {/* booking form */}
      {/* payment summary */}
      {/* 150+ lines of JSX */}
    </>
  );
}
```

### GOOD

```tsx
export function BookingPage() {
  return (
    <>
      <BookingHeader />
      <BookingFilters />
      <VenueList />
      <BookingSummary />
    </>
  );
}
```

---

## REACT-004: Avoid deep props drilling

**When to apply:**  
Passing props through more than 3 component levels is a signal to refactor. Consider composition, Context, or colocating state.

**Severity:** INFO

### BAD

```tsx
<App user={user}>
  <Layout user={user}>
    <Sidebar user={user}>
      <ProfileMenu user={user} />
    </Sidebar>
  </Layout>
</App>
```

### GOOD

```tsx
<UserProvider user={user}>
  <Layout>
    <Sidebar>
      <ProfileMenu />
    </Sidebar>
  </Layout>
</UserProvider>
```

---

## REACT-005: Choose children pattern vs explicit props intentionally

**When to apply:**  
Use `children` for flexible layout composition. Use explicit props when the component needs specific data and behavior.

**Severity:** INFO

### BAD

```tsx
<Card title="Profile" content={<ProfileDetails user={user} />} />
```

### GOOD

```tsx
<Card title="Profile">
  <ProfileDetails user={user} />
</Card>
```

```tsx
<UserAvatar imageUrl={user.imageUrl} displayName={user.name} />
```

---

# 2. Hooks

## REACT-006: Keep useEffect dependency arrays correct

**When to apply:**  
Every value used inside `useEffect` should be included in the dependency array unless there is a clear and safe reason.

**Severity:** SERIOUS

### BAD

```tsx
useEffect(() => {
  fetchUser(userId);
}, []);
```

### GOOD

```tsx
useEffect(() => {
  fetchUser(userId);
}, [userId]);
```

---

## REACT-007: Do not overuse useCallback and useMemo

**When to apply:**  
Use `useCallback` and `useMemo` only when there is a real reason: expensive computation, stable dependency for memoized children, or avoiding unnecessary effect triggers.

**Severity:** INFO

### BAD

```tsx
const fullName = useMemo(
  () => `${firstName} ${lastName}`,
  [firstName, lastName],
);

const handleClick = useCallback(() => {
  setOpen(true);
}, []);
```

### GOOD

```tsx
const fullName = `${firstName} ${lastName}`;

function handleClick() {
  setOpen(true);
}
```

```tsx
const filteredItems = useMemo(() => {
  return items.filter((item) => expensiveMatch(item, keyword));
}, [items, keyword]);
```

---

## REACT-008: Extract custom hooks for reusable logic

**When to apply:**  
Move reusable stateful logic out of components into custom hooks. Keep UI components focused on rendering.

**Severity:** INFO

### BAD

```tsx
export function UserProfile({ userId }: Props) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    setIsLoading(true);
    getUser(userId)
      .then(setUser)
      .finally(() => setIsLoading(false));
  }, [userId]);

  return <ProfileView user={user} isLoading={isLoading} />;
}
```

### GOOD

```tsx
function useUser(userId: string) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    setIsLoading(true);
    getUser(userId)
      .then(setUser)
      .finally(() => setIsLoading(false));
  }, [userId]);

  return { user, isLoading };
}

export function UserProfile({ userId }: Props) {
  const { user, isLoading } = useUser(userId);
  return <ProfileView user={user} isLoading={isLoading} />;
}
```

---

## REACT-009: Use useReducer for complex state transitions

**When to apply:**  
Use `useReducer` when state has multiple related fields, complex transitions, or many updates based on previous state.

**Severity:** INFO

### BAD

```tsx
const [step, setStep] = useState(1);
const [status, setStatus] = useState("idle");
const [error, setError] = useState<string | null>(null);
```

### GOOD

```tsx
type State = {
  step: number;
  status: "idle" | "submitting" | "success" | "error";
  error: string | null;
};

type Action =
  | { type: "submit" }
  | { type: "success" }
  | { type: "fail"; error: string };

const [state, dispatch] = useReducer(reducer, initialState);
```

---

## REACT-010: Never call hooks inside conditions or loops

**When to apply:**  
Hooks must be called at the top level of React components or custom hooks.

**Severity:** SERIOUS

### BAD

```tsx
if (isLoggedIn) {
  const [user, setUser] = useState(null);
}
```

```tsx
items.forEach((item) => {
  useEffect(() => {
    trackView(item.id);
  }, [item.id]);
});
```

### GOOD

```tsx
const [user, setUser] = useState<User | null>(null);

useEffect(() => {
  if (!isLoggedIn) return;
  loadUser().then(setUser);
}, [isLoggedIn]);
```

---

# 3. State Management

## REACT-011: Keep local state local

**When to apply:**  
Use local state for UI-only state used by one component or a small subtree. Do not put everything into global state.

**Severity:** INFO

### BAD

```tsx
globalStore.setState({
  isDropdownOpen: true,
});
```

### GOOD

```tsx
const [isDropdownOpen, setIsDropdownOpen] = useState(false);
```

---

## REACT-012: Use global state only for shared cross-cutting state

**When to apply:**  
Use global state for auth user, theme, feature flags, app-wide filters, or state shared by distant parts of the app.

**Severity:** INFO

### BAD

```tsx
const [currentUser, setCurrentUser] = useState<User | null>(null);
// passed through many unrelated components
```

### GOOD

```tsx
<AuthProvider user={currentUser}>
  <AppShell />
</AuthProvider>
```

---

## REACT-013: Avoid unnecessary Context re-renders

**When to apply:**  
Context value should be stable and scoped. Avoid passing large changing objects through a broad provider.

**Severity:** WARNING

### BAD

```tsx
<AuthContext.Provider value={{ user, permissions, refreshUser }}>
  {children}
</AuthContext.Provider>
```

### GOOD

```tsx
const value = useMemo(
  () => ({ user, permissions, refreshUser }),
  [user, permissions, refreshUser],
);

<AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
```

---

## REACT-014: Separate server state from client state

**When to apply:**  
Remote data from APIs should be treated as server state. Prefer React Query / TanStack Query pattern for caching, refetching, loading, and error states in Client Components.

**Severity:** WARNING

### BAD

```tsx
const [users, setUsers] = useState<User[]>([]);

useEffect(() => {
  fetch("/api/users")
    .then((res) => res.json())
    .then(setUsers);
}, []);
```

### GOOD

```tsx
const {
  data: users,
  isLoading,
  error,
} = useQuery({
  queryKey: ["users"],
  queryFn: fetchUsers,
});
```

---

# 4. Next.js 14 App Router Specific

## REACT-015: Use fetch cache and revalidate intentionally

**When to apply:**  
In Server Components and route handlers, specify caching behavior for data freshness requirements.

**Severity:** WARNING

### BAD

```tsx
const res = await fetch("https://api.example.com/products");
```

### GOOD

```tsx
const res = await fetch("https://api.example.com/products", {
  next: { revalidate: 300 },
});
```

```tsx
const res = await fetch("https://api.example.com/profile", {
  cache: "no-store",
});
```

---

## REACT-016: Use loading.tsx and error.tsx for route-level states

**When to apply:**  
Use `loading.tsx` for route loading UI and `error.tsx` for route error boundaries.

**Severity:** INFO

### BAD

```tsx
export default async function Page() {
  const data = await loadSlowData();
  return <Dashboard data={data} />;
}
```

### GOOD

```tsx
// app/dashboard/loading.tsx
export default function Loading() {
  return <DashboardSkeleton />;
}
```

```tsx
// app/dashboard/error.tsx
"use client";

export default function ErrorPage({ error, reset }: Props) {
  return <ErrorState message={error.message} onRetry={reset} />;
}
```

---

## REACT-017: Choose Route Handler vs Server Action correctly

**When to apply:**  
Use Route Handlers for public HTTP endpoints, webhooks, third-party callbacks, or external clients.  
Use Server Actions for form submissions and mutations directly from React Server Components or Client Components.

**Severity:** INFO

### BAD

```tsx
// Using Server Action for external webhook callback
export async function paymentWebhookAction() {
  "use server";
}
```

### GOOD

```tsx
// app/api/payment/webhook/route.ts
export async function POST(req: Request) {
  const payload = await req.json();
  return handleWebhook(payload);
}
```

```tsx
async function createBooking(formData: FormData) {
  "use server";
  await bookingService.create(formData);
}
```

---

## REACT-018: Use Metadata API correctly

**When to apply:**  
Use static `metadata` for fixed metadata and `generateMetadata` for dynamic pages.

**Severity:** INFO

### BAD

```tsx
export default function Page() {
  return (
    <>
      <title>Product</title>
      <ProductDetails />
    </>
  );
}
```

### GOOD

```tsx
export const metadata = {
  title: "Products",
  description: "Browse available products",
};
```

```tsx
export async function generateMetadata({ params }: Props) {
  const product = await getProduct(params.id);

  return {
    title: product.name,
    description: product.summary,
  };
}
```

---

## REACT-019: Use Next Image with width/height or fill

**When to apply:**  
`next/image` should include `width` and `height`, or `fill` with a positioned parent container.

**Severity:** WARNING

### BAD

```tsx
<Image src={user.avatarUrl} alt={user.name} />
```

### GOOD

```tsx
<Image src={user.avatarUrl} alt={user.name} width={80} height={80} />
```

```tsx
<div className="relative h-64 w-full">
  <Image src={heroUrl} alt="Hotel lobby" fill className="object-cover" />
</div>
```

---

## REACT-020: Understand Link prefetch behavior

**When to apply:**  
Use default prefetch for likely navigation. Disable prefetch for very large, rarely used, or permission-sensitive routes if needed.

**Severity:** INFO

### BAD

```tsx
<Link href="/admin/reports">Reports</Link>
```

### GOOD

```tsx
<Link href="/admin/reports" prefetch={false}>
  Reports
</Link>
```

```tsx
<Link href="/venues">Venues</Link>
```

---

# 5. Performance

## REACT-021: Avoid anonymous functions in JSX props when they cause unnecessary renders

**When to apply:**  
Avoid inline functions when passed to memoized children or frequently rendered large lists. Inline handlers are acceptable for simple local UI.

**Severity:** INFO

### BAD

```tsx
{
  items.map((item) => (
    <MemoizedRow key={item.id} onClick={() => selectItem(item.id)} />
  ));
}
```

### GOOD

```tsx
const handleSelect = useCallback(
  (id: string) => {
    selectItem(id);
  },
  [selectItem],
);

{
  items.map((item) => (
    <MemoizedRow key={item.id} itemId={item.id} onClick={handleSelect} />
  ));
}
```

---

## REACT-022: Use stable key props

**When to apply:**  
Use stable unique IDs for list keys. Avoid array index when the list can reorder, filter, insert, or delete items.

**Severity:** WARNING

### BAD

```tsx
{
  users.map((user, index) => <UserRow key={index} user={user} />);
}
```

### GOOD

```tsx
{
  users.map((user) => <UserRow key={user.id} user={user} />);
}
```

---

## REACT-023: Lazy load heavy components with dynamic import

**When to apply:**  
Use dynamic import for heavy client-only components such as charts, editors, maps, video players, or complex modals.

**Severity:** INFO

### BAD

```tsx
import RichTextEditor from "@/components/RichTextEditor";

export function ArticleForm() {
  return <RichTextEditor />;
}
```

### GOOD

```tsx
import dynamic from "next/dynamic";

const RichTextEditor = dynamic(() => import("@/components/RichTextEditor"), {
  ssr: false,
  loading: () => <p>Loading editor...</p>,
});

export function ArticleForm() {
  return <RichTextEditor />;
}
```

---

## REACT-024: Place Suspense boundaries close to slow UI

**When to apply:**  
Use Suspense around slow or async parts of the page, not necessarily around the entire page.

**Severity:** INFO

### BAD

```tsx
<Suspense fallback={<FullPageLoading />}>
  <Header />
  <SlowRecommendations />
  <Footer />
</Suspense>
```

### GOOD

```tsx
<Header />
<Suspense fallback={<RecommendationsSkeleton />}>
  <SlowRecommendations />
</Suspense>
<Footer />
```

---

# 6. Accessibility

## REACT-025: Buttons must have accessible text

**When to apply:**  
Icon-only buttons need `aria-label` or visually hidden text.

**Severity:** SERIOUS

### BAD

```tsx
<button>
  <TrashIcon />
</button>
```

### GOOD

```tsx
<button aria-label="Delete item">
  <TrashIcon />
</button>
```

---

## REACT-026: Images must have meaningful alt text

**When to apply:**  
Informative images need meaningful `alt`. Decorative images may use empty `alt=""`.

**Severity:** WARNING

### BAD

```tsx
<img src="/hotel.jpg" />
```

```tsx
<Image src={hotel.imageUrl} alt="image" width={400} height={300} />
```

### GOOD

```tsx
<Image
  src={hotel.imageUrl}
  alt={`${hotel.name} main lobby`}
  width={400}
  height={300}
/>
```

```tsx
<img src="/divider.svg" alt="" />
```

---

## REACT-027: Form inputs must have labels

**When to apply:**  
Every input, select, and textarea should have an associated label or accessible name.

**Severity:** SERIOUS

### BAD

```tsx
<input type="email" placeholder="Email" />
```

### GOOD

```tsx
<label htmlFor="email">Email</label>
<input id="email" name="email" type="email" />
```

```tsx
<input type="search" aria-label="Search venues" placeholder="Search" />
```

---

# Quick Reviewer Checklist

## Component Design

- [ ] Server Components are used by default where possible.
- [ ] `"use client"` is added only when needed.
- [ ] Components with more than 150 lines of JSX are flagged for splitting.
- [ ] Props drilling deeper than 3 levels is flagged.
- [ ] Children pattern and explicit props are used intentionally.

## Hooks

- [ ] `useEffect` dependency arrays are correct.
- [ ] `useCallback` and `useMemo` are not used for premature optimization.
- [ ] Reusable stateful logic is extracted into custom hooks when appropriate.
- [ ] Complex state transitions use `useReducer` when appropriate.
- [ ] Hooks are not called inside conditions, loops, or nested functions.

## State Management

- [ ] Local UI state stays local.
- [ ] Global state is only used for shared cross-cutting state.
- [ ] Context values are scoped and stable enough to avoid unnecessary re-renders.
- [ ] Server state is separated from client UI state.
- [ ] React Query / TanStack Query pattern is considered for client-side server state.

## Next.js 14 App Router

- [ ] `fetch()` cache and revalidate behavior are intentional.
- [ ] `loading.tsx` and `error.tsx` are used for route-level states where useful.
- [ ] Route Handlers are used for external HTTP endpoints and webhooks.
- [ ] Server Actions are used for form submissions and server-side mutations where appropriate.
- [ ] Metadata API is used instead of manual `<title>` tags.
- [ ] `next/image` has `width`/`height` or `fill`.
- [ ] Link prefetch behavior is considered for heavy or sensitive routes.

## Performance

- [ ] Anonymous functions in JSX props are avoided when they cause unnecessary renders.
- [ ] List keys use stable IDs, not array index for reorderable lists.
- [ ] Heavy client-only components are lazy loaded where appropriate.
- [ ] Suspense boundaries are placed near slow UI sections.

## Accessibility

- [ ] Icon-only buttons have accessible text.
- [ ] Images have meaningful `alt`, or empty `alt=""` if decorative.
- [ ] Form inputs have associated labels or accessible names.

## Review Decision

- [ ] SERIOUS issues are reported clearly.
- [ ] WARNING issues include practical refactor suggestions.
- [ ] INFO issues are presented as improvements, not blockers.
