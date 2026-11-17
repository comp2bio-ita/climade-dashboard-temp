-- Manual schema change for existing databases.
-- create_db_schema.py only creates missing tables; it does not ALTER existing ones.

ALTER TABLE ncbi_sequence_data
  ADD COLUMN location_normalized VARCHAR(100) NULL AFTER location;
