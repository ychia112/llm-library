Audit and sync the Python and Swift data models.

Check the following pairs for field consistency:

1. `llmlib/models.py :: Session`
   ↔ `macapp/Models/Session.swift :: Session`
   Fields to check: id, source_id, platform, title, created_at, updated_at,
                    messages, topic, tags, key_entities, question_type, summary

2. `llmlib/api/server.py :: TopicStats`
   ↔ `macapp/Models/LibraryOverview.swift :: TopicSummary`
   Fields to check: topic, count, top_tags (+ any new fields)

3. `llmlib/api/server.py :: LibraryOverview`
   ↔ `macapp/Models/LibraryOverview.swift :: LibraryOverview`

4. `llmlib/api/server.py :: SessionSummary`
   ↔ `macapp/Models/Session.swift` (summary variant if any)

For each mismatch found:
- Report the field name, Python type, and Swift type
- Apply the fix to both files in the same edit
- Ensure CodingKeys in Swift use the snake_case equivalent of the Python field name

Constraints:
- Never remove fields that exist on both sides without confirming the feature is gone
- Optional fields in Python (`Optional[str]`) → optional in Swift (`String?`)
- List fields in Python (`List[str]`) → array in Swift (`[String]`)
- datetime in Python → String in Swift (ISO8601, decoded via `iso8601DateDecodingStrategy`)
