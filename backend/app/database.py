import logging
import os
from functools import lru_cache

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

logger = logging.getLogger(__name__)


@lru_cache
def get_supabase() -> Client:
    """Create the Supabase client on first use, so importing this module needs no credentials."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set (see backend/.env.example)")
    return create_client(url, key)


def _clean_key(value: object, field: str) -> str:
    """Strip surrounding whitespace (including NBSP) from a key column; reject blanks."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string, got {value!r}")
    return value.strip()


def _dedupe(records: list[dict], key_fields: tuple[str, ...], table: str) -> list[dict]:
    """Keep the first record for each key; a batch upsert cannot touch one row twice."""
    seen: set[tuple[str, ...]] = set()
    unique = []
    for record in records:
        key = tuple(record[field] for field in key_fields)
        if key in seen:
            logger.warning("Dropping duplicate %s record for key %s", table, key)
            continue
        seen.add(key)
        unique.append(record)
    return unique


def normalize_subject_records(subjects: list[dict]) -> list[dict]:
    """Return subject records with normalized, de-duplicated "code" values."""
    cleaned = [{**s, "code": _clean_key(s.get("code"), "code").upper()} for s in subjects]
    return _dedupe(cleaned, ("code",), "subjects")


def normalize_course_records(courses: list[dict]) -> list[dict]:
    """Return course records with normalized "subject"/"catalog_number", de-duplicated.

    Catalog number suffixes ("101L", "89H") are kept; only surrounding whitespace and a
    trailing period are removed so keys match the subjects table and the unique constraint.
    """
    cleaned = [
        {
            **c,
            "subject": _clean_key(c.get("subject"), "subject").upper(),
            "catalog_number": _clean_key(c.get("catalog_number"), "catalog_number")
            .removesuffix(".")
            .strip(),
        }
        for c in courses
    ]
    return _dedupe(cleaned, ("subject", "catalog_number"), "courses")


def upsert_subjects(subjects: list[dict]) -> list[dict]:
    """Upsert subjects to database with format [{"code": ..., "name": ...}, ...]"""
    subjects = normalize_subject_records(subjects)
    if not subjects:
        return []
    response = (
        get_supabase()
        .table("subjects")
        .upsert(subjects, on_conflict="code", ignore_duplicates=False)
        .execute()
    )
    return response.data


def upsert_courses(courses: list[dict]) -> list[dict]:
    """Upsert courses keyed on the (subject, catalog_number) unique constraint."""
    courses = normalize_course_records(courses)
    if not courses:
        return []
    response = (
        get_supabase()
        .table("courses")
        .upsert(courses, on_conflict="subject,catalog_number")
        .execute()
    )
    return response.data
