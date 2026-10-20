import requests
from bs4 import BeautifulSoup

CATALOG_ENDPOINT = "https://catalog.unc.edu/courses/"
CODE_LENGTH = 5


def _fetch_html(url: str) -> str:
    """Return the response from HTTP request, checking if it succeeded"""
    response = requests.get(url)
    response.raise_for_status()
    response = response.text
    return response


def extract_subject_tags() -> list[str]:
    """Return subject tags as a list from UNC Catalog"""
    html = _fetch_html(CATALOG_ENDPOINT)
    soup = BeautifulSoup(html, "html.parser")
    subjects = soup.select("#atozindex li")
    subjects = [subject.get_text() for subject in subjects]

    subject_tags = []
    for subject in subjects:
        start = subject.index("(")
        end = subject.index(")", start + 1)
        subject_tags.append(subject[start + 1 : end])
    return subject_tags


def extract_subjects() -> list[dict]:
    """Return subject title and tags as a json from UNC Catalog

    Format: [{"code": ..., "name": ...}]
    """
    html = _fetch_html(CATALOG_ENDPOINT)
    soup = BeautifulSoup(html, "html.parser")
    subjects = soup.select("#atozindex li")
    subjects = [subject.get_text() for subject in subjects]

    json = []

    for subject in subjects:
        start_code = subject.index("(")
        end_code = subject.index(")", start_code + 1)

        # If the text between () is too long to be a code, the real code is in the next ()
        # e.g. PHARMACY (NON-DEPARTMENTAL) (PHCY)
        if (end_code - start_code) > CODE_LENGTH:
            start_code = subject.index("(", start_code + 1)
            end_code = subject.index(")", end_code + 1)

        subject_tag = subject[start_code + 1 : end_code]

        end_name = start_code - 1
        subject_name = subject[0:end_name]

        field = {"code": subject_tag, "name": subject_name}
        json.append(field)
    return json
