"""
FETCH & NORMALIZE

Handles: URL scraping (with Selenium JS fallback), pasted text, local file.
Normalization: strips boilerplate, deduplicates lines, preserves structure.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import requests
from bs4 import BeautifulSoup


# ---- Signals that indicate a JS-shell page --------------------------------

_JS_SHELL_SIGNALS = [
    "you need to enable javascript",
    '__next',
    'id="root"',
    'id="app"',
]
_JS_SHELL_MIN_LENGTH = 1500

# ---- Boilerplate patterns to strip ----------------------------------------

_BOILERPLATE_PATTERNS = [
    r"cookie(s)? (policy|banner|settings|preferences)",
    r"privacy policy",
    r"terms of service",
    r"powered by \w+",
    r"this site is protected by recaptcha",
    r"©\s*\d{4}",
    r"all rights reserved",
    r"sign (in|up|out)",
    r"^(home|menu|navigation|skip to content)$",
]
_BOILERPLATE_RE = re.compile(
    "|".join(_BOILERPLATE_PATTERNS), re.IGNORECASE
)


@dataclass
class FetchResult:
    text: str
    input_type: str               # "url" | "text" | "filepath"
    method: str                   # "scrape" | "selenium" | "text" | "file"
    url: str | None = None
    file_path: str | None = None
    signals_triggered: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def fetch_and_normalize(
    *,
    url: str = "",
    text: str = "",
    filepath: str = "",
) -> FetchResult:
    """
    Route to the right acquisition method, then normalize.
    Exactly one of url / text / filepath should be non-empty.
    """
    if text:
        result = _from_text(text)
    elif filepath:
        result = _from_file(filepath)
    elif url:
        result = _from_url(url)
    else:
        raise ValueError("Provide at least one of: url, text, filepath.")

    result.text = _normalize(result.text)
    return result


# ---------------------------------------------------------------------------
# Acquisition methods
# ---------------------------------------------------------------------------

def _from_text(text: str) -> FetchResult:
    return FetchResult(text=text, input_type="text", method="text")


def _from_file(filepath: str) -> FetchResult:
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    return FetchResult(
        text=path.read_text(encoding="utf-8"),
        input_type="filepath",
        method="file",
        file_path=str(path),
    )


def _from_url(url: str) -> FetchResult:
    signals: list[str] = []
    warnings: list[str] = []

    # --- Attempt 1: plain HTTP scrape ---
    raw = _scrape(url)

    if _is_js_shell(raw, signals):
        # --- Attempt 2: Selenium fallback ---
        selenium_raw = _scrape_selenium(url)
        if selenium_raw and len(selenium_raw) > len(raw) and _has_job_headings(selenium_raw):
            raw = selenium_raw
            method = "selenium"
        else:
            method = "scrape"
            warnings.append("JS-shell signals triggered but Selenium output not preferred; using scrape output.")
    else:
        method = "scrape"

    if not raw:
        warnings.append("fetch_empty: no content retrieved from URL.")

    return FetchResult(
        text=raw,
        input_type="url",
        method=method,
        url=url,
        signals_triggered=signals,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Scraping helpers
# ---------------------------------------------------------------------------

def _scrape(url: str) -> str:
    """Plain requests + BeautifulSoup text extraction."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; JobPostProfiler/1.0)"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
            tag.decompose()
        return soup.get_text(separator="\n")
    except Exception as exc:
        return f"[scrape_error: {exc}]"


def _scrape_selenium(url: str) -> str:
    """Selenium fallback for JS-heavy pages. Returns empty string on failure."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By

        opts = Options()
        opts.add_argument("--headless")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(options=opts)
        try:
            driver.get(url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            return driver.find_element(By.TAG_NAME, "body").text
        finally:
            driver.quit()
    except Exception:
        return ""


def _is_js_shell(content: str, signals: list[str]) -> bool:
    triggered = False
    if len(content) < _JS_SHELL_MIN_LENGTH:
        signals.append(f"content_too_short:{len(content)}")
        triggered = True
    for sig in _JS_SHELL_SIGNALS:
        if sig.lower() in content.lower():
            signals.append(f"js_signal:{sig}")
            triggered = True
    return triggered


def _has_job_headings(text: str) -> bool:
    headings = ["responsibilities", "qualifications", "requirements", "about"]
    return any(h in text.lower() for h in headings)


# ---------------------------------------------------------------------------
# Normalization — deterministic text cleanup, no LLM
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """
    Clean scraped/raw text for downstream extraction.
    Rules: remove boilerplate lines, deduplicate, collapse whitespace,
           preserve headings and bullets, maintain original order.
    """
    lines = text.splitlines()
    seen: set[str] = set()
    cleaned: list[str] = []

    for raw_line in lines:
        line = raw_line.strip()

        # Drop empty lines beyond a single blank separator
        if not line:
            if cleaned and cleaned[-1] != "":
                cleaned.append("")
            continue

        # Drop boilerplate
        if _BOILERPLATE_RE.search(line):
            continue

        # Deduplicate
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)

        cleaned.append(line)

    # Collapse multiple blank lines into one
    result_lines: list[str] = []
    prev_blank = False
    for line in cleaned:
        if line == "":
            if not prev_blank:
                result_lines.append("")
            prev_blank = True
        else:
            result_lines.append(line)
            prev_blank = False

    return "\n".join(result_lines).strip()