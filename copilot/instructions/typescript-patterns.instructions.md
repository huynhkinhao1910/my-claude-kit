---
applyTo: "**/*.ts,**/*.tsx,**/*.js,**/*.jsx"
---

# TypeScript/JavaScript Patterns

> This file extends [common/patterns.md](../common/patterns.md) with TypeScript/JavaScript specific content.

## API Response Format

Existing project: reuse its response types. New project (`api-design`):

```typescript
interface Paging {
  current_page?: number
  per_page: number
  total?: number
  last_page?: number
  next_cursor?: string | null
  has_more?: boolean
}

interface Meta {
  message: string
  request_id: string
  code?: string                       // errors only
  errors?: Record<string, string[]>   // validation errors only
}

interface ApiResponse<T> {
  data: T | null
  paging?: Paging                     // lists only
  meta: Meta
}
```

## Custom Hooks Pattern

```typescript
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)

  useEffect(() => {
    const handler = setTimeout(() => setDebouncedValue(value), delay)
    return () => clearTimeout(handler)
  }, [value, delay])

  return debouncedValue
}
```

## Repository Pattern

```typescript
interface Repository<T> {
  findAll(filters?: Filters): Promise<T[]>
  findById(id: string): Promise<T | null>
  create(data: CreateDto): Promise<T>
  update(id: string, data: UpdateDto): Promise<T>
  delete(id: string): Promise<void>
}
```
