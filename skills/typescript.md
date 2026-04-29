# TypeScript Review Guidelines

## Common Issues to Check
- `any` type usage — should be avoided, use proper types or `unknown`
- Missing return types on exported functions
- Non-null assertions (`!`) without justification
- `as` type casting without validation

## Best Practices
- Use `strict` mode in tsconfig
- Prefer interfaces over type aliases for object shapes
- Use `readonly` for immutable properties

## Security
- Validate external data before trusting TypeScript types
- Use `zod` or similar for runtime validation of unknown data
