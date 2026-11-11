"""Sphinx configuration for the Woodlots BC planning portal tech docs."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

project = "Woodlots BC Planning Portal"
author = "UBC FRESH Lab"
copyright = "2026, UBC FRESH Lab"
release = "0.1.0"
version = "0.1"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.mathjax",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}
master_doc = "index"
exclude_patterns = [
    "_build",
    "reports/*",
    "BCCFA-HANDOFF.md",
    "aac/W0026-AAC-SHA256.txt",
]

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "tasklist",
    "attrs_block",
]
myst_heading_anchors = 3

autodoc_typehints = "description"
autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
}
napoleon_numpy_docstring = True
napoleon_google_docstring = False

html_theme = "sphinx_rtd_theme"
html_title = "Woodlots BC Planning Portal"
html_short_title = "Woodlots BC docs"
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_baseurl = os.environ.get(
    "DOCS_BASEURL", "https://ubc-fresh.github.io/fresh-woodlots/"
)
html_theme_options = {
    "navigation_depth": 3,
    "collapse_navigation": False,
    "sticky_navigation": True,
    "includehidden": True,
    "titles_only": False,
}

nitpicky = False
suppress_warnings = ["myst.header"]
