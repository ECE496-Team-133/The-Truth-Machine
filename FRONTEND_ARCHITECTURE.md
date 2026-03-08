# Frontend Architecture & System Design Decisions

## Table of Contents
1. [Overview](#overview)
2. [Frontend Architecture](#frontend-architecture)
3. [System Architecture](#system-architecture)
4. [Key Design Decisions](#key-design-decisions)
5. [Data Flow](#data-flow)
6. [Component Responsibilities](#component-responsibilities)

---

## Overview

The Truth Machine is a fact-checking application that validates claims against multiple sources (Wikipedia, AP News, Reuters, The Guardian) using AI-powered analysis. This document explains the architectural decisions and design patterns used in the system, focusing on the "why" rather than the "how" for junior engineers.

---

## Frontend Architecture

### Component Hierarchy

The frontend follows a **hierarchical component structure** that mirrors the logical flow of fact-checking:

```
App (Root Component)
├── QueryInput
├── FactCheckTree
    └── ClaimNode (one per claim)
        ├── ValidationBlock (prerequisites)
        ├── ValidationBlock (additional info)
        └── ValidationBlock (final claim)
```

**Why this structure?**
- **Separation of Concerns**: Each component has a single, well-defined responsibility
- **Reusability**: `ValidationBlock` is used for all three types of validations (prerequisites, additional info, final claim)
- **Maintainability**: Changes to one part of the UI don't affect others
- **Scalability**: Easy to add new claim types or validation stages

### State Management

The application uses **React's built-in state management** (useState hooks) rather than external state management libraries like Redux or Zustand.

**Why local state management?**
- **Simplicity**: The application's state is relatively straightforward - it's primarily a single fact-checking session
- **No Global State Needed**: State doesn't need to be shared across multiple screens or persisted across sessions
- **Real-time Updates**: State updates come directly from the server stream, making local state management sufficient
- **Avoid Over-engineering**: Adding Redux would introduce unnecessary complexity for a single-page application

**State Structure:**
- `factCheckData`: Final complete data structure (set when fact-checking completes)
- `incrementalData`: Partial data structure that updates in real-time (used during loading)
- `loading`: Boolean flag indicating if a fact-check is in progress
- `error`: Error message if something goes wrong
- `progressUpdates`: Array of all progress updates received (for debugging/logging)
- `currentStep`: The most recent step being processed (for highlighting in UI)
- `abortController`: Allows canceling in-progress requests

**Why two data structures (factCheckData and incrementalData)?**
- **User Experience**: Users see results appear incrementally as they're validated, not just at the end
- **Feedback**: Users can see which prerequisite is currently being checked, which article is being fetched, etc.
- **Progressive Enhancement**: The UI builds up the tree structure as data arrives, creating a sense of progress

### Real-Time Updates via Server-Sent Events (SSE)

The frontend receives updates from the backend using **Server-Sent Events (SSE)**, a one-way communication protocol from server to client.

**Why SSE instead of WebSockets?**
- **Simplicity**: SSE is simpler - it's just HTTP with a special content type
- **One-Way Communication**: We only need server-to-client updates, not bidirectional communication
- **Automatic Reconnection**: Browsers handle SSE reconnection automatically
- **No Protocol Overhead**: SSE is lighter than WebSockets for one-way streaming
- **HTTP-Based**: Works through firewalls and proxies more easily than WebSockets

**Why SSE instead of polling?**
- **Efficiency**: No need to repeatedly ask "are you done yet?" - the server pushes updates when ready
- **Real-Time**: Updates arrive immediately when available, not on a polling interval
- **Reduced Server Load**: Server doesn't need to handle constant polling requests
- **Better UX**: Users see updates as they happen, creating a smoother experience

**How it works:**
1. Frontend sends POST request to `/api/factcheck`
2. Backend responds with `text/event-stream` content type
3. Backend streams JSON messages as events: `data: {"type": "step", "message": "..."}\n\n`
4. Frontend reads the stream using `ReadableStream` API
5. Each event updates the UI incrementally

### Incremental UI Rendering

The UI renders validation blocks **as soon as they're created**, even before validation completes. This creates a "skeleton" view that fills in progressively.

**Why incremental rendering?**
- **Perceived Performance**: Users see structure immediately, making the app feel faster
- **Transparency**: Users can see what's being checked before it completes
- **Better UX**: Instead of a blank screen, users see a tree structure that's being built
- **Reduces Anxiety**: Users know the system is working, not stuck

**The rendering strategy:**
1. When plan is generated, all prerequisites and additional info blocks are created with "pending" status
2. As each item is processed, its status updates: `pending` → `validating` → `validated`/`failed`
3. Visual indicators (colors, spinners) show current state
4. Final claim appears when prerequisites are validated

---

## System Architecture

### Overall Architecture Pattern

The system follows a **client-server architecture** with a clear separation between frontend (React) and backend (FastAPI).

```
┌─────────────────┐         HTTP/SSE          ┌─────────────────┐
│                 │ ◄─────────────────────── │                 │
│  React Frontend │                           │  FastAPI Backend│
│  (Port 5173)    │ ───────────────────────► │  (Port 8000)    │
│                 │      POST /api/factcheck │                 │
└─────────────────┘                           └─────────────────┘
                                                      │
                                                      ▼
                                            ┌─────────────────┐
                                            │  External APIs  │
                                            │  - OpenAI       │
                                            │  - Google Search│
                                            │  - Wikipedia    │
                                            │  - News Sites   │
                                            └─────────────────┘
```

**Why client-server architecture?**
- **Security**: API keys and sensitive operations stay on the server
- **Performance**: Backend can cache results, optimize queries, and handle heavy processing
- **Scalability**: Backend can be scaled independently of frontend
- **Separation of Concerns**: Frontend handles UI, backend handles business logic

### Backend Architecture

The backend is built with **FastAPI**, a modern Python web framework.

**Why FastAPI?**
- **Performance**: Very fast, comparable to Node.js frameworks
- **Type Safety**: Built-in support for Pydantic models for request/response validation
- **Modern Python**: Uses Python 3.8+ features like type hints and async/await
- **Auto Documentation**: Automatically generates OpenAPI/Swagger documentation
- **Streaming Support**: Built-in support for streaming responses (SSE)
- **Developer Experience**: Great error messages and debugging tools

**Backend Structure:**
```
api.py (FastAPI app)
├── Fact-checking pipeline
│   ├── Extract claims from query
│   ├── For each claim:
│   │   ├── Generate plan (prerequisites, additional info, template)
│   │   ├── Validate prerequisites (parallel)
│   │   ├── Extract additional info (parallel)
│   │   ├── Generate final claim
│   │   └── Validate final claim
│   └── Stream progress updates
└── Utility modules
    ├── claims.py (LLM interactions for planning)
    ├── factcheck.py (LLM interactions for validation)
    ├── google_custom_search.py (search API)
    ├── wikipedia_scraper.py (web scraping)
    └── news_scrapers.py (news site scraping)
```

### Fact-Checking Pipeline

The fact-checking process follows a **plan-based approach** rather than directly validating the original claim.

**Why a plan-based approach?**
- **Complex Claims**: Many claims require validating prerequisites first (e.g., "X is a member of Y" requires checking if X exists, if Y exists, and if X is actually a member)
- **Structured Validation**: Breaking down complex claims into simpler sub-claims makes validation more reliable
- **Transparency**: Users can see the reasoning process, not just the final answer
- **Error Handling**: If a prerequisite fails, we can stop early and explain why

**The Pipeline Steps:**

1. **Claim Extraction**: Split user query into individual claims
   - **Why?** Users might ask multiple questions in one query
   - **Example**: "Is Paris the capital of France? Also, is London in England?"

2. **Plan Generation** (for each claim):
   - **Prerequisites**: Facts that must be true for the claim to be validatable
   - **Additional Info Needed**: Information required to construct the final claim
   - **Final Claim Template**: A template for the final, specific claim to validate
   - **Why?** The original claim might be vague or require context

3. **Prerequisite Validation** (parallel):
   - Each prerequisite is validated independently
   - **Why parallel?** Prerequisites are independent - no need to wait for one to finish before starting another
   - **Performance**: Reduces total time from O(n) to O(1) for n prerequisites

4. **Additional Info Extraction** (parallel):
   - Extract required information from sources
   - **Why parallel?** Same reason as prerequisites - independent operations
   - **Context Building**: Information extracted here is used to build the final claim

5. **Final Claim Generation**:
   - Combine template with extracted information
   - **Why?** Creates a specific, validatable claim from the original vague query

6. **Final Validation**:
   - Validate the final claim against sources
   - **Why last?** Only makes sense to validate after we have all context

**Why parallel processing?**
- **Performance**: If we have 5 prerequisites, sequential processing takes 5x longer than parallel
- **User Experience**: Users see multiple items being processed simultaneously
- **Resource Utilization**: Modern servers have multiple CPU cores - use them!
- **Trade-off**: Slightly more complex code, but significant performance gains

### Multi-Source Validation

The system supports validating claims against multiple sources: Wikipedia, AP News, Reuters, and The Guardian.

**Why multiple sources?**
- **Reliability**: Cross-referencing multiple sources increases confidence
- **Coverage**: Different sources may have information about different aspects
- **Bias Reduction**: Multiple perspectives reduce single-source bias
- **Fallback**: If one source fails, others can still provide answers

**Source Selection Strategy:**
- **Wikipedia**: Best for basic factual queries (entity existence, definitions, historical facts)
- **News Sources**: Best for recent events, current affairs, and news-worthy claims
- **Automatic Fallback**: For entity detection queries, Wikipedia is automatically included even if not selected

**Why automatic Wikipedia fallback?**
- **Entity Detection**: Queries like "there is an entity named X" are better answered by Wikipedia
- **User Experience**: Users don't need to know which source is best for which query type
- **Reliability**: Wikipedia is comprehensive for basic factual information

### Caching Strategy

The backend implements an **in-memory cache** for scraped articles.

**Why caching?**
- **Performance**: Scraping the same article multiple times is wasteful
- **Cost**: Reduces API calls to search engines
- **Speed**: Cached articles are returned instantly
- **Rate Limiting**: Helps avoid hitting rate limits on external APIs

**Cache Key Strategy:**
- Uses `source:query` as the cache key
- **Why include source?** Different sources might have different articles for the same query
- **Why query-based?** Same query should return same article (within a session)

**Cache Scope:**
- Cache is per-request (cleared between fact-checks)
- **Why not persistent?** Articles can change over time, and we want fresh data
- **Why per-request?** Multiple claims in one query might reference the same articles

---

## Key Design Decisions

### Why React?

**Component-Based Architecture:**
- **Reusability**: Components like `ValidationBlock` can be used multiple times
- **Maintainability**: Each component is self-contained and testable
- **Developer Experience**: Large ecosystem, great tooling, excellent documentation

**Virtual DOM:**
- **Performance**: Efficient updates - only re-renders what changed
- **Predictability**: React's reconciliation algorithm makes UI updates predictable

**Ecosystem:**
- **Vite**: Fast build tool and dev server
- **Framer Motion**: Smooth animations for better UX
- **Large Community**: Easy to find solutions to common problems

### Why Vite Instead of Create React App?

**Performance:**
- **Faster Dev Server**: Uses native ES modules, no bundling in development
- **Faster Builds**: Uses esbuild (written in Go) for bundling
- **Hot Module Replacement**: Instant updates without full page reload

**Modern Tooling:**
- **Native ES Modules**: No need for complex bundling in development
- **Better DX**: Faster feedback loop for developers

### Why Framer Motion for Animations?

**Declarative API:**
- Animations are defined declaratively, matching React's philosophy
- Easy to understand and maintain

**Performance:**
- Uses hardware acceleration
- Optimized for React's rendering cycle

**User Experience:**
- Smooth animations make the app feel polished and responsive
- Visual feedback for state changes (e.g., when a validation completes)

### Why FastAPI Instead of Flask or Django?

**Performance:**
- Built on Starlette and Pydantic, which are very fast
- Async/await support for handling concurrent requests

**Type Safety:**
- Pydantic models provide automatic validation
- Catches errors at request time, not runtime

**Modern Python:**
- Uses Python 3.8+ features
- Better type hints support
- Async/await for I/O-bound operations

**Developer Experience:**
- Automatic API documentation
- Great error messages
- Easy to test

### Why Server-Sent Events Instead of WebSockets?

**Simplicity:**
- SSE is just HTTP with a special content type
- No need for a separate protocol or connection management

**One-Way Communication:**
- We only need server-to-client updates
- No need for bidirectional communication

**Automatic Reconnection:**
- Browsers handle reconnection automatically
- Less code to maintain

**HTTP-Based:**
- Works through firewalls and proxies
- Easier to debug (just HTTP requests)

### Why Parallel Processing?

**Performance:**
- If we have 5 prerequisites, sequential takes 5x longer
- Parallel processing uses available CPU cores

**User Experience:**
- Users see multiple items being processed simultaneously
- Feels faster and more responsive

**Trade-offs:**
- Slightly more complex code
- Need to handle thread safety (though Python's GIL helps here)
- Worth it for the performance gains

### Why Incremental UI Updates?

**Perceived Performance:**
- Users see structure immediately
- App feels faster even if total time is the same

**Transparency:**
- Users can see what's being checked
- Reduces anxiety about whether the system is working

**Better UX:**
- Progressive disclosure - information appears as it's ready
- No "blank screen" waiting period

### Why Plan-Based Fact-Checking?

**Complex Claims:**
- Many claims require validating prerequisites first
- Breaking down into simpler sub-claims is more reliable

**Transparency:**
- Users can see the reasoning process
- Not just a black box that says "true" or "false"

**Error Handling:**
- If a prerequisite fails, we can stop early
- Clear explanation of why validation failed

**Example:**
- Claim: "Ada Lovelace is a member of the Royal Society"
- Prerequisites:
  1. Ada Lovelace exists (entity detection)
  2. Royal Society exists (entity detection)
- Additional Info: When was Ada Lovelace born? When did she die?
- Final Claim: "Ada Lovelace (born 1815, died 1852) was a member of the Royal Society"

---

## Data Flow

### Request Flow

1. **User submits query** via `QueryInput` component
2. **App component** creates abort controller and sets loading state
3. **POST request** sent to `/api/factcheck` with query and source selection
4. **Backend** starts processing and streams updates via SSE
5. **Frontend** reads stream and updates state incrementally
6. **UI re-renders** as state updates, showing progress in real-time
7. **Final result** replaces incremental data when complete

### Data Structure Evolution

**Initial State:**
```javascript
incrementalData = {
  query: "Is Paris the capital of France?",
  claims: []
}
```

**After Plan Generation:**
```javascript
incrementalData = {
  query: "Is Paris the capital of France?",
  claims: [{
    text: "Paris is the capital of France",
    prerequisites: [
      { text: "Paris exists", validation: { status: "pending" } },
      { text: "France exists", validation: { status: "pending" } }
    ],
    additional_info: [],
    final_claim: null,
    final_validation: null
  }]
}
```

**During Validation:**
```javascript
// Prerequisites update from "pending" → "validating" → "validated"
prerequisites[0].validation = {
  status: "validating",
  article_query: "Paris",
  article_url: "https://en.wikipedia.org/wiki/Paris",
  ...
}
```

**Final State:**
```javascript
factCheckData = {
  query: "Is Paris the capital of France?",
  claims: [{
    text: "Paris is the capital of France",
    prerequisites: [...], // all validated
    additional_info: [...],
    final_claim: "Paris (city in France) is the capital of France",
    final_validation: {
      status: "validated",
      label: "True",
      evidence: "...",
      link: "..."
    }
  }],
  total_time: 12.34
}
```

### Event Types

The SSE stream sends different event types:

- `step`: General progress update (e.g., "Generating plan...")
- `claim`: Claim-level update (e.g., "Processing claim 1/2")
- `plan_generated`: Plan structure is ready (creates all UI blocks)
- `prerequisite`: Prerequisite validation update
- `additional_info`: Additional info extraction update
- `final_claim`: Final claim generation and validation update
- `complete`: Fact-checking is complete
- `error`: An error occurred

**Why multiple event types?**
- **Granularity**: Different components need different information
- **Flexibility**: Easy to add new event types without breaking existing code
- **Debugging**: Clear separation makes it easier to trace issues

---

## Component Responsibilities

### App Component
- **Orchestration**: Coordinates all child components
- **State Management**: Manages global application state
- **API Communication**: Handles SSE stream connection
- **Error Handling**: Displays errors to users
- **Request Cancellation**: Allows canceling in-progress requests

### QueryInput Component
- **User Input**: Captures query text from user
- **Source Selection**: Allows users to select which sources to check
- **Form Validation**: Ensures at least one source is selected
- **Submission**: Triggers fact-checking process

### FactCheckTree Component
- **Container**: Wraps all claim nodes
- **Header**: Displays overall status and timing
- **Rendering Logic**: Determines which claims to show
- **Loading States**: Handles display during loading vs. completed states

### ClaimNode Component
- **Claim Display**: Shows individual claim text
- **Section Organization**: Organizes prerequisites, additional info, and final claim
- **Processing State**: Determines which item is currently being processed
- **Conditional Rendering**: Shows sections only when data is available

### ValidationBlock Component
- **Status Display**: Shows validation status (pending, validating, validated, failed)
- **Visual Indicators**: Color-coded status, loading spinners
- **Evidence Display**: Shows evidence text and links
- **Error Display**: Shows error messages when validation fails
- **Reusability**: Used for prerequisites, additional info, and final claims

---

## Summary

The Truth Machine's architecture prioritizes:

1. **User Experience**: Real-time updates, incremental rendering, clear visual feedback
2. **Performance**: Parallel processing, caching, efficient rendering
3. **Maintainability**: Clear component boundaries, reusable components
4. **Transparency**: Users can see the reasoning process, not just the final answer
5. **Reliability**: Multiple sources, error handling, graceful degradation

Each design decision was made with these priorities in mind, balancing complexity with benefits. The result is a system that is both performant and maintainable, with a focus on providing users with clear, understandable fact-checking results.
