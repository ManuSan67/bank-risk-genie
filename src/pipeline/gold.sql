CREATE OR REFRESH MATERIALIZED VIEW gold.dim_date
COMMENT 'Calendario diario de nov-2024 a oct-2026'
AS SELECT
  d AS calendar_date,
  year(d) AS year,
  quarter(d) AS quarter,
  month(d) AS month,
  element_at(array('enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
                   'septiembre', 'octubre', 'noviembre', 'diciembre'), month(d)) AS month_name,
  date_format(d, 'yyyy-MM') AS year_month,
  last_day(d) AS month_end,
  dayofweek(d) IN (1, 7) AS is_weekend
FROM (SELECT explode(sequence(DATE'2024-11-01', DATE'2026-10-31', INTERVAL 1 DAY)) AS d);

CREATE OR REFRESH MATERIALIZED VIEW gold.dim_customer (
  customer_id STRING,
  full_name STRING MASK ${catalog}.governance.mask_name,
  rfc STRING MASK ${catalog}.governance.mask_pii,
  curp STRING MASK ${catalog}.governance.mask_pii,
  birth_date DATE,
  age_band STRING,
  sex STRING,
  state STRING,
  segment STRING,
  monthly_income DECIMAL(12,2),
  income_band STRING,
  customer_since DATE
)
COMMENT 'Clientes del banco con segmento, estado y rangos de edad e ingreso. Nombre, RFC y CURP enmascarados salvo para risk_team'
AS SELECT
  customer_id,
  full_name,
  rfc,
  curp,
  birth_date,
  CASE
    WHEN floor(months_between(DATE'2026-10-31', birth_date) / 12) < 30 THEN '18-29'
    WHEN floor(months_between(DATE'2026-10-31', birth_date) / 12) < 45 THEN '30-44'
    WHEN floor(months_between(DATE'2026-10-31', birth_date) / 12) < 60 THEN '45-59'
    ELSE '60+'
  END AS age_band,
  sex,
  state,
  segment,
  monthly_income,
  CASE
    WHEN monthly_income < 15000 THEN 'menos de 15k'
    WHEN monthly_income <= 40000 THEN '15k a 40k'
    ELSE 'más de 40k'
  END AS income_band,
  customer_since
FROM silver.customers;

CREATE OR REFRESH MATERIALIZED VIEW gold.dim_account (
  account_id STRING,
  customer_id STRING,
  clabe STRING MASK ${catalog}.governance.mask_pii,
  product STRING,
  opened_at DATE
)
COMMENT 'Cuentas de depósito de los clientes. CLABE enmascarada salvo para risk_team'
AS SELECT account_id, customer_id, clabe, product, opened_at
FROM silver.accounts;

CREATE OR REFRESH MATERIALIZED VIEW gold.dim_loan
COMMENT 'Créditos otorgados: tarjeta, personal y nómina, con calificación de riesgo A a E'
AS SELECT
  loan_id,
  customer_id,
  product,
  risk_grade,
  amount,
  annual_rate,
  term_months,
  origination_date,
  date_format(origination_date, 'yyyy-MM') AS origination_month
FROM silver.loans;

CREATE OR REFRESH MATERIALIZED VIEW gold.dim_rule
COMMENT 'Reglas del motor de alertas de fraude y PLD'
AS SELECT * FROM VALUES
  ('R01_MONTO_ALTO', 'Monto alto', 'PLD', 'Transferencia de 50,000 pesos o más'),
  ('R02_BENEF_DISPOSITIVO_NUEVO', 'Beneficiario y dispositivo nuevos', 'Fraude', 'Primer envío a un beneficiario desde un dispositivo no reconocido'),
  ('R03_NOCTURNO', 'Operación nocturna', 'Fraude', 'Transferencia de 10,000 pesos o más entre las 0:00 y las 5:59'),
  ('R04_FRACCIONAMIENTO', 'Fraccionamiento', 'PLD', 'Tres o más transferencias entre 40,000 y 50,000 pesos en el mismo mes'),
  ('R05_MONTO_VS_INGRESO', 'Monto contra ingreso', 'PLD', 'Transferencia mayor a tres veces el ingreso mensual del cliente')
AS t(rule_code, rule_name, rule_type, rule_description);

CREATE OR REFRESH MATERIALIZED VIEW gold.dim_bank
COMMENT 'Bancos destino de las transferencias SPEI'
AS SELECT * FROM VALUES
  ('002', 'Banamex'),
  ('012', 'BBVA México'),
  ('014', 'Santander'),
  ('021', 'HSBC'),
  ('072', 'Banorte'),
  ('127', 'Banco Azteca'),
  ('137', 'BanCoppel'),
  ('638', 'Nu México'),
  ('999', 'Banco propio')
AS t(bank_code, bank_name);

CREATE OR REFRESH MATERIALIZED VIEW gold.fact_loan_month
COMMENT 'Foto mensual de cada crédito: saldo, pago, días de atraso y estatus. Cartera vencida = estatus vencido (90+ días)'
AS SELECT
  lm.loan_id,
  l.customer_id,
  lm.period_end,
  lm.balance,
  lm.amount_due,
  lm.amount_paid,
  lm.days_past_due,
  CASE
    WHEN lm.days_past_due = 0 THEN '0'
    WHEN lm.days_past_due < 60 THEN '30-59'
    WHEN lm.days_past_due < 90 THEN '60-89'
    ELSE '90+'
  END AS dpd_bucket,
  lm.status,
  lm.status = 'vencido' AS is_past_due
FROM silver.loan_months lm
JOIN silver.loans l ON lm.loan_id = l.loan_id;

CREATE OR REFRESH MATERIALIZED VIEW gold.fact_transfer
COMMENT 'Transferencias SPEI enviadas, con bandera de alerta y de fraude confirmado'
AS SELECT
  t.transfer_id,
  t.account_id,
  a.customer_id,
  t.transfer_date,
  t.transfer_ts,
  hour(t.transfer_ts) AS transfer_hour,
  t.amount,
  t.channel,
  t.new_beneficiary,
  t.new_device,
  t.dest_bank,
  al.alert_id IS NOT NULL AS has_alert,
  coalesce(al.resolution = 'fraude_confirmado', false) AS is_confirmed_fraud
FROM silver.transfers t
JOIN silver.accounts a ON t.account_id = a.account_id
LEFT JOIN silver.alerts al ON t.transfer_id = al.transfer_id;

CREATE OR REFRESH MATERIALIZED VIEW gold.fact_alert (
  alert_id STRING,
  transfer_id STRING,
  account_id STRING,
  customer_id STRING,
  rule_code STRING,
  created_date DATE,
  created_at TIMESTAMP,
  analyst STRING,
  status STRING,
  resolution STRING,
  closed_at TIMESTAMP,
  hours_to_close DOUBLE,
  transfer_amount DECIMAL(14,2),
  recovered_amount DECIMAL(14,2),
  is_false_positive BOOLEAN,
  is_confirmed_fraud BOOLEAN,
  is_pld_report BOOLEAN
)
COMMENT 'Alertas generadas por las reglas, con analista, resolución, tiempo de atención y monto recuperado. Las alertas PLD solo las ve risk_team'
WITH ROW FILTER ${catalog}.governance.alert_filter ON (rule_code)
AS SELECT
  al.alert_id,
  al.transfer_id,
  t.account_id,
  a.customer_id,
  al.rule_code,
  CAST(al.created_at AS DATE) AS created_date,
  al.created_at,
  al.analyst,
  al.status,
  al.resolution,
  al.closed_at,
  CAST(al.hours_to_close AS DOUBLE) AS hours_to_close,
  t.amount AS transfer_amount,
  al.recovered_amount,
  coalesce(al.resolution = 'falso_positivo', false) AS is_false_positive,
  coalesce(al.resolution = 'fraude_confirmado', false) AS is_confirmed_fraud,
  coalesce(al.resolution = 'reporte_pld', false) AS is_pld_report
FROM silver.alerts al
JOIN silver.transfers t ON al.transfer_id = t.transfer_id
JOIN silver.accounts a ON t.account_id = a.account_id;