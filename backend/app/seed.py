"""Scrape subjects from the UNC catalog and upsert them into Supabase.

Run from backend/:  python -m app.seed
"""

from app.catalog_scraper import extract_subjects
from app.database import upsert_subjects


def main() -> None:
    subjects = extract_subjects()
    upsert_subjects(subjects)
    print(f"Upserted {len(subjects)} subjects")


if __name__ == "__main__":
    main()
