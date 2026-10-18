import json
import re
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup


CLASS_SEARCH_ENDPOINT = "https://reports.unc.edu/class-search/"


def _fetch_class_html(course_tag: str):
    """Return the filtered response to a specific course from HTTP request to UNC Class Search endpoint"""
    session = requests.Session()

    response = session.get(CLASS_SEARCH_ENDPOINT)
    soup = BeautifulSoup(response.text, "html.parser")
    token = soup.select_one(
    'input[name="csrfmiddlewaretoken"]'
    )["value"]
    response = session.post(
        CLASS_SEARCH_ENDPOINT, 
        data={
            "csrfmiddlewaretoken": token,
            "subject": course_tag,
            "term": "2027 Spring",
        })
    response.raise_for_status()
    response = response.text
    return response


# Day codes used in the Schedule column (e.g. "MWF", "TTH", "MTWTHF").
# Two-letter codes are listed first so "TH" isn't read as "T" + "H".
_DAY_CODES = [("TH", "TH"), ("SA", "SA"), ("SU", "SU"),
              ("M", "MO"), ("T", "TU"), ("W", "WE"), ("F", "FR"), ("S", "SA")]


def _clean(text: str) -> str | None:
    """Collapse whitespace; map the site's 'None' / empty cells to None."""
    text = " ".join(text.split())
    return None if text in ("", "None", "TBA") else text


def _to_24h(t: str) -> str:
    return datetime.strptime(t.strip(), "%I:%M %p").strftime("%H:%M")

def _to_iso_date(d: str) -> str:
    return datetime.strptime(d.strip(), "%m/%d/%Y").strftime("%Y-%m-%d")


def _parse_days(code: str) -> list[str]:
    days, i = [], 0
    while i < len(code):
        for raw, norm in _DAY_CODES:
            if code.startswith(raw, i):
                days.append(norm)
                i += len(raw)
                break
        else:
            i += 1  # skips anything unexpected
    return days


def _parse_meeting(dates: str | None, schedule: str | None) -> list[dict]:
    """'01/06/2027 - 05/06/2027' + 'MWF 09:05 AM-09:55 AM' -> meeting dict."""
    if not dates and not schedule:
        return []
    meeting = {"days": [], "start_time": None, "end_time": None,
               "start_date": None, "end_date": None, "location": None}
    if dates and " - " in dates:
        start, end = dates.split(" - ", 1)
        meeting["start_date"], meeting["end_date"] = _to_iso_date(start), _to_iso_date(end)
    if schedule:
        m = re.match(r"([A-Z]+)\s+(\d{1,2}:\d{2}\s*[AP]M)\s*-\s*(\d{1,2}:\d{2}\s*[AP]M)", schedule)
        if m:
            meeting["days"] = _parse_days(m.group(1))
            meeting["start_time"] = _to_24h(m.group(2))
            meeting["end_time"] = _to_24h(m.group(3))
    return [meeting]


def _parse_credits(hours: str | None):
    if not hours:
        return None
    try:
        value = float(hours)
    except ValueError:
        return hours  # e.g. a range like "1.0-3.0"; keep as-is
    return int(value) if value.is_integer() else value


def _format_term(term: str | None) -> str | None:
    """'2027 Spring' -> 'Spring 2027'."""
    if not term:
        return None
    parts = term.split()
    return f"{parts[1]} {parts[0]}" if len(parts) == 2 and parts[0].isdigit() else term


def extract_class_data_as_json(course_tag: str) -> str:
    """Parse the class-search results page into a JSON string.

    The results table uses rowspan for Subject and Catalog Number, so a row has
    12 cells (new subject), 11 (new catalog number) or 10 (another section of
    the same course). The last 10 cells are always the same columns, so we read
    those and carry Subject / Catalog Number forward from earlier rows.

    The site no longer shows component, instructor or room, so those come back
    as None / [].
    """
    html = _fetch_class_html(course_tag)
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("#results-table")

    sections = []
    term = None
    subject = catalog_number = None

    rows = table.select("tbody tr") if table else []
    for row in rows:
        cells = row.find_all("td", recursive=False)
        if len(cells) < 10:
            continue
        if len(cells) >= 12:
            subject = cells[-12].get_text(strip=True)
        if len(cells) >= 11:
            catalog_number = cells[-11].get_text(strip=True)

        (same_as_td, section_td, class_num_td, title_td, term_td, hours_td,
         dates_td, schedule_td, mode_td, seats_td) = cells[-10:]

        same_as_text = _clean(same_as_td.get_text())
        same_as = [s.strip() for s in same_as_text.split(",")] if same_as_text else []

        row_term = _clean(term_td.get_text())
        term = term or _format_term(row_term)

        seats_text = _clean(seats_td.get_text())
        try:
            seats = int(seats_text) if seats_text else None
        except ValueError:
            seats = None

        sections.append({
            "subject": subject,
            "catalog_number": catalog_number,
            "title": _clean(title_td.get_text()),
            "section": _clean(section_td.get_text()),
            "class_number": _clean(class_num_td.get_text()),
            "component": None,
            "credits": _parse_credits(_clean(hours_td.get_text())),
            "same_as": same_as,
            "instruction_mode": _clean(mode_td.get_text()),
            "instructors": [],
            "available_seats": seats,
            "meetings": _parse_meeting(_clean(dates_td.get_text()),
                                       _clean(schedule_td.get_text())),
        })

    result = {
        "term": term,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sections": sections,
    }
    return json.dumps(result, indent=2)
