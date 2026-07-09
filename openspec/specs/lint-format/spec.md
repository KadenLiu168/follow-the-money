# lint-format Specification

## Purpose
TBD - created by archiving change lint-format-tooling. Update Purpose after archive.
## Requirements
### Requirement: repository provides ESLint configuration and lint script
The repository SHALL include an ESLint flat config (`eslint.config.js`) and an npm script `lint` (`eslint .`) that lints all first-party JavaScript and JSON source. The config SHALL be based on `eslint:recommended` and SHALL disable rules that conflict with Prettier via `eslint-config-prettier`, so Prettier remains the sole authority on formatting. Linting MUST NOT require network access or a build step.

#### Scenario: lint runs in a clean checkout
- **WHEN** a developer runs `npm run lint` in a clean checkout
- **THEN** ESLint evaluates all first-party source and exits non-zero if any violation is found, without needing network or a build

#### Scenario: intentional disables are explicit
- **WHEN** a source file contains an `eslint-disable` comment
- **THEN** ESLint honors the disable for the scoped rule(s), and the comment documents the intent (not a blanket suppress-all)

### Requirement: repository provides Prettier configuration and format scripts
The repository SHALL include a Prettier config (`.prettierrc`) and npm scripts `format` (`prettier --write .`) and `format:check` (`prettier --check .`). Prettier SHALL be the sole authority on formatting (indentation, quotes, line width, trailing commas).

#### Scenario: format rewrites files
- **WHEN** a developer runs `npm run format`
- **THEN** all first-party source files are rewritten to the project's Prettier rules and the command exits 0

#### Scenario: format:check gates unformatted files
- **WHEN** a developer runs `npm run format:check` on a repo containing unformatted files
- **THEN** Prettier exits non-zero and lists the offending files (suitable as a CI gate)

### Requirement: repository pins Node version via .nvmrc
The repository SHALL include a `.nvmrc` file pinning a Node major version (e.g. `22`) that satisfies `package.json` `engines.node` (`>=20.19.0`). Running `nvm use` at the repo root SHALL select that version.

#### Scenario: nvm selects pinned version
- **WHEN** a developer runs `nvm use` at the repo root
- **THEN** the resolved Node version matches the pinned major and satisfies `engines.node >=20.19.0`

