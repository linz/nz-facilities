BEGIN;

-- Create table facilities_task_logging
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


-- Create table facilities_result_logging
CREATE TABLE facilities.facilities_result_logging(
    log_id serial PRIMARY KEY,
    log_date timestamp NOT NULL DEFAULT now(),
    "user" character varying NOT NULL,
    added integer DEFAULT 0,
    removed integer DEFAULT 0,
    geom_updated integer DEFAULT 0,
    attr_updated integer DEFAULT 0,
    geom_attr_updated integer DEFAULT 0,
    unchanged integer DEFAULT 0,
    row_count_before integer DEFAULT 0,
    row_count_after integer DEFAULT 0,
);

COMMENT ON TABLE facilities.facilities_result_logging IS 'Stores the log of the results of the update facilities table';

COMMENT ON COLUMN facilities.facilities_result_logging.log_id IS
'Unique identifier for the facilities log.';
COMMENT ON COLUMN facilities.facilities_result_logging.log_date IS
'Date of creation for the facilities log.';
COMMENT ON COLUMN facilities.facilities_result_logging.user IS
'User name for the person updating the facilities log.';
COMMENT ON COLUMN facilities.facilities_result_logging.added IS
'Count of new facilities added in update.';
COMMENT ON COLUMN facilities.facilities_result_logging.removed IS
'Count of facilities removed in update.';
COMMENT ON COLUMN facilities.facilities_result_logging.geom_updated IS
'Count of facilities where the geometry has been modified.';
COMMENT ON COLUMN facilities.facilities_result_logging.attr_updated IS
'Count of facilities where the attributes have been modified.';
COMMENT ON COLUMN facilities.facilities_result_logging.geom_attr_updated IS
'Count of facilities where the geometry and attributes have been modified.';
COMMENT ON COLUMN facilities.facilities_result_logging.unchanged IS
'Count of facilities which were not modified.';
COMMENT ON COLUMN facilities.facilities_result_logging.row_count_before IS
'Count of facilities in the facilites table before the update.';
COMMENT ON COLUMN facilities.facilities_result_logging.row_count_after IS
'Count of facilities in the facilites table after the update.';

COMMIT;