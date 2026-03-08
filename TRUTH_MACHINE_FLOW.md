# Truth Machine Flow Diagram

```mermaid
flowchart TD
    Start([User Input]) --> ExtractClaims[Use LLM to Extract Factual Claims]
    
    ExtractClaims --> Claim1[Claim 1]
    ExtractClaims --> Claim2[Claim 2]
    ExtractClaims --> ClaimN[Claim N]
    
    Claim1 --> ProcessClaim1[Process Claim 1]
    Claim2 --> ProcessClaim2[Process Claim 2]
    ClaimN --> ProcessClaimN[Process Claim N]
    
    ProcessClaim1 --> PlanGen1[Generate Plan:<br/>- Prerequisite Questions<br/>- Additional Info Questions<br/>- Final Claim Template]
    
    PlanGen1 --> PrereqValidation1{Validate Prerequisites<br/>IN PARALLEL}
    
    PrereqValidation1 --> Prereq1_1[Prerequisite 1:<br/>Query Wikipedia<br/>Scrape Article<br/>Fact-Check]
    PrereqValidation1 --> Prereq1_2[Prerequisite 2:<br/>Query Wikipedia<br/>Scrape Article<br/>Fact-Check]
    PrereqValidation1 --> Prereq1_N[Prerequisite N:<br/>Query Wikipedia<br/>Scrape Article<br/>Fact-Check]
    
    Prereq1_1 --> CheckPrereq1{All Prerequisites<br/>Valid?}
    Prereq1_2 --> CheckPrereq1
    Prereq1_N --> CheckPrereq1
    
    CheckPrereq1 -->|Invalid| FalseLabel1[Label: False]
    CheckPrereq1 -->|Valid| AdditionalInfo1{Extract Additional Info<br/>IN PARALLEL}
    
    AdditionalInfo1 --> Info1_1[Info Item 1:<br/>Query Wikipedia<br/>Scrape Article<br/>Extract Answer]
    AdditionalInfo1 --> Info1_2[Info Item 2:<br/>Query Wikipedia<br/>Scrape Article<br/>Extract Answer]
    AdditionalInfo1 --> Info1_N[Info Item N:<br/>Query Wikipedia<br/>Scrape Article<br/>Extract Answer]
    
    Info1_1 --> FillTemplate1[Fill Template with<br/>Extracted Info]
    Info1_2 --> FillTemplate1
    Info1_N --> FillTemplate1
    
    FillTemplate1 --> FinalClaim1[Generate Final Claim]
    FinalClaim1 --> FinalValidation1[Verify Final Claim<br/>Against Wikipedia]
    FinalValidation1 --> Result1[Return Evidence/<br/>Truth Label]
    
    ProcessClaim2 --> PlanGen2[Generate Plan]
    PlanGen2 --> PrereqValidation2{Validate Prerequisites<br/>IN PARALLEL}
    PrereqValidation2 --> CheckPrereq2{All Valid?}
    CheckPrereq2 -->|Valid| AdditionalInfo2{Extract Additional Info<br/>IN PARALLEL}
    AdditionalInfo2 --> FillTemplate2[Fill Template]
    FillTemplate2 --> FinalValidation2[Verify Final Claim]
    FinalValidation2 --> Result2[Return Result]
    
    ProcessClaimN --> PlanGenN[Generate Plan]
    PlanGenN --> PrereqValidationN{Validate Prerequisites<br/>IN PARALLEL}
    PrereqValidationN --> CheckPrereqN{All Valid?}
    CheckPrereqN -->|Valid| AdditionalInfoN{Extract Additional Info<br/>IN PARALLEL}
    AdditionalInfoN --> FillTemplateN[Fill Template]
    FillTemplateN --> FinalValidationN[Verify Final Claim]
    FinalValidationN --> ResultN[Return Result]
    
    Result1 --> End([All Claims Processed])
    Result2 --> End
    ResultN --> End
    FalseLabel1 --> End
    
    style PrereqValidation1 fill:#e1f5ff,stroke:#0066cc,stroke-width:3px
    style AdditionalInfo1 fill:#e1f5ff,stroke:#0066cc,stroke-width:3px
    style PrereqValidation2 fill:#e1f5ff,stroke:#0066cc,stroke-width:3px
    style AdditionalInfo2 fill:#e1f5ff,stroke:#0066cc,stroke-width:3px
    style PrereqValidationN fill:#e1f5ff,stroke:#0066cc,stroke-width:3px
    style AdditionalInfoN fill:#e1f5ff,stroke:#0066cc,stroke-width:3px
```

## Key Parallelization Points

1. **Prerequisite Validation (Parallel)**: All prerequisite questions for a claim are validated simultaneously. Each prerequisite independently:
   - Queries Wikipedia for relevant article
   - Scrapes article content
   - Fact-checks the prerequisite against the article
   - Returns validation result

2. **Additional Information Extraction (Parallel)**: All additional information questions for a claim are processed simultaneously. Each information item independently:
   - Queries Wikipedia for relevant article
   - Scrapes article content
   - Extracts the answer from the article
   - Returns extracted information

3. **Sequential Dependencies**: 
   - Plan generation must complete before prerequisites and additional info can be processed
   - Prerequisites must all be valid before additional info extraction begins
   - Final claim generation depends on all additional info being extracted
   - Final validation depends on final claim generation







