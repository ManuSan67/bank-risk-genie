CREATE OR REFRESH STREAMING TABLE bronze.customers
AS SELECT *, _metadata.file_path AS source_file, current_timestamp() AS ingested_at
FROM STREAM read_files('/Volumes/${catalog}/bronze/landing/customers/', format => 'csv', header => true);

CREATE OR REFRESH STREAMING TABLE bronze.accounts
AS SELECT *, _metadata.file_path AS source_file, current_timestamp() AS ingested_at
FROM STREAM read_files('/Volumes/${catalog}/bronze/landing/accounts/', format => 'csv', header => true);

CREATE OR REFRESH STREAMING TABLE bronze.loans
AS SELECT *, _metadata.file_path AS source_file, current_timestamp() AS ingested_at
FROM STREAM read_files('/Volumes/${catalog}/bronze/landing/loans/', format => 'csv', header => true);

CREATE OR REFRESH STREAMING TABLE bronze.loan_months
AS SELECT *, _metadata.file_path AS source_file, current_timestamp() AS ingested_at
FROM STREAM read_files('/Volumes/${catalog}/bronze/landing/loan_months/', format => 'csv', header => true);

CREATE OR REFRESH STREAMING TABLE bronze.transfers
AS SELECT *, _metadata.file_path AS source_file, current_timestamp() AS ingested_at
FROM STREAM read_files('/Volumes/${catalog}/bronze/landing/transfers/', format => 'csv', header => true);

CREATE OR REFRESH STREAMING TABLE bronze.alerts
AS SELECT *, _metadata.file_path AS source_file, current_timestamp() AS ingested_at
FROM STREAM read_files('/Volumes/${catalog}/bronze/landing/alerts/', format => 'csv', header => true);