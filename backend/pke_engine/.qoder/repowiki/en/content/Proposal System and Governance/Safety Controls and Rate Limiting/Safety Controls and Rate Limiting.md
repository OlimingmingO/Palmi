# Safety Controls and Rate Limiting

<cite>
**Referenced Files in This Document**
- [README.md](file://README.md)
- [package.json](file://package.json)
- [bin/pke](file://bin/pke)
- [scripts/pke.mjs](file://scripts/pke.mjs)
- [docs/prd.md](file://docs/prd.md)
- [docs/implementation-notes.md](file://docs/implementation-notes.md)
- [docs/implementation-backlog.md](file://docs/implementation-backlog.md)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)

## Introduction
This document explains the comprehensive safety control system implemented in the Personal Knowledge Engine (PKE) MVP. It covers rate limiting, confidence thresholds, append-only validation, built-in safeguards (maximum daily proposals, candidate limits, event retention caps, file size restrictions), confidence-based safety mechanisms (high-confidence automatic application, safe append-only proposal validation, batch-safe processing), audit trails (proposal tracking, approval history, backup mechanisms), governance gates preventing unauthorized wiki modifications, and controlled self-improvement. It also includes examples of safety violations and how the system prevents unauthorized changes.

## Project Structure
The PKE MVP is a Node.js CLI with a small set of core modules:
- CLI entrypoint: a Bash wrapper that invokes the main script.
- Main script: implements all commands, safety controls, governance gates, and audit facilities.
- Documentation: PRD, implementation notes, and backlog define intended safety behavior and enforcement targets.

```mermaid
graph TB
subgraph "CLI Layer"
BIN["bin/pke"]
PKEMJS["scripts/pke.mjs"]
end
subgraph "Engine State (.pke)"
STATE[".pke/state.json"]
MONITORSTATE[".pke/monitor-state.json"]
EVENTS[".pke/events.jsonl"]
REPORTS[".pke/reports/"]
PROPOSALS[".pke/proposals/"]
APPLIED[".pke/applied/"]
REJECTED[".pke/rejected/"]
BACKUPS[".pke/backups/"]
end
subgraph "Vault"
RAW["raw/"]
WIKI["wiki/"]
end
subgraph "External"
QMD["qmd engine"]
end
BIN --> PKEMJS
PKEMJS --> STATE
PKEMJS --> MONITORSTATE
PKEMJS --> EVENTS
PKEMJS --> REPORTS
PKEMJS --> PROPOSALS
PKEMJS --> APPLIED
PKEMJS --> REJECTED
PKEMJS --> BACKUPS
PKEMJS --> RAW
PKEMJS --> WIKI
PKEMJS --> QMD
```

**Diagram sources**
- [bin/pke](file://bin/pke)
- [scripts/pke.mjs](file://scripts/pke.mjs)
- [docs/prd.md](file://docs/prd.md)

**Section sources**
- [README.md](file://README.md)
- [package.json](file://package.json)
- [bin/pke](file://bin/pke)
- [scripts/pke.mjs](file://scripts/pke.mjs)
- [docs/prd.md](file://docs/prd.md)

## Core Components
- Governance gates: compile, propose, apply, and reject enforce that wiki writes occur only under explicit user control.
- Safety controls: file size limits, event retention caps, proposal caps, and candidate queue limits.
- Confidence-based safety: confidence levels influence proposal ranking and eligibility for fast-path approval.
- Append-only validation: patch operations are restricted to safe sections and types.
- Audit trail: proposals, backups, and change reports track all wiki modifications.
- Controlled self-improvement: retrieval tuning and compile strategy refinement use historical acceptance rates to adjust confidence and reduce friction for high-confidence proposals.

**Section sources**
- [README.md](file://README.md)
- [docs/prd.md](file://docs/prd.md)
- [docs/implementation-backlog.md](file://docs/implementation-backlog.md)
- [scripts/pke.mjs](file://scripts/pke.mjs)

## Architecture Overview
The safety system spans CLI commands, state files, and the qmd engine. The monitor observes vault changes and emits knowledge events. Proposals are generated from events and must be approved before applying. The apply command enforces backup, append-only patching, and qmd refresh.

```mermaid
sequenceDiagram
participant User as "User"
participant CLI as "pke CLI"
participant Monitor as "Monitor"
participant Events as "events.jsonl"
participant Proposals as "proposals/"
participant Wiki as "wiki/"
User->>CLI : "pke monitor"
CLI->>Monitor : scan vault
Monitor->>Events : append knowledge events
User->>CLI : "pke candidates"
CLI->>Events : read events
CLI->>Proposals : create proposal (append-only)
User->>CLI : "pke propose ..."
CLI->>Proposals : write proposal
User->>CLI : "pke apply <id>"
CLI->>Wiki : backup target page
CLI->>Wiki : apply append-only patch
CLI->>Events : record apply event
CLI->>CLI : refresh qmd
CLI-->>User : apply result
```

**Diagram sources**
- [scripts/pke.mjs](file://scripts/pke.mjs)
- [docs/prd.md](file://docs/prd.md)

## Detailed Component Analysis

### Rate Limiting and Built-in Safeguards
- Maximum daily proposals: the system prioritizes candidates and limits to a fixed number per day to avoid overload.
- Candidate limits: candidates queue is capped and expires after a time window.
- Event retention caps: event log rotation is enforced to cap entries.
- File size restrictions: vault scans skip files exceeding a maximum size.

```mermaid
flowchart TD
Start(["Daily Compilation"]) --> LoadEvents["Load recent events"]
LoadEvents --> FilterTriggers["Filter compile-trigger events"]
FilterTriggers --> ExpireOld["Expire candidates older than threshold"]
ExpireOld --> CapQueue["Cap candidates to maximum"]
CapQueue --> Rank["Rank by confidence and evidence"]
Rank --> Limit["Limit to maximum daily proposals"]
Limit --> CreateProposals["Create proposals (append-only)"]
CreateProposals --> End(["Ready for review"])
```

**Diagram sources**
- [scripts/pke.mjs](file://scripts/pke.mjs)
- [docs/implementation-backlog.md](file://docs/implementation-backlog.md)

**Section sources**
- [scripts/pke.mjs](file://scripts/pke.mjs)
- [docs/implementation-backlog.md](file://docs/implementation-backlog.md)

### Confidence Thresholds and Confidence-Based Safety
- Confidence levels: proposals carry a confidence rating used to rank candidates and adjust confidence based on historical acceptance rates.
- High-confidence automatic application: proposals meeting strict criteria can be fast-tracked for batch approval.
- Safe append-only proposal validation: only specific operations and sections are permitted.

```mermaid
flowchart TD
Start(["Proposal Created"]) --> HasConf["Has confidence?"]
HasConf --> |No| DefaultLow["Assign low confidence"]
HasConf --> |Yes| BaseConf["Use base confidence"]
BaseConf --> History["Adjust by acceptance history"]
DefaultLow --> History
History --> Eligible{"Eligible for fast-path?"}
Eligible --> |Yes| Batch["Batch-safe approval"]
Eligible --> |No| Manual["Manual review required"]
Batch --> Apply["Apply with backup"]
Manual --> Apply
Apply --> End(["Applied"])
```

**Diagram sources**
- [scripts/pke.mjs](file://scripts/pke.mjs)
- [docs/implementation-backlog.md](file://docs/implementation-backlog.md)

**Section sources**
- [scripts/pke.mjs](file://scripts/pke.mjs)
- [docs/implementation-backlog.md](file://docs/implementation-backlog.md)

### Append-Only Validation and Governance Gates
- Governance gates: wiki writes are gated behind explicit commands and approvals.
- Append-only validation: patch operations are restricted to safe sections and types.
- Atomicity: apply backs up the target page before mutating.

```mermaid
sequenceDiagram
participant User as "User"
participant CLI as "pke apply"
participant Wiki as "wiki/"
participant Backups as "backups/"
participant Events as "events.jsonl"
User->>CLI : "pke apply <id>"
CLI->>Backups : backup target page
CLI->>Wiki : apply append-only patch
CLI->>Events : record apply event
CLI-->>User : success/failure
```

**Diagram sources**
- [scripts/pke.mjs](file://scripts/pke.mjs)
- [docs/prd.md](file://docs/prd.md)

**Section sources**
- [scripts/pke.mjs](file://scripts/pke.mjs)
- [docs/prd.md](file://docs/prd.md)

### Audit Trail System
- Proposal tracking: proposals are stored with full metadata and lifecycle status.
- Approval history: applied and rejected proposals are archived for review.
- Backup mechanisms: pre-apply backups are created and retained.
- Change reports: detailed reports record before/after hashes and qmd refresh outcomes.

```mermaid
classDiagram
class Proposal {
+string id
+string status
+string target_page
+string confidence
+object patch
+string appliedAt
+string rejectedAt
+object changeReport
}
class Backup {
+string path
+string originalContentHash
}
class ChangeReport {
+string target
+boolean changed
+string beforeSha256
+string afterSha256
+number operations
+object qmdRefresh
}
Proposal --> Backup : "references"
Proposal --> ChangeReport : "produces"
```

**Diagram sources**
- [scripts/pke.mjs](file://scripts/pke.mjs)
- [docs/prd.md](file://docs/prd.md)

**Section sources**
- [scripts/pke.mjs](file://scripts/pke.mjs)
- [docs/prd.md](file://docs/prd.md)

### Controlled Self-Improvement
- Retrieval tuning: proposals are generated to improve coverage for frequently queried topics.
- Compile strategy refinement: historical acceptance rates adjust confidence and ranking.
- Fast-path approval: high-confidence, safe proposals can be batch-applied.

```mermaid
flowchart TD
Start(["Analyze Events"]) --> Topics["Aggregate topics and signals"]
Topics --> Proposals["Generate retrieval tuning proposals"]
Proposals --> Acceptance["Compute acceptance rates"]
Acceptance --> Adjust["Adjust confidence by history"]
Adjust --> Rank["Rank candidates"]
Rank --> Batch["Batch-safe approval for high-confidence"]
Batch --> End(["Applied"])
```

**Diagram sources**
- [scripts/pke.mjs](file://scripts/pke.mjs)
- [docs/implementation-backlog.md](file://docs/implementation-backlog.md)

**Section sources**
- [scripts/pke.mjs](file://scripts/pke.mjs)
- [docs/implementation-backlog.md](file://docs/implementation-backlog.md)

### Examples of Safety Violations and Prevention
- Unauthorized wiki write without approval: prevented by governance gates enforcing proposal-only mode and requiring explicit apply.
- Silent pollution of knowledge: prevented by append-only patches and strict section targeting.
- Overload from excessive proposals: prevented by proposal caps, candidate queue limits, and daily proposal limits.
- Unbounded event growth: prevented by event log rotation and retention policies.
- Large file ingestion: prevented by skipping files larger than the configured maximum size.

**Section sources**
- [README.md](file://README.md)
- [docs/prd.md](file://docs/prd.md)
- [docs/implementation-backlog.md](file://docs/implementation-backlog.md)
- [scripts/pke.mjs](file://scripts/pke.mjs)

## Dependency Analysis
The CLI depends on state files and the qmd engine. The monitor depends on vault snapshots and emits events. Proposals depend on events and governance rules. Apply depends on backups and qmd refresh.

```mermaid
graph LR
CLI["scripts/pke.mjs"] --> STATE[".pke/state.json"]
CLI --> MONITORSTATE[".pke/monitor-state.json"]
CLI --> EVENTS[".pke/events.jsonl"]
CLI --> PROPOSALS[".pke/proposals/"]
CLI --> APPLIED[".pke/applied/"]
CLI --> REJECTED[".pke/rejected/"]
CLI --> BACKUPS[".pke/backups/"]
CLI --> QMD["qmd engine"]
CLI --> RAW["raw/"]
CLI --> WIKI["wiki/"]
```

**Diagram sources**
- [scripts/pke.mjs](file://scripts/pke.mjs)
- [docs/prd.md](file://docs/prd.md)

**Section sources**
- [scripts/pke.mjs](file://scripts/pke.mjs)
- [docs/prd.md](file://docs/prd.md)

## Performance Considerations
- File size limits reduce scan overhead and memory pressure.
- Event rotation and retention policies bound storage growth.
- Proposal caps and candidate queue limits bound memory and UI responsiveness.
- Batch-safe approval reduces manual overhead while preserving safety.

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
- Proposal not found: verify the proposal ID and directory.
- Target page missing: ensure the target wiki page exists before applying.
- Not pending: only pending proposals can be applied.
- Exceeded proposal cap: review or archive older proposals.
- Large file skipped: reduce file size or split content.

**Section sources**
- [scripts/pke.mjs](file://scripts/pke.mjs)
- [docs/implementation-backlog.md](file://docs/implementation-backlog.md)

## Conclusion
The PKE MVP implements a robust safety control system centered on governance gates, append-only validation, confidence thresholds, and comprehensive audit trails. Built-in safeguards manage scale and prevent unauthorized changes. Confidence-based mechanisms and controlled self-improvement enable gradual, safe enhancements while maintaining user control over wiki updates.