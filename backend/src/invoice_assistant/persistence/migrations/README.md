# Database migrations

`001_initial.sql` declares workspace-scoped entities and row-level security policies. Apply only to a disposable local database until security review is complete. Production migration execution, migration version tracking, least-privilege roles, and an RLS bypass audit are not implemented yet. The app role must not own protected tables or have `BYPASSRLS`; migrations should run under a separate owner role. Review policy behavior with connection pooling and reset the transaction-local workspace context on every checkout/return.
