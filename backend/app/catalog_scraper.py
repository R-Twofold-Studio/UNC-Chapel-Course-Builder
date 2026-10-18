import requests
from bs4 import BeautifulSoup


CATALOG_ENDPOINT = "https://catalog.unc.edu/courses/"


def _fetch_html(url: str) -> str:
    """Return the response from HTTP request, checking if it succeeded"""
    response = requests.get(url)
    response.raise_for_status()
    response = response.text
    return response


def extract_course_tags() -> list[str]:
    """Return course tags from UNC Course Catalog"""
    html = _fetch_html(CATALOG_ENDPOINT)
    soup = BeautifulSoup(html, "html.parser")
    courses = soup.select("#atozindex li")
    courses = [course.get_text() for course in courses]

    course_tags = []
    for course in courses:
        start = course.index("(")
        end = course.index(")", start + 1)
        course_tags.append(course[start + 1: end])
    return course_tags






