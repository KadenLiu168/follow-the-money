# Filing Presentation Contract

## Domain Purpose

Present validated `filing` evidence as a typed SEC filing record with its form,
issuer or company identity, filing and acceptance provenance, subtype-specific
holdings or ownership facts, typed comparisons, amendment state, and stated
limitations. One filing contract owns all filing subtypes. The list below is a
closed whitelist; it does not authorize facts outside the listed paths.

## Evidence Fields

The closed common whitelist for a `filing` item is:

- `id`
- `provider_id`
- `source.id`
- `source.name`
- `source.tier`
- `source.kind`
- `source.url`
- `source.published_at`
- `source.updated_at`
- `source.knowledge_available_at`
- `source.original_publisher`
- `source.syndication_origin`
- `source_lineage[].id`
- `source_lineage[].provider_id`
- `source_lineage[].source_id`
- `source_lineage[].original_publisher`
- `source_lineage[].syndication_origin`
- `payload.type`
- `payload.filing_subtype`
- `payload.form`
- `payload.company`
- `payload.accession_number`
- `payload.filed_at`
- `payload.company_identity.cik`
- `payload.company_identity.name`
- `payload.company_identity.tickers[]`
- `payload.report_period`
- `payload.accepted_at`
- `payload.value_normalization.source_unit`
- `payload.value_normalization.formula_id`
- `payload.document_url`
- `payload.is_amendment`
- `payload.amendment_number`

For `filing_subtype = form13f`, the additional closed whitelist is:

- `payload.comparison.status`
- `payload.comparison.previous_accession_number`
- `payload.comparison.previous_report_period`
- `payload.comparison.previous_accepted_at`
- `payload.comparison.previous_filed_at`
- `payload.comparison.previous_source_url`
- `payload.comparison.previous_value_normalization.source_unit`
- `payload.comparison.previous_value_normalization.formula_id`
- `payload.comparison.reason`
- `payload.holdings[].security.cusip`
- `payload.holdings[].security.figi`
- `payload.holdings[].security.issuer_name`
- `payload.holdings[].security.title_of_class`
- `payload.holdings[].security.put_call`
- `payload.holdings[].security.amount_type`
- `payload.holdings[].current.reported_amount.value`
- `payload.holdings[].current.reported_amount.unit`
- `payload.holdings[].current.reported_amount.unknown_reason`
- `payload.holdings[].current.reported_value_usd_thousands.value`
- `payload.holdings[].current.reported_value_usd_thousands.unit`
- `payload.holdings[].current.reported_value_usd_thousands.unknown_reason`
- `payload.holdings[].previous.reported_amount.value`
- `payload.holdings[].previous.reported_amount.unit`
- `payload.holdings[].previous.reported_amount.unknown_reason`
- `payload.holdings[].previous.reported_value_usd_thousands.value`
- `payload.holdings[].previous.reported_value_usd_thousands.unit`
- `payload.holdings[].previous.reported_value_usd_thousands.unknown_reason`
- `payload.holdings[].delta.reported_amount.value`
- `payload.holdings[].delta.reported_amount.unit`
- `payload.holdings[].delta.reported_amount.unknown_reason`
- `payload.holdings[].delta.reported_value_usd_thousands.value`
- `payload.holdings[].delta.reported_value_usd_thousands.unit`
- `payload.holdings[].delta.reported_value_usd_thousands.unknown_reason`
- `payload.holdings[].change_type`

For `filing_subtype = form4`, the additional closed whitelist is:

- `payload.issuer.cik`
- `payload.issuer.name`
- `payload.issuer.trading_symbol`
- `payload.reporting_owners[].cik`
- `payload.reporting_owners[].name`
- `payload.reporting_owners[].relationship.director`
- `payload.reporting_owners[].relationship.officer`
- `payload.reporting_owners[].relationship.ten_percent_owner`
- `payload.reporting_owners[].relationship.other`
- `payload.reporting_owners[].relationship.officer_title`
- `payload.reporting_owners[].relationship.other_text`
- `payload.non_derivative_entries[]` and `payload.derivative_entries[]` entry paths:
  `entry_kind`, `source_ordinal`, `entry_id`, `security_title`,
  `post_transaction_amount`, `ownership_nature`, `derivative_terms`,
  `underlying_security`, and `field_references[]`
- `payload.non_derivative_entries[]` and `payload.derivative_entries[]` transaction-only paths:
  `transaction_date`, `deemed_execution_date`, `transaction_coding`,
  `timeliness`, `transaction_amount`, `price_per_share`, and
  `acquisition_disposition_code`
- `payload.footnotes[].id`
- `payload.footnotes[].text`
- `payload.remarks`
- `payload.date_of_original_submission`
- `payload.non_derivative_entries[].entry_kind`
- `payload.non_derivative_entries[].source_ordinal`
- `payload.non_derivative_entries[].entry_id`
- `payload.non_derivative_entries[].security_title`
- `payload.non_derivative_entries[].transaction_date`
- `payload.non_derivative_entries[].deemed_execution_date`
- `payload.non_derivative_entries[].transaction_coding.transaction_form_type`
- `payload.non_derivative_entries[].transaction_coding.transaction_code`
- `payload.non_derivative_entries[].transaction_coding.equity_swap_involved`
- `payload.non_derivative_entries[].timeliness`
- `payload.non_derivative_entries[].transaction_amount`
- `payload.non_derivative_entries[].price_per_share`
- `payload.non_derivative_entries[].acquisition_disposition_code`
- `payload.non_derivative_entries[].post_transaction_amount`
- `payload.non_derivative_entries[].ownership_nature.direct_or_indirect`
- `payload.non_derivative_entries[].ownership_nature.nature_of_ownership`
- `payload.non_derivative_entries[].derivative_terms`
- `payload.non_derivative_entries[].underlying_security`
- `payload.non_derivative_entries[].field_references[]`
- the same entry paths under `payload.derivative_entries[]`

For each Form 4 numeric object, present only its typed `value`, `unit`, and
`footnote_ids` when present. Preserve field-reference and footnote links.

For `filing_subtype = beneficial_ownership`, the additional closed whitelist is:

- `payload.schedule_family`
- `payload.current_snapshot.accession_number`
- `payload.current_snapshot.form`
- `payload.current_snapshot.schedule_family`
- `payload.current_snapshot.filed_at`
- `payload.current_snapshot.accepted_at`
- `payload.current_snapshot.document_url`
- `payload.current_snapshot.issuer.cik`
- `payload.current_snapshot.issuer.name`
- `payload.current_snapshot.ownership_class.cusip`
- `payload.current_snapshot.ownership_class.title`
- `payload.current_snapshot.ownership_class.identity_basis`
- `payload.current_snapshot.reporting_positions[]` and its position paths below
- `payload.current_snapshot.group_evidence`
- `payload.current_snapshot.is_amendment`
- `payload.current_snapshot.amendment_number`
- `payload.previous_snapshot.accession_number` (when present)
- `payload.previous_snapshot.form` (when present)
- `payload.previous_snapshot.schedule_family` (when present)
- `payload.previous_snapshot.filed_at` (when present)
- `payload.previous_snapshot.accepted_at` (when present)
- `payload.previous_snapshot.document_url` (when present)
- `payload.previous_snapshot.issuer.cik` (when present)
- `payload.previous_snapshot.issuer.name` (when present)
- `payload.previous_snapshot.ownership_class.cusip` (when present)
- `payload.previous_snapshot.ownership_class.title` (when present)
- `payload.previous_snapshot.ownership_class.identity_basis` (when present)
- `payload.previous_snapshot.reporting_positions[]` (when present)
- `payload.previous_snapshot.group_evidence` (when present)
- `payload.previous_snapshot.is_amendment` (when present)
- `payload.previous_snapshot.amendment_number` (when present)
- `payload.comparison.status`
- `payload.comparison.reason`
- `payload.comparison.previous.accession_number`
- `payload.comparison.previous.accepted_at`
- `payload.comparison.previous.document_url`
- `payload.current_snapshot.reporting_positions[].source_ordinal`
- `payload.current_snapshot.reporting_positions[].source_name`
- `payload.current_snapshot.reporting_positions[].source_cik`
- `payload.current_snapshot.reporting_positions[].identity_basis`
- `payload.current_snapshot.reporting_positions[].person_types[]`
- `payload.current_snapshot.reporting_positions[].group_membership.is_member`
- `payload.current_snapshot.reporting_positions[].beneficially_owned_shares.status`
- `payload.current_snapshot.reporting_positions[].beneficially_owned_shares.value`
- `payload.current_snapshot.reporting_positions[].beneficially_owned_shares.unit`
- `payload.current_snapshot.reporting_positions[].beneficially_owned_shares.reason`
- `payload.current_snapshot.reporting_positions[].beneficially_owned_shares.source_field_refs[]`
- `payload.current_snapshot.reporting_positions[].beneficially_owned_shares.derivation`
- `payload.current_snapshot.reporting_positions[].ownership_percentage.status`
- `payload.current_snapshot.reporting_positions[].ownership_percentage.value`
- `payload.current_snapshot.reporting_positions[].ownership_percentage.unit`
- `payload.current_snapshot.reporting_positions[].ownership_percentage.reason`
- `payload.current_snapshot.reporting_positions[].ownership_percentage.source_field_refs[]`
- `payload.current_snapshot.reporting_positions[].ownership_percentage.derivation`
- `payload.current_snapshot.reporting_positions[].voting_power.status`
- `payload.current_snapshot.reporting_positions[].voting_power.value`
- `payload.current_snapshot.reporting_positions[].voting_power.unit`
- `payload.current_snapshot.reporting_positions[].voting_power.reason`
- `payload.current_snapshot.reporting_positions[].voting_power.source_field_refs[]`
- `payload.current_snapshot.reporting_positions[].voting_power.derivation`
- `payload.current_snapshot.reporting_positions[].dispositive_power.status`
- `payload.current_snapshot.reporting_positions[].dispositive_power.value`
- `payload.current_snapshot.reporting_positions[].dispositive_power.unit`
- `payload.current_snapshot.reporting_positions[].dispositive_power.reason`
- `payload.current_snapshot.reporting_positions[].dispositive_power.source_field_refs[]`
- `payload.current_snapshot.reporting_positions[].dispositive_power.derivation`
- `payload.current_snapshot.reporting_positions[].source_field_refs[]`
- `payload.current_snapshot.reporting_positions[].comparison.status`
- `payload.current_snapshot.reporting_positions[].comparison.reason`
- `payload.current_snapshot.reporting_positions[].comparison.shares_delta`
- `payload.current_snapshot.reporting_positions[].comparison.percentage_delta`

For beneficial-ownership numeric objects, preserve `status`, `value`, `unit`,
`reason`, `source_field_refs`, and the explicit `derivation` when present.

Filing does not carry `semantic_context`.

## Recommended Representation

Identify the filing and its source, form, subtype, company or issuer, accession
number, filed/accepted times, and document URL when present. For Form 13F,
represent typed current, previous, delta, change, security identity, value
normalization, and comparison evidence without converting it into a portfolio
judgment. For Form 4, preserve reporting-owner relationships, transaction or
holding entries, acquisition/disposition code, post-transaction state,
derivative terms, footnotes, and amendment facts as reported. For beneficial
ownership, preserve schedule family, issuer/class identity, source-ordered
positions, ownership facts, source references, comparison status, and
amendment facts. State unavailable comparison, numeric, holding, transaction,
or ownership values as unavailable when the Feed says so.

Null, explicitly unavailable, absent, or legacy-omitted evidence remains
missing. Do not reconstruct or infer a holding, transaction, owner, amendment,
comparison, identity, or ownership value from a title, company name, another
filing, historical Feed, external knowledge, or `raw_metadata`. Do not perform
an unstated calculation.

## Forbidden Interpretation

Do not add importance, anomaly, ranking, causality, sentiment, direction,
market impact, signal, prediction, investment judgment, recommendation, or
trading instruction. Do not translate a filing, holding, transaction,
ownership percentage, comparison, amendment, or source-authored statement into
intent, conviction, control, valuation, market meaning, or a trading conclusion.
Do not upgrade source limitations or typed comparison states. `raw_metadata`
and every unlisted field are outside the presentation evidence. Source-authored
analysis may be summarized only with clear attribution and without upgrading
its authority.
