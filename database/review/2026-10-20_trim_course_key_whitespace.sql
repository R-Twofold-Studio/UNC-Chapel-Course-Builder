-- Review-only cleanup for whitespace in course/subject key columns.
-- NOT run automatically. Read each step's output before going on.
--
-- Background: the old catalog scraper sliced course codes at index 4, so rows already written
-- for four-letter subjects (e.g. AAAD, ANTH, ARTH, ASIA, ...) have catalog_number values with a
-- leading NBSP/space such as E' 110'. Re-seeding with the fixed scraper writes '110', which is
-- a different key, so those old rows would become stale near-duplicates unless cleaned up.
--
-- "Whitespace" below = space, tab, LF, CR and NBSP (chr(160)); plain btrim() ignores NBSP.
-- The script never deletes rows and leaves FK and unique constraints untouched.

-- 1. Preview subjects with dirty codes (expected: none; subjects were already stripped).
SELECT code, '[' || code || ']' AS bracketed, name
FROM subjects
WHERE code <> btrim(code, ' ' || chr(9) || chr(10) || chr(13) || chr(160));

-- 2. Preview courses with dirty keys and what they would become.
SELECT subject,
       catalog_number,
       '[' || catalog_number || ']' AS bracketed,
       upper(btrim(subject, ' ' || chr(9) || chr(10) || chr(13) || chr(160))) AS new_subject,
       btrim(catalog_number, ' ' || chr(9) || chr(10) || chr(13) || chr(160)) AS new_catalog_number
FROM courses
WHERE subject <> btrim(subject, ' ' || chr(9) || chr(10) || chr(13) || chr(160))
   OR catalog_number <> btrim(catalog_number, ' ' || chr(9) || chr(10) || chr(13) || chr(160))
ORDER BY 1, 2;

-- 3. Collisions: dirty rows whose cleaned key already exists as a clean row, or where two dirty
--    rows clean to the same key. These must be resolved by hand (decide which row to keep);
--    step 4 skips them so the unique constraint is never violated.
WITH cleaned AS (
    SELECT ctid AS row_id,
           subject,
           catalog_number,
           upper(btrim(subject, ' ' || chr(9) || chr(10) || chr(13) || chr(160))) AS new_subject,
           btrim(catalog_number, ' ' || chr(9) || chr(10) || chr(13) || chr(160)) AS new_catalog_number
    FROM courses
)
SELECT new_subject, new_catalog_number, count(*) AS rows_with_this_key,
       array_agg('[' || subject || '|' || catalog_number || ']') AS original_keys
FROM cleaned
GROUP BY new_subject, new_catalog_number
HAVING count(*) > 1
ORDER BY 1, 2;

-- 4. Fix non-colliding dirty rows in place. Runs in a transaction that ROLLS BACK by default:
--    check the UPDATE count against step 2 minus step 3, then change ROLLBACK to COMMIT.
--    If another table references courses by (subject, catalog_number) without ON UPDATE CASCADE,
--    the UPDATE will fail on those rows; review the referencing table first in that case.
BEGIN;

WITH cleaned AS (
    SELECT ctid AS row_id,
           upper(btrim(subject, ' ' || chr(9) || chr(10) || chr(13) || chr(160))) AS new_subject,
           btrim(catalog_number, ' ' || chr(9) || chr(10) || chr(13) || chr(160)) AS new_catalog_number,
           (subject <> upper(btrim(subject, ' ' || chr(9) || chr(10) || chr(13) || chr(160)))
            OR catalog_number <> btrim(catalog_number, ' ' || chr(9) || chr(10) || chr(13) || chr(160)))
               AS is_dirty
    FROM courses
),
key_counts AS (
    SELECT new_subject, new_catalog_number, count(*) AS n
    FROM cleaned
    GROUP BY new_subject, new_catalog_number
)
UPDATE courses AS c
SET subject = cl.new_subject,
    catalog_number = cl.new_catalog_number
FROM cleaned AS cl
JOIN key_counts AS k USING (new_subject, new_catalog_number)
WHERE c.ctid = cl.row_id
  AND cl.is_dirty
  AND k.n = 1                                                     -- skip collisions (step 3)
  AND cl.new_catalog_number <> ''
  AND EXISTS (SELECT 1 FROM subjects s WHERE s.code = cl.new_subject);  -- keep FK satisfied

-- Re-run step 2 here to confirm only the step-3 collisions remain.

ROLLBACK;  -- change to COMMIT after reviewing the results
