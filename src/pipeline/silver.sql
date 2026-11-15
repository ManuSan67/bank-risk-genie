CREATE OR REFRESH MATERIALIZED VIEW silver.customers (
  CONSTRAINT valid_id EXPECT (customer_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_rfc EXPECT (length(rfc) = 13),
  CONSTRAINT valid_curp EXPECT (length(curp) = 18),
  CONSTRAINT positive_income EXPECT (monthly_income > 0)
)
AS SELECT
  customer_id,
  full_name,
  rfc,
  curp,
  CAST(birth_date AS DATE) AS birth_date,
  sex,
  state,
  segment,
  CAST(monthly_income AS DECIMAL(12,2)) AS monthly_income,
  CAST(customer_since AS DATE) AS customer_since
FROM bronze.customers;

CREATE OR REFRESH MATERIALIZED VIEW silver.accounts (
  CONSTRAINT valid_id EXPECT (account_id IS NOT NULL AND customer_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_clabe EXPECT (length(clabe) = 18)
)
AS SELECT
  account_id,
  customer_id,
  lpad(CAST(clabe AS STRING), 18, '0') AS clabe,
  product,
  CAST(opened_at AS DATE) AS opened_at
FROM bronze.accounts;

CREATE OR REFRESH MATERIALIZED VIEW silver.loans (
  CONSTRAINT valid_id EXPECT (loan_id IS NOT NULL AND customer_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT positive_amount EXPECT (amount > 0),
  CONSTRAINT valid_grade EXPECT (risk_grade IN ('A', 'B', 'C', 'D', 'E'))
)
AS SELECT
  loan_id,
  customer_id,
  product,
  risk_grade,
  CAST(amount AS DECIMAL(14,2)) AS amount,
  CAST(annual_rate AS DECIMAL(5,4)) AS annual_rate,
  CAST(term_months AS INT) AS term_months,
  CAST(origination_date AS DATE) AS origination_date
FROM bronze.loans;

CREATE OR REFRESH MATERIALIZED VIEW silver.loan_months (
  CONSTRAINT valid_key EXPECT (loan_id IS NOT NULL AND period_end IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT non_negative_balance EXPECT (balance >= 0),
  CONSTRAINT valid_dpd EXPECT (days_past_due >= 0),
  CONSTRAINT valid_status EXPECT (status IN ('vigente', 'vencido', 'castigado', 'liquidado'))
)
AS SELECT
  loan_id,
  CAST(period_end AS DATE) AS period_end,
  CAST(balance AS DECIMAL(14,2)) AS balance,
  CAST(amount_due AS DECIMAL(14,2)) AS amount_due,
  CAST(amount_paid AS DECIMAL(14,2)) AS amount_paid,
  CAST(days_past_due AS INT) AS days_past_due,
  status
FROM bronze.loan_months;

CREATE OR REFRESH MATERIALIZED VIEW silver.transfers (
  CONSTRAINT valid_id EXPECT (transfer_id IS NOT NULL AND account_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT positive_amount EXPECT (amount > 0) ON VIOLATION DROP ROW,
  CONSTRAINT valid_dest_clabe EXPECT (length(dest_clabe) = 18)
)
AS SELECT
  transfer_id,
  account_id,
  CAST(ts AS TIMESTAMP) AS transfer_ts,
  CAST(ts AS DATE) AS transfer_date,
  CAST(amount AS DECIMAL(14,2)) AS amount,
  channel,
  CAST(new_beneficiary AS BOOLEAN) AS new_beneficiary,
  CAST(new_device AS BOOLEAN) AS new_device,
  lpad(CAST(dest_bank AS STRING), 3, '0') AS dest_bank,
  lpad(CAST(dest_clabe AS STRING), 18, '0') AS dest_clabe
FROM bronze.transfers;

CREATE OR REFRESH MATERIALIZED VIEW silver.alerts (
  CONSTRAINT valid_id EXPECT (alert_id IS NOT NULL AND transfer_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_status EXPECT (status IN ('abierta', 'cerrada')),
  CONSTRAINT closed_has_resolution EXPECT (status = 'abierta' OR resolution IS NOT NULL)
)
AS SELECT
  alert_id,
  transfer_id,
  rule_code,
  CAST(created_at AS TIMESTAMP) AS created_at,
  analyst,
  status,
  resolution,
  CAST(closed_at AS TIMESTAMP) AS closed_at,
  round((unix_timestamp(CAST(closed_at AS TIMESTAMP)) - unix_timestamp(CAST(created_at AS TIMESTAMP))) / 3600, 2) AS hours_to_close,
  CAST(recovered_amount AS DECIMAL(14,2)) AS recovered_amount
FROM bronze.alerts;