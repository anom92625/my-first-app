"""
PDF generation from newsletter HTML.

Uses WeasyPrint to render the newsletter HTML to a print-ready PDF.
WeasyPrint is a pure-Python library that handles CSS layout well and
requires no external binary dependencies beyond system-level font/cairo libs.

The newsletter HTML uses inline styles (email-safe), which WeasyPrint
renders faithfully.  We inject a thin <style> block to add:
  - A4 page setup with sensible margins
  - Correct page-break behaviour for card sections
  - Suppressed navigation/unsubscribe footer (not useful in print)
  - Forced white background on elements that use dark/navy backgrounds
    so ink-unfriendly areas render cleanly in print
"""
import logging
import re
from io import BytesIO

logger = logging.getLogger(__name__)

# CSS injected into the document before WeasyPrint renders it.
# Targets the outermost newsletter wrappers and overrides anything
# that looks terrible in print.
_PRINT_CSS = """
@page {
    size: A4;
    margin: 18mm 16mm 18mm 16mm;
}

/* Ensure the entire doc has a white background */
html, body {
    background: #fff !important;
    color: #0a0a0c !important;
    font-size: 10pt;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
}

/* Masthead: keep navy background but tighten padding for print */
.masthead, [class*="masthead"] {
    page-break-after: avoid;
}

/* Don't break inside a deal card or company row */
table tr, .deal-card {
    page-break-inside: avoid;
}

/* Make the header stat bar and section dividers readable in print */
a {
    color: #0f2545 !important;
    text-decoration: none;
}

/* Hide unsubscribe footer — irrelevant in PDF */
.unsub-footer, [id="unsub"], [class*="unsub"] {
    display: none !important;
}

/* Widen the content column to fill the A4 page */
.email-wrapper, .page, [style*="max-width:600px"], [style*="max-width: 600px"] {
    max-width: 100% !important;
    width: 100% !important;
}
"""


def _inject_print_css(html: str) -> str:
    """
    Inject _PRINT_CSS into the document <head>.
    If no <head> tag exists, prepend the style block directly.
    """
    style_tag = f"<style>{_PRINT_CSS}</style>"
    if re.search(r"</head>", html, re.IGNORECASE):
        return re.sub(r"(</head>)", f"{style_tag}\\1", html, count=1, flags=re.IGNORECASE)
    return style_tag + html


def generate_pdf(html: str) -> bytes:
    """
    Render newsletter HTML to a PDF and return the raw bytes.

    Raises ImportError if weasyprint is not installed.
    Raises any WeasyPrint rendering exceptions on failure.
    """
    try:
        from weasyprint import HTML, CSS  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "weasyprint is required for PDF generation. "
            "Install it with: pip install weasyprint"
        ) from exc

    prepared_html = _inject_print_css(html)
    buf = BytesIO()
    HTML(string=prepared_html).write_pdf(buf)
    buf.seek(0)
    return buf.read()
