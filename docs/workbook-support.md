# XLSX support matrix (prototype)

This prototype intentionally supports a conservative subset and is not certified against arbitrary vendor workbooks.

## Currently handled

- `.xlsx` ZIP/OOXML package with bounded entry count, uncompressed size, compression ratio, and no encrypted parts.
- One or more ordinary worksheets; first row is treated as headers and mappings use one-based column indexes.
- Basic cell values, formulas preserved when untouched, and appended mapped rows.
- Invoice-derived text is serialized as explicit string cells to avoid interpreting `=`-prefixed content as formulas.
- Uploaded original is retained as an application snapshot; downloadable result is a separate copy.

## Rejected or not guaranteed

- Macro-enabled `.xlsm`, signatures, encrypted files, ActiveX/embedded objects, drawings/shapes, external links, rich text, unsupported OOXML parts, and complex workbook features not covered by current tests.
- Formula calculation/recalculation, dependent formula ranges, table expansion, validation-rule enforcement, merged destination cells, advanced style fidelity, or print-layout fidelity.
- Concurrent edits outside the application's snapshot flow or changes to the user's local original after upload.

## Release requirement

Build an approved representative workbook corpus; test open/save/reopen in supported spreadsheet clients; review all warnings and the OOXML allowlist with AP and security owners before real invoices are used. Do not claim general workbook preservation beyond tested fixtures.
