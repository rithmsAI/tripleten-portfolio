-- Read-only inspection of the local fictional SQLite database.
SELECT id, version, json_extract(payload, '$.status') AS status,
       json_extract(payload, '$.owner') AS investigator
FROM incidents ORDER BY id;

SELECT incident_id, COUNT(*) AS recorded_actions, MIN(at) AS first_action,
       MAX(at) AS latest_action
FROM audit GROUP BY incident_id;

SELECT seq, at, action, detail FROM audit
WHERE incident_id = 'INC-1042' ORDER BY seq;
