BEGIN;

-- Create table facilities_logging
CREATE TABLE facilities.facilities_task_logging(
    log_id serial PRIMARY KEY,
    log_date timestamp NOT NULL DEFAULT now(),
    log_level character varying NOT NULL,
    "user" character varying NOT NULL,
    task character varying NOT NULL,
    comment character varying NOT NULL
  );

COMMENT ON TABLE facilities.facilities_task_logging IS 'Stores the log of the current task';

COMMENT ON COLUMN facilities.facilities_task_logging.log_id IS
'Unique identifier for the facilities log.';
COMMENT ON COLUMN facilities.facilities_task_logging.log_date IS
'Date of creation for the facilities log.';
COMMENT ON COLUMN facilities.facilities_task_logging.user IS
'User name for the person updating the facilities log.';
COMMENT ON COLUMN facilities.facilities_task_logging.task IS
'The main task during the facilities log, options are test dbconn, update temp facilities table, and update facilities table.';
COMMENT ON COLUMN facilities.facilities_task_logging.comment IS
'The log comment of the facilities log.';

COMMIT;