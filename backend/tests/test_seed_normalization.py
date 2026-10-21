"""Regression tests for the "BCB " foreign key failure during course seeding.

Course codes in the catalog are "<SUBJECT>&#160;<NUMBER>." and subject codes are not all four
letters long, so slicing at a fixed index produced subjects like "BCB " that are absent from the
subjects table (and catalog numbers like "\\xa0110" for four-letter subjects).
"""

import logging

import pytest

from app import catalog_scraper
from app.catalog_scraper import parse_course_code
from app.database import normalize_course_records, normalize_subject_records

NBSP = "\xa0"

INDEX_HTML = f"""
<div id="atozindex"><ul>
  <li><a href="/courses/bcb/">Bioinformatics and Computational Biology (BCB)</a></li>
  <li><a href="/courses/chem/">Chemistry ( CHEM{NBSP})</a></li>
  <li><a href="/courses/comp/">Computer Science (COMP)</a></li>
</ul></div>
"""


def _courseblock(code: str, title: str = "Title.") -> str:
    return f"""
    <div class="courseblock">
      <div class="detail-code"><strong>{code}</strong></div>
      <div class="detail-title"><strong>{title}</strong></div>
      <div class="detail-hours"><strong>3 Credits.</strong></div>
    </div>
    """


COURSES_HTML = "".join(
    [
        _courseblock(f"BCB{NBSP}501."),  # 3-letter subject: previously "BCB "
        _courseblock(f"COMP{NBSP}110."),  # previously catalog_number "\xa0110"
        _courseblock(f" CHEM {NBSP}101L. "),  # suffix must survive
        _courseblock("COMP 89H."),
    ]
)


@pytest.fixture
def fake_catalog(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_fetch(url: str, endpoint: str = "") -> str:
        return INDEX_HTML if endpoint == "" else COURSES_HTML

    monkeypatch.setattr(catalog_scraper, "_fetch_html", fake_fetch)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (f"BCB{NBSP}501.", ("BCB", "501")),
        ("BCB 501.", ("BCB", "501")),
        (f"COMP{NBSP}110.", ("COMP", "110")),
        (f"  CHEM{NBSP}101L.{NBSP}", ("CHEM", "101L")),
        ("COMP 590H.", ("COMP", "590H")),
        ("AS 101.", ("AS", "101")),
    ],
)
def test_parse_course_code_strips_whitespace_and_keeps_suffix(
    raw: str, expected: tuple[str, str]
) -> None:
    assert parse_course_code(raw) == expected


def test_parse_course_code_rejects_garbage() -> None:
    with pytest.raises(ValueError):
        parse_course_code("Special Topics")


def test_scraped_course_subjects_match_scraped_subject_codes(fake_catalog: None) -> None:
    subject_codes = {s["code"] for s in catalog_scraper.extract_subjects()}
    courses = catalog_scraper.extract_courses("BCB")

    assert subject_codes == {"BCB", "CHEM", "COMP"}
    assert catalog_scraper.extract_subject_tags() == ["BCB", "CHEM", "COMP"]
    keys = [(c["subject"], c["catalog_number"]) for c in courses]
    assert keys == [("BCB", "501"), ("COMP", "110"), ("CHEM", "101L"), ("COMP", "89H")]
    # Every course would satisfy courses_subject_fkey.
    assert {subject for subject, _ in keys} <= subject_codes


def test_normalize_course_records_strips_and_dedupes(caplog: pytest.LogCaptureFixture) -> None:
    courses = [
        {"subject": "BCB ", "catalog_number": "501", "title": "first"},
        {"subject": f"{NBSP}BCB", "catalog_number": " 501. ", "title": "duplicate"},
        {"subject": "COMP", "catalog_number": f"{NBSP}110", "title": "intro"},
        {"subject": "CHEM", "catalog_number": "101L", "title": "lab"},
    ]

    with caplog.at_level(logging.WARNING):
        result = normalize_course_records(courses)

    assert [(c["subject"], c["catalog_number"], c["title"]) for c in result] == [
        ("BCB", "501", "first"),
        ("COMP", "110", "intro"),
        ("CHEM", "101L", "lab"),
    ]
    assert "duplicate courses record" in caplog.text
    assert courses[0]["subject"] == "BCB "  # input is not mutated


def test_normalize_subject_records_strips_and_dedupes() -> None:
    subjects = [{"code": "BCB ", "name": "Bioinformatics"}, {"code": "BCB", "name": "Dup"}]

    assert normalize_subject_records(subjects) == [{"code": "BCB", "name": "Bioinformatics"}]


@pytest.mark.parametrize("bad", ["", "   ", None])
def test_normalize_course_records_rejects_blank_keys(bad: object) -> None:
    with pytest.raises(ValueError):
        normalize_course_records([{"subject": bad, "catalog_number": "101"}])


class _FakeTable:
    def __init__(self, calls: list, name: str) -> None:
        self.calls, self.name = calls, name

    def upsert(self, rows: list[dict], **kwargs: object) -> "_FakeTable":
        self.calls.append((self.name, rows, kwargs))
        self.rows = rows
        return self

    def execute(self) -> object:
        return type("Response", (), {"data": self.rows})()


class _FakeClient:
    def __init__(self) -> None:
        self.calls: list = []

    def table(self, name: str) -> _FakeTable:
        return _FakeTable(self.calls, name)


def test_upserts_normalize_and_use_unique_conflict_targets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import database

    client = _FakeClient()
    monkeypatch.setattr(database, "get_supabase", lambda: client)

    database.upsert_subjects([{"code": "BCB ", "name": "Bioinformatics"}])
    database.upsert_courses([{"subject": "BCB ", "catalog_number": "501"}])
    assert database.upsert_courses([]) == []

    (subj_table, subj_rows, subj_kwargs), (course_table, course_rows, course_kwargs) = client.calls
    assert (subj_table, subj_kwargs["on_conflict"]) == ("subjects", "code")
    assert (course_table, course_kwargs["on_conflict"]) == ("courses", "subject,catalog_number")
    assert subj_rows == [{"code": "BCB", "name": "Bioinformatics"}]
    assert course_rows == [{"subject": "BCB", "catalog_number": "501"}]
