import re
import requests

from bs4 import BeautifulSoup
from urllib.parse import urlparse

from agents import function_tool

@function_tool
def fetch_website_text(url: str) -> str:
    """
    Fetch a public webpage and return readable text content.

    Use this tool when the user asks to open, inspect, or summarize a webpage.
    """

    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        return "Error: Only http and https URLs are allowed."

    try:
        response = requests.get(
            url,
            timeout=20,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 compatible; PhDResearchAgent/0.1; "
                    "+https://example.com"
                )
            },
        )
        response.raise_for_status()

    except requests.RequestException as exc:
        return f"Error fetching URL: {exc}"

    content_type = response.headers.get("content-type", "")

    if "text/html" not in content_type and "text/plain" not in content_type:
        return f"Error: Unsupported content type: {content_type}"

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove scripts, styles, navigation noise, etc.
    for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav"]):
        tag.decompose()

    title = soup.title.get_text(" ", strip=True) if soup.title else ""

    text = soup.get_text(separator="\n", strip=True)

    # Clean repeated blank lines.
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Keep it small enough for a simple model call.
    max_chars = 20_000
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[Text truncated because webpage was long.]"

    return f"URL: {url}\nTITLE: {title}\n\nCONTENT:\n{text}"
