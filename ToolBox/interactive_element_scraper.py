"""Interactive element picker and scraper.

This utility opens a webpage in a Selenium-controlled browser session,
lets the user hover and click on elements to capture a CSS selector, and
then re-downloads the page with ``requests`` to scrape every element that
matches the selector. The extracted data is saved to a CSV file for later
analysis.

Example usage::

    python ToolBox/interactive_element_scraper.py https://example.com \
        --output elements.csv

The script requires a working Chrome/Chromium driver that is compatible
with the installed browser version. Install dependencies with::

    pip install selenium beautifulsoup4 requests

"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from dataclasses import dataclass
from typing import Iterable, List, Optional

import requests
from bs4 import BeautifulSoup

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.support.ui import WebDriverWait
except ImportError as exc:  # pragma: no cover - handled via CLI feedback
    raise SystemExit(
        "Selenium is required to run this script. Install it with 'pip install selenium'."
    ) from exc


@dataclass
class ScrapedElement:
    index: int
    css_selector: str
    text: str
    attributes: str
    outer_html: str


def _install_picker(driver: webdriver.Chrome) -> None:
    """Inject JavaScript that highlights hovered elements and stores selection."""

    picker_script = """
        (() => {
            if (window.__leanElementPickerInstalled) { return; }
            window.__leanElementPickerInstalled = true;

            const highlightStyle = '2px solid #ff5a36';
            let lastHovered = null;

            const buildCssPath = (element) => {
                if (!(element instanceof Element)) { return ''; }
                const path = [];
                while (element && element.nodeType === Node.ELEMENT_NODE) {
                    let selector = element.nodeName.toLowerCase();
                    if (element.id) {
                        selector = `#${element.id}`;
                        path.unshift(selector);
                        break;
                    } else {
                        let sibling = element;
                        let nth = 1;
                        while ((sibling = sibling.previousElementSibling) != null) {
                            if (sibling.nodeName === element.nodeName) { nth += 1; }
                        }
                        if (nth > 1 || element.nextElementSibling) {
                            selector += `:nth-of-type(${nth})`;
                        }
                    }
                    path.unshift(selector);
                    element = element.parentElement;
                }
                return path.join(' > ');
            };

            const clearHighlight = () => {
                if (!lastHovered) { return; }
                lastHovered.style.outline = lastHovered.__leanOriginalOutline || '';
                delete lastHovered.__leanOriginalOutline;
                lastHovered = null;
            };

            document.addEventListener('mouseover', (event) => {
                if (!(event.target instanceof Element)) { return; }
                clearHighlight();
                lastHovered = event.target;
                lastHovered.__leanOriginalOutline = lastHovered.style.outline;
                lastHovered.style.outline = highlightStyle;
            }, true);

            document.addEventListener('mouseout', (event) => {
                if (event.target === lastHovered) {
                    clearHighlight();
                }
            }, true);

            document.addEventListener('click', (event) => {
                if (!(event.target instanceof Element)) { return; }
                event.preventDefault();
                event.stopPropagation();
                clearHighlight();
                const selection = {
                    css: buildCssPath(event.target),
                    html: event.target.outerHTML,
                    text: event.target.innerText
                };
                window.__leanSelectedElement = selection;
                window.dispatchEvent(new CustomEvent('lean-element-picked'));
            }, true);
        })();
    """

    driver.execute_script(picker_script)


def _await_selection(driver: webdriver.Chrome, timeout: float = 120) -> dict:
    """Wait for the user to click an element and return the captured metadata."""

    def _selection_available(_: webdriver.Chrome) -> Optional[dict]:
        return driver.execute_script("return window.__leanSelectedElement || null;")

    wait = WebDriverWait(driver, timeout=timeout, poll_frequency=0.2)
    return wait.until(_selection_available)


def _scrape_with_selector(url: str, css_selector: str) -> List[ScrapedElement]:
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    matches = soup.select(css_selector)

    scraped: List[ScrapedElement] = []
    for index, element in enumerate(matches, start=1):
        text = " ".join(element.get_text(separator=" ", strip=True).split())
        attributes = json.dumps(element.attrs, ensure_ascii=False)
        scraped.append(
            ScrapedElement(
                index=index,
                css_selector=css_selector,
                text=text,
                attributes=attributes,
                outer_html=str(element),
            )
        )
    return scraped


def _write_csv(path: str, data: Iterable[ScrapedElement]) -> None:
    rows = list(data)
    if not rows:
        raise ValueError("No elements matched the selected CSS selector; nothing to write.")

    fieldnames = ["index", "css_selector", "text", "attributes", "outer_html"]
    with open(path, "w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)


def _create_driver(chrome_binary: Optional[str], driver_path: Optional[str]) -> webdriver.Chrome:
    options = Options()
    if chrome_binary:
        options.binary_location = chrome_binary

    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--start-maximized")

    service = Service(executable_path=driver_path) if driver_path else Service()
    return webdriver.Chrome(service=service, options=options)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Interactively pick an element on a webpage and scrape matching elements.",
    )
    parser.add_argument("url", help="Target webpage URL to inspect and scrape.")
    parser.add_argument(
        "--output",
        default="scraped_elements.csv",
        help="Path to the CSV file where scraped data will be stored.",
    )
    parser.add_argument(
        "--chrome-binary",
        help="Path to the Chrome/Chromium binary to use (optional).",
    )
    parser.add_argument(
        "--driver-path",
        help="Path to the ChromeDriver executable if it is not on PATH.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="Seconds to wait for an element selection before timing out.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    driver = _create_driver(args.chrome_binary, args.driver_path)
    try:
        print(f"Opening {args.url} ...")
        driver.get(args.url)
        time.sleep(2)

        print("Hover over elements to highlight them. Click an element to select it.")
        _install_picker(driver)

        selection = _await_selection(driver, timeout=args.timeout)
        css_selector = selection["css"]
        print(f"Selected CSS selector: {css_selector}")

        scraped = _scrape_with_selector(args.url, css_selector)
        _write_csv(args.output, scraped)

        print(f"Saved {len(scraped)} elements to {args.output}")
        return 0
    except Exception as exc:  # pragma: no cover - CLI surface
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        driver.quit()


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main())
