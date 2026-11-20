# Synthetic validation evaluation

`python scripts/evaluate_invoice_quality.py path/to/synthetic-cases.json` runs the deterministic field/total/duplicate rules and compares them with each case's expected outcomes.

The JSON file is a list of objects with `case_id`, `fields` (invoice field objects containing `value`), optional `existing_records`, and `expected` (check name to expected status). Use synthetic or approved consented data only. This runner does not measure OCR/model extraction accuracy, AP handling time, or user satisfaction; those require an approved labeled dataset and evaluation procedure before production.
