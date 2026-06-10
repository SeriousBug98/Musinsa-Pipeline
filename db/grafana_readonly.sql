-- Grafana 읽기전용 유저 생성 (idempotent — 여러 번 실행해도 안전)
-- 실행 방법:
--   docker compose exec -T postgres psql \
--     -U $DB_USER -d $DB_NAME \
--     -v grafana_password="$GRAFANA_DB_PASSWORD" \
--     < db/grafana_readonly.sql

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'grafana_ro') THEN
    CREATE ROLE grafana_ro LOGIN;
  END IF;
END $$;

ALTER ROLE grafana_ro PASSWORD :'grafana_password';

DO $$
BEGIN
  EXECUTE 'GRANT CONNECT ON DATABASE ' || current_database() || ' TO grafana_ro';
END $$;

GRANT USAGE ON SCHEMA public TO grafana_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO grafana_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO grafana_ro;
