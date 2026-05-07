Add a new API endpoint: $ARGUMENTS

Steps:
1. Read `llmlib/api/server.py` to understand existing endpoint patterns.
2. Define a Pydantic response model in `server.py` if the response shape is new.
3. Implement the endpoint using `db: LibraryDB = Depends(get_db)`.
4. Read `macapp/Services/APIClient.swift` to understand the existing fetch pattern.
5. Add a corresponding `func fetch<Name>(...) async throws -> <ResponseType>` in APIClient.
6. Add a matching Swift model in `macapp/Models/` if the response type is new.
7. Ensure CodingKeys in Swift match the snake_case JSON from Python.

Constraints:
- Never break existing endpoint signatures
- New endpoints must use the existing `get_db` dependency
- Swift model fields must exactly mirror the Pydantic response model
- Use `async throws` pattern in APIClient, consistent with existing methods
