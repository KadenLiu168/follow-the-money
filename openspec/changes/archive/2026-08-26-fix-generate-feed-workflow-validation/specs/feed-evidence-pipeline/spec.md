## ADDED Requirements

### Requirement: Feed deployment workflow acceptance includes Actions semantics
The accepted Feed deployment workflow SHALL be valid under GitHub Actions workflow-definition and expression/context semantics. The authoritative pre-merge path SHALL evaluate the repository's real workflows with an established Actions-aware validator in addition to the repository-specific Feed deployment invariant checks. Dedicated Feed runner selection SHALL remain scheduler-enforced through the job's `runs-on` labels, without depending on an unavailable workflow-level context or a redundant runtime label guard.

#### Scenario: Accepted Feed deployment workflow
- **WHEN** the repository's real GitHub Actions workflows are evaluated by the authoritative Actions-aware validator
- **THEN** they pass workflow-definition and expression/context validation while the existing project-specific Feed workflow invariants also pass

#### Scenario: Unavailable context is used
- **WHEN** a workflow uses a GitHub Actions context at a workflow key where that context is unavailable
- **THEN** authoritative pre-merge workflow validation fails and the invalid workflow cannot satisfy repository acceptance

#### Scenario: Dedicated Feed runner is selected
- **WHEN** GitHub Actions schedules an opted-in Feed generation job
- **THEN** the job is eligible only for a self-hosted runner matching `follow-the-money-feed`, and non-matching runners are excluded by `runs-on` scheduling rather than rejected by a later runtime label check
