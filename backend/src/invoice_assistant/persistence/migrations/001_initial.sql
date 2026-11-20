CREATE TABLE IF NOT EXISTS workspace (
  id text PRIMARY KEY,
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS membership (
  workspace_id text NOT NULL REFERENCES workspace(id),
  user_id text NOT NULL,
  role text NOT NULL CHECK (role IN ('operator', 'reviewer', 'administrator')),
  PRIMARY KEY (workspace_id, user_id, role)
);

CREATE TABLE IF NOT EXISTS policy_version (
  workspace_id text NOT NULL REFERENCES workspace(id),
  version integer NOT NULL CHECK (version > 0),
  payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, version)
);

CREATE TABLE IF NOT EXISTS document (
  id text PRIMARY KEY,
  workspace_id text NOT NULL REFERENCES workspace(id),
  object_key text NOT NULL,
  original_name text NOT NULL,
  detected_type text NOT NULL,
  checksum text NOT NULL,
  byte_size bigint NOT NULL CHECK (byte_size > 0),
  status text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, id)
);

CREATE TABLE IF NOT EXISTS document_page (
  workspace_id text NOT NULL,
  document_id text NOT NULL,
  page integer NOT NULL CHECK (page > 0),
  status text NOT NULL,
  preview_key text,
  error_code text,
  PRIMARY KEY (workspace_id, document_id, page),
  FOREIGN KEY (workspace_id, document_id) REFERENCES document(workspace_id, id)
);

CREATE TABLE IF NOT EXISTS draft (
  id text PRIMARY KEY,
  workspace_id text NOT NULL REFERENCES workspace(id),
  document_id text NOT NULL,
  version integer NOT NULL DEFAULT 1 CHECK (version > 0),
  status text NOT NULL,
  fields jsonb NOT NULL,
  warnings jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (workspace_id, document_id) REFERENCES document(workspace_id, id),
  UNIQUE (workspace_id, id)
);

CREATE TABLE IF NOT EXISTS conversation_message (
  id text PRIMARY KEY,
  workspace_id text NOT NULL REFERENCES workspace(id),
  draft_id text NOT NULL,
  actor_id text NOT NULL,
  role text NOT NULL CHECK (role IN ('user', 'assistant')),
  body text NOT NULL,
  provenance text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (workspace_id, draft_id) REFERENCES draft(workspace_id, id)
);

CREATE TABLE IF NOT EXISTS workbook (
  id text PRIMARY KEY,
  workspace_id text NOT NULL REFERENCES workspace(id),
  name text NOT NULL,
  current_version integer NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, id)
);

CREATE TABLE IF NOT EXISTS workbook_version (
  workspace_id text NOT NULL,
  workbook_id text NOT NULL,
  version integer NOT NULL CHECK (version > 0),
  parent_version integer,
  object_key text NOT NULL,
  checksum text NOT NULL,
  status text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, workbook_id, version),
  FOREIGN KEY (workspace_id, workbook_id) REFERENCES workbook(workspace_id, id)
);

CREATE TABLE IF NOT EXISTS field_mapping (
  workspace_id text NOT NULL,
  workbook_id text NOT NULL,
  version integer NOT NULL CHECK (version > 0),
  worksheet text NOT NULL,
  header_signature text NOT NULL,
  mapping jsonb NOT NULL,
  PRIMARY KEY (workspace_id, workbook_id, version),
  FOREIGN KEY (workspace_id, workbook_id) REFERENCES workbook(workspace_id, id)
);

CREATE TABLE IF NOT EXISTS validation_run (
  id text PRIMARY KEY,
  workspace_id text NOT NULL,
  draft_id text NOT NULL,
  draft_version integer NOT NULL,
  policy_version integer NOT NULL,
  workbook_version integer,
  mapping_version integer,
  results jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (workspace_id, draft_id) REFERENCES draft(workspace_id, id)
);

CREATE TABLE IF NOT EXISTS review_decision (
  id text PRIMARY KEY,
  workspace_id text NOT NULL,
  draft_id text NOT NULL,
  reviewer_id text NOT NULL,
  action text NOT NULL CHECK (action IN ('confirm_record', 'reject', 'return_to_draft')),
  draft_version integer NOT NULL,
  policy_version integer NOT NULL,
  validation_id text REFERENCES validation_run(id),
  acknowledgement jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (workspace_id, draft_id) REFERENCES draft(workspace_id, id)
);

CREATE TABLE IF NOT EXISTS record_intent (
  id text PRIMARY KEY,
  workspace_id text NOT NULL,
  draft_id text NOT NULL,
  decision_id text NOT NULL REFERENCES review_decision(id),
  idempotency_key text NOT NULL,
  request_fingerprint text NOT NULL,
  expected_workbook_version integer NOT NULL,
  status text NOT NULL,
  candidate_key text,
  candidate_checksum text,
  record_reference text,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, idempotency_key),
  UNIQUE (decision_id),
  FOREIGN KEY (workspace_id, draft_id) REFERENCES draft(workspace_id, id)
);

CREATE TABLE IF NOT EXISTS recorded_invoice (
  id text PRIMARY KEY,
  workspace_id text NOT NULL,
  draft_id text NOT NULL,
  workbook_id text NOT NULL,
  workbook_version integer NOT NULL,
  worksheet text NOT NULL,
  row_reference text NOT NULL,
  normalized_vendor text,
  normalized_invoice_number text,
  amount numeric,
  currency text,
  invoice_date date,
  decision_id text NOT NULL UNIQUE REFERENCES review_decision(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (workspace_id, draft_id) REFERENCES draft(workspace_id, id),
  FOREIGN KEY (workspace_id, workbook_id, workbook_version) REFERENCES workbook_version(workspace_id, workbook_id, version)
);

CREATE TABLE IF NOT EXISTS audit_event (
  id text PRIMARY KEY,
  workspace_id text NOT NULL REFERENCES workspace(id),
  actor_id text NOT NULL,
  action text NOT NULL,
  resource_id text NOT NULL,
  details jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

DO $$
DECLARE table_name text;
BEGIN
  FOREACH table_name IN ARRAY ARRAY['document','draft','conversation_message','workbook','workbook_version','field_mapping','validation_run','review_decision','record_intent','recorded_invoice','audit_event','policy_version','membership','document_page'] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format('DROP POLICY IF EXISTS workspace_isolation ON %I', table_name);
    EXECUTE format('CREATE POLICY workspace_isolation ON %I USING (workspace_id = current_setting(''app.workspace_id'', true)) WITH CHECK (workspace_id = current_setting(''app.workspace_id'', true))', table_name);
  END LOOP;
END $$;
