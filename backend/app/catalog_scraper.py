import logging
import re

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

CATALOG_URL = "https://catalog.unc.edu/courses/"

# A catalog course code is "<SUBJECT><whitespace><NUMBER>." e.g. "COMP 110.", "BCB 501." or
# "CHEM 101L.". Subject codes vary in length (2-5 letters) and the separator is usually a
# non-breaking space (&#160;), so the code must be split on whitespace, not at a fixed index.
# Python's str.strip() and regex \s both treat U+00A0 as whitespace.
_COURSE_CODE_RE = re.compile(r"^([A-Za-z]{2,5})\s*(\d+[A-Za-z]*)\.?$")


def _normalize_subject_code(code: str) -> str:
    """Return a subject code with surrounding whitespace (including NBSP) removed."""
    return code.strip().upper()


def _normalize_catalog_number(catalog_number: str) -> str:
    """Return a catalog number without surrounding whitespace or a trailing period.

    Suffixes that are part of the number ("101L", "89H", "590H") are preserved.
    """
    return catalog_number.strip().removesuffix(".").strip()


def _parse_course_code(course_code: str) -> tuple[str, str]:
    """Split a catalog course code such as "BCB\xa0501." into ("BCB", "501")."""
    match = _COURSE_CODE_RE.match(course_code.strip())
    if match is None:
        raise ValueError(f"Unrecognized course code: {course_code!r}")
    subject, catalog_number = match.groups()
    return _normalize_subject_code(subject), _normalize_catalog_number(catalog_number)


def _fetch_html(url: str, endpoint: str = "") -> str:
    """Return the response from HTTP request, checking if it succeeded"""
    response = requests.get(url + endpoint)
    response.raise_for_status()
    response = response.text
    return response


def extract_subject_tags() -> list[str]:
    """Return subject codes from the UNC Catalog."""
    html = _fetch_html(CATALOG_URL)
    soup = BeautifulSoup(html, "html.parser")

    subject_tags = []
    for subject in soup.select("#atozindex li"):
        text = subject.get_text().strip()
        start = text.rindex("(")
        end = text.rindex(")")
        subject_tags.append(_normalize_subject_code(text[start + 1 : end]))

    return subject_tags


def extract_subjects() -> list[dict[str, str]]:
    """Return subject codes and names from the UNC Catalog."""
    html = _fetch_html(CATALOG_URL)
    soup = BeautifulSoup(html, "html.parser")

    records = []

    for subject in soup.select("#atozindex li"):
        text = subject.get_text().strip()

        start_code = text.rindex("(")
        end_code = text.rindex(")")

        subject_tag = _normalize_subject_code(text[start_code + 1 : end_code])
        subject_name = " ".join(text[:start_code].split())

        records.append({"code": subject_tag, "name": subject_name})

    return records


def _parse_rules_requirements(element: str | None, label: str) -> str | None:
    if element is not None:
        text = " ".join(element.get_text().split())
        result = text.removeprefix(label).removesuffix(".")
    else:
        result = None
    return result


def _set_min_credit(credits: str) -> str:
    return credits[0]


def _set_max_credit(credits: str) -> str:
    if "-" in credits:
        idx = credits.index("-")
        credits = credits[idx + 1]
    return credits[0]


def _format_gen_ed(gen_ed: str) -> list[str]:
    """Return gen education fullfillments as a list"""
    result = []
    if gen_ed is None:
        return result

    if "," in gen_ed:
        gen_eds = gen_ed.replace(" ", "").split(",")
        for gen in gen_eds:
            result.append(gen)
    else:
        result.append(gen_ed)
    return result


def extract_courses(course_tag: str = None) -> list[dict]:
    """Return course details of specified subject as a json from UNC Catalog

    Any courses approved after June 1, 2026 will not appear in the 2026-27 Academic Catalog.
    """
    json = []

    endpoint = course_tag.lower() + "/"
    html = _fetch_html(CATALOG_URL, endpoint)
    soup = BeautifulSoup(html, "html.parser")

    # Scraping logic
    for course in soup.select(".courseblock"):
        gen_ed_element = course.select_one(".detail-idea_action")
        requisites_element = course.select_one(".detail-requisites")
        grading_element = course.select_one(".detail-grading_status")
        course_code = course.select_one(".detail-code strong").get_text()

        try:
            subject, catalog_number = _parse_course_code(course_code)
        except ValueError:
            logger.warning("Skipping course with unparseable code %r", course_code)
            continue
        title = course.select_one(".detail-title strong").get_text().removesuffix(".")
        credits = course.select_one(".detail-hours strong").get_text()
        description = course.select_one(".courseblockextra")
        if description is not None:
            description = description.get_text()
        gen_ed = _parse_rules_requirements(gen_ed_element, "IDEAs in Action Gen Ed: ")
        requisites = _parse_rules_requirements(requisites_element, "Requisites: ")
        grading = _parse_rules_requirements(grading_element, "Grading Status: ")

        # Supabase record format
        record = {
            "subject": subject,
            "catalog_number": catalog_number,
            "title": title,
            "min_credits": _set_min_credit(credits),
            "max_credits": _set_max_credit(credits),
            "description": description,
            "requisites": requisites,
            "gen_ed": _format_gen_ed(gen_ed),
            "grading_status": grading,
        }
        json.append(record)

    return json
