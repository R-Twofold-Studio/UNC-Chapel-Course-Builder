"""Scrape subjects and courses from the UNC catalog and upsert them into Supabase.

Run from backend/app/:  python seed.py
"""

from catalog_scraper import extract_courses, extract_subject_tags, extract_subjects
from database import upsert_courses, upsert_subjects


def upsert_subjects_in_db() -> None:
    subjects = extract_subjects()
    upsert_subjects(subjects)
    print(f"Upserted {len(subjects)} subjects")


def upsert_courses_in_db(subject_tag: str) -> None:
    courses = extract_courses(subject_tag)
    upsert_courses(courses)


def upsert_all_courses_in_db() -> None:
    for subject_tag in extract_subject_tags():
        upsert_courses_in_db(subject_tag)


if __name__ == "__main__":
    upsert_subjects_in_db()
    upsert_all_courses_in_db()
