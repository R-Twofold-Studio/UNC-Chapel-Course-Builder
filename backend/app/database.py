import os
from functools import lru_cache

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()


@lru_cache
def get_supabase() -> Client:
    """Create the Supabase client on first use, so importing this module needs no credentials."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set (see backend/.env.example)")
    return create_client(url, key)


def upsert_subjects(subjects: list[dict]) -> dict:
    """Upsert subjects to database with format [{"code": ..., "name": ...}, ...]"""
    response = (
        get_supabase()
        .table("subjects")
        .upsert(subjects, on_conflict="code", ignore_duplicates=False)
        .execute()
    )
    return response.data[0]


def insert_courses(
    subject: str,
    catalog_num: str,
    title: str,
    min_cred: str,
    max_cred: str,
    description: str = "",
    requisites: str = "",
) -> dict:
    response = (
        get_supabase()
        .table("courses")
        .insert(
            {
                "subject": subject,
                "catalog_number": catalog_num,
                "title": title,
                "min_credits": min_cred,
                "max_credits": max_cred,
                "description": description,
                "requisites": requisites,
            }
        )
        .execute()
    )
    return response.data[0]
