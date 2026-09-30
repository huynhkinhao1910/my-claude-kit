---
applyTo: "**"
---

# Common Patterns

## Skeleton Projects

When implementing new functionality:
1. Search for battle-tested skeleton projects
2. Use parallel agents to evaluate options:
   - Security assessment
   - Extensibility analysis
   - Relevance scoring
   - Implementation planning
3. Clone best match as foundation
4. Iterate within proven structure

## Design Patterns

### Repository Pattern

Encapsulate data access behind a consistent interface:
- Repositories own every query; services own business rules and transactions
- Name methods for what the caller needs (`paginateForUser`, `findForUpdate`) rather than generic CRUD
- Laravel house style: repositories are concrete classes with no interface (`laravel-patterns`)
- Test against the real database; mock only what sits outside the app

### API Response Format

Follow the `api-design` skill:
- Existing project: detect the response format it already uses and follow it exactly. Never add a second format.
- New project: `data` + `paging` (lists only) + `meta` (`message`, `request_id`). Errors: `data: null` + `meta.message`, `meta.code`, `meta.errors` (validation only).
