# Truth Machine - Module Diagrams

## Article Fetching Module (Simplified)

```mermaid
flowchart LR
    A[Query] --> B[Search<br/>Google]
    B --> C[Download<br/>Articles]
    C --> D[Clean<br/>Content]
    D --> E[Return<br/>Articles]
    
    style A fill:#e1f5ff
    style E fill:#c8e6c9
```

**Sources:** Wikipedia • AP • Reuters • Guardian

---

## Claim Verification Module (Simplified)

```mermaid
flowchart LR
    A[Claim] --> B[Get<br/>Articles]
    B --> C[AI<br/>Analyzes]
    C --> D{Answer<br/>Found?}
    D -->|Yes| E[Return:<br/>True/False<br/>+ Evidence]
    D -->|No| F[Try Next<br/>Source]
    F --> C
    
    style A fill:#e1f5ff
    style E fill:#c8e6c9
    style F fill:#fff9c4
```

---

## Complete System Flow (Simplified)

```mermaid
flowchart LR
    A[User Query] --> B[Fetch<br/>Articles]
    B --> C[Verify<br/>Claim]
    C --> D[Return<br/>Result]
    
    style A fill:#e1f5ff
    style D fill:#c8e6c9
```

---

## Article Fetching Module - Performance Metrics

In a **250-claim benchmark**, demonstrating high reliability in article retrieval across multiple sources.

### Per Claim

**Average article retrieval time across 4 sources (Wikipedia, AP, Reuters, Guardian), significantly outperforming our target.**

### Target Exceeded

Successfully met and surpassed targets of **under 8 seconds per source** and **over 85% article retrieval success rate**.

---

## Claim Verification Module - Performance Metrics

In a **250-claim benchmark**, demonstrating high reliability in claim verification.

### Per Claim

**Average verification time with evidence extraction, significantly outperforming our target.**

### Target Exceeded

Successfully met and surpassed targets of **under 15 seconds per verification** and **over 82% definitive answer rate**.

