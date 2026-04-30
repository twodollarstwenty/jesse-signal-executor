CREATE TABLE IF NOT EXISTS signal_events (
  id BIGSERIAL PRIMARY KEY,
  instance_id TEXT NOT NULL DEFAULT 'dryrun',
  strategy TEXT NOT NULL,
  symbol TEXT NOT NULL,
  timeframe TEXT NOT NULL,
  signal_time TIMESTAMPTZ NOT NULL,
  action TEXT NOT NULL,
  signal_hash TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL,
  payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS signal_decision_events (
  id BIGSERIAL PRIMARY KEY,
  instance_id TEXT NOT NULL DEFAULT 'dryrun',
  strategy TEXT NOT NULL,
  symbol TEXT NOT NULL,
  timeframe TEXT NOT NULL,
  signal_time TIMESTAMPTZ NOT NULL,
  candle_timestamp BIGINT NOT NULL,
  decision_hash TEXT NOT NULL UNIQUE,
  intent TEXT NOT NULL,
  action TEXT NOT NULL,
  emitted BOOLEAN NOT NULL,
  decision_status TEXT NOT NULL,
  reason_code TEXT NOT NULL,
  payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS execution_events (
  id BIGSERIAL PRIMARY KEY,
  signal_id BIGINT NOT NULL REFERENCES signal_events(id) ON DELETE RESTRICT,
  instance_id TEXT NOT NULL DEFAULT 'dryrun',
  symbol TEXT NOT NULL,
  side TEXT NOT NULL,
  mode TEXT NOT NULL,
  status TEXT NOT NULL,
  detail_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS position_state (
  id BIGSERIAL PRIMARY KEY,
  instance_id TEXT NOT NULL DEFAULT 'dryrun',
  symbol TEXT NOT NULL,
  side TEXT,
  qty NUMERIC NOT NULL,
  entry_price NUMERIC,
  state_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE signal_events ADD COLUMN IF NOT EXISTS instance_id TEXT NOT NULL DEFAULT 'dryrun';
ALTER TABLE execution_events ADD COLUMN IF NOT EXISTS instance_id TEXT NOT NULL DEFAULT 'dryrun';
ALTER TABLE position_state ADD COLUMN IF NOT EXISTS instance_id TEXT NOT NULL DEFAULT 'dryrun';
