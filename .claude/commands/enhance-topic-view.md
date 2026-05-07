Implement the Library → TopicDetailView feature for knowledge exploration.

Goal: When a user taps a topic card, they should enter a rich "knowledge space"
for that topic — not just see a filtered list.

Target layout of TopicDetailView (top to bottom):
1. Hero section: large topic name, session count badge, platform breakdown chips
2. Question type distribution: horizontal segmented bar
   - debug = blue / research = green / howto = orange / design = purple
3. Key entities chip cloud: aggregated top_entities from all sessions in topic
4. Tag filter pills: tappable, filters the session list below
5. Session cards list: title + one-line summary + question_type badge + tag chips

Steps (in order — do not skip):
1. **Python: `llmlib/storage/db.py`**
   - Extend `get_library_overview()` topic aggregation to include:
     - `by_question_type`: count per question_type for this topic
     - `top_entities`: top 8 key_entities by frequency across sessions in topic
   - Extend `get_topics()` to return the same enriched data

2. **Python: `llmlib/api/server.py`**
   - Add fields to `TopicStats`:
     ```python
     by_question_type: List[QuestionTypeStats]
     top_entities: List[str]
     ```
   - Verify `/library/overview` and `/library/topics` both return these fields

3. **Swift: `macapp/Models/LibraryOverview.swift`**
   - Sync `TopicSummary` with new fields:
     ```swift
     let byQuestionType: [QuestionTypeStats]
     let topEntities: [String]
     ```
   - Add CodingKeys: `by_question_type`, `top_entities`

4. **Swift: `macapp/ViewModels/TopicDetailViewModel.swift`** (new file)
   - `@Observable @MainActor class TopicDetailViewModel`
   - Properties: `sessions`, `selectedTags`, `isLoading`
   - `func load(topic: String) async` — calls `GET /sessions?topic=<topic>`
   - `func toggleTag(_ tag: String)` — filters sessions by tag client-side

5. **Swift: `macapp/Views/Library/TopicDetailView.swift`** (new file)
   - Accepts `topic: TopicSummary` as init parameter
   - `.navigationTitle(topic.topic)`
   - Implement all 5 sections described in the goal above
   - Reuse `FlowLayout` from LibraryView.swift for chip clouds

6. **Swift: `macapp/Views/Library/TopicCardView.swift`**
   - Add mini question-type distribution bar at the bottom of each card
   - Use coloured `RoundedRectangle` segments proportional to `byQuestionType` counts

7. **Swift: `macapp/Views/Library/LibraryView.swift`**
   - Replace `onTapGesture { viewModel.selectedTopic = topic.topic }` with:
     `navigationDestination(for: TopicSummary.self) { topic in TopicDetailView(topic: topic) }`
   - Change TopicCardView tap to use `NavigationLink(value: topic)`

8. **Swift: `macapp/ViewModels/LibraryViewModel.swift`**
   - Remove `selectedTopic: String?` property (navigation is now stack-based)
   - Remove `selectedTopic`-triggered `loadSessions()` observer

Constraints:
- Always update Python and Swift models in the same task (Model Sync Rule)
- Do not use `selectedTopic` string state for navigation — use NavigationStack value-based routing
- FlowLayout is already defined in LibraryView.swift — do not duplicate it
- Question type colour mapping must be consistent across TopicDetailView and TopicCardView
