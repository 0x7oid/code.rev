# Architecture Intent - acme_notes

## Intended layering
1. **Transport layer** (`app.py`) - HTTP routing ONLY. Parse the request,
   delegate to a service function, serialise the response. No business logic,
   no direct DB access, no shell calls.
2. **Domain layer** (`calculations.py`) - pure business logic, no IO.
3. **Data layer** (`db.py`) - all persistence access, parameterised queries only.
4. **Utilities** (`utils.py`) - cross-cutting helpers.

## Conventions
- Handlers should be thin (a few lines): validate -> call service -> respond.
- No function should mix validation, business rules, side effects and IO.
- Secrets come from environment/config, never hardcoded.
- All user input is validated/escaped at the boundary.

## Known smells to watch for
- "God" handlers doing everything inline.
- Business logic leaking into the transport layer.
- Direct string interpolation into SQL.
