-- sqlite_reports.sql
-- Звіти для локальної SQLite-бази (таблиця facts), створеної csv_to_sqlite.py
-- Поля: created_at, status, gateway_code, gateway_message, bin_country, ip_country, billing_country,
--       billing_zip, billing_city, billing_address, browser_language

-- 1) Daily metrics by BIN/Billing/IP
SELECT
  DATE(created_at) AS day_utc,
  'BIN' AS geo_source,
  bin_country AS geo,
  COUNT(*) AS attempts,
  SUM(CASE WHEN LOWER(status) IN ('approved','authorized','captured','success') THEN 1 ELSE 0 END) AS approved,
  ROUND(100.0 * SUM(CASE WHEN LOWER(status) IN ('approved','authorized','captured','success') THEN 1 ELSE 0 END) / COUNT(*), 2) AS ar_pct
FROM facts
WHERE bin_country IN ('AU','DE','IT','HU')
GROUP BY 1,2,3
UNION ALL
SELECT
  DATE(created_at) AS day_utc,
  'Billing' AS geo_source,
  billing_country AS geo,
  COUNT(*),
  SUM(CASE WHEN LOWER(status) IN ('approved','authorized','captured','success') THEN 1 ELSE 0 END),
  ROUND(100.0 * SUM(CASE WHEN LOWER(status) IN ('approved','authorized','captured','success') THEN 1 ELSE 0 END) / COUNT(*), 2)
FROM facts
WHERE billing_country IN ('AU','DE','IT','HU')
GROUP BY 1,2,3
UNION ALL
SELECT
  DATE(created_at) AS day_utc,
  'IP' AS geo_source,
  ip_country AS geo,
  COUNT(*),
  SUM(CASE WHEN LOWER(status) IN ('approved','authorized','captured','success') THEN 1 ELSE 0 END),
  ROUND(100.0 * SUM(CASE WHEN LOWER(status) IN ('approved','authorized','captured','success') THEN 1 ELSE 0 END) / COUNT(*), 2)
FROM facts
WHERE ip_country IN ('AU','DE','IT','HU')
GROUP BY 1,2,3
ORDER BY day_utc DESC, geo_source, geo;

-- 2) Weekly top declines by gateway_code + gateway_message (BIN geo)
WITH d AS (
  SELECT
    STRFTIME('%Y-%W', created_at) AS week,
    bin_country AS geo,
    gateway_code || ' | ' || IFNULL(gateway_message,'') AS code_msg,
    COUNT(*) AS declines
  FROM facts
  WHERE bin_country IN ('AU','DE','IT','HU')
    AND LOWER(status) NOT IN ('approved','authorized','captured','success')
  GROUP BY 1,2,3
),
tot AS (
  SELECT week, geo, SUM(declines) AS total_declines
  FROM d GROUP BY 1,2
)
SELECT d.week, d.geo, d.code_msg, d.declines,
       ROUND(100.0 * d.declines / NULLIF(t.total_declines,0), 2) AS share_pct
FROM d JOIN tot t ON t.week=d.week AND t.geo=d.geo
ORDER BY d.week DESC, d.geo, d.declines DESC
LIMIT 300;

-- 3) Data Quality summary
SELECT 'Missing BIN country' AS check, ROUND(100.0 * AVG(CASE WHEN bin_country IS NULL OR bin_country='' THEN 1 ELSE 0 END), 2) AS percent FROM facts
UNION ALL
SELECT 'Missing Billing country', ROUND(100.0 * AVG(CASE WHEN billing_country IS NULL OR billing_country='' THEN 1 ELSE 0 END), 2) FROM facts
UNION ALL
SELECT 'Missing IP country', ROUND(100.0 * AVG(CASE WHEN ip_country IS NULL OR ip_country='' THEN 1 ELSE 0 END), 2) FROM facts
UNION ALL
SELECT 'Missing Billing ZIP', ROUND(100.0 * AVG(CASE WHEN billing_zip IS NULL OR billing_zip='' THEN 1 ELSE 0 END), 2) FROM facts
UNION ALL
SELECT 'Missing Billing City', ROUND(100.0 * AVG(CASE WHEN billing_city IS NULL OR billing_city='' THEN 1 ELSE 0 END), 2) FROM facts
UNION ALL
SELECT 'Missing Billing Address', ROUND(100.0 * AVG(CASE WHEN billing_address IS NULL OR billing_address='' THEN 1 ELSE 0 END), 2) FROM facts
UNION ALL
SELECT 'Missing Browser Language', ROUND(100.0 * AVG(CASE WHEN browser_language IS NULL OR browser_language='' THEN 1 ELSE 0 END), 2) FROM facts;

-- 4) Gateway code consistency (one code -> many messages)
SELECT gateway_code, COUNT(DISTINCT COALESCE(gateway_message,'')) AS distinct_messages,
       COUNT(*) AS declines
FROM facts
WHERE LOWER(status) NOT IN ('approved','authorized','captured','success')
GROUP BY gateway_code
ORDER BY distinct_messages DESC, declines DESC
LIMIT 100;
