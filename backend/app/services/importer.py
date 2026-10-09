"""OpenAPI import — paste a Swagger URL or document, get an editable project.

No LLM involved; this is the second demo path that cannot fail on model
quality. Every import goes through the same structural validator the model
drafts face, so an imported project is indistinguishable from a generated one.
"""

import ipaddress
import json
import socket
from urllib.parse import urlparse

import httpx
import yaml

from app.services.validate import validate_openapi

MAX_IMPORT_BYTES = 2 * 1024 * 1024
FETCH_TIMEOUT = 10.0


def _public_url(raw: str) -> str:
    """SSRF guard: only public http(s) hosts. Rejects anything else."""
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError(f"rejected: not a public http(s) URL: {raw!r}")
    try:
        addrs = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror:
        raise ValueError(f"rejected: cannot resolve host: {parsed.hostname!r}")
    for info in addrs:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise ValueError(f"rejected: not a public host: {parsed.hostname!r}")
    return raw


def _parse(text: str) -> dict:
    """JSON if it looks like JSON, YAML otherwise. Never yaml.full_load."""
    stripped = text.strip()
    try:
        doc = json.loads(stripped) if stripped[:1] in "{[" else yaml.safe_load(stripped)
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        raise ValueError(f"could not parse as JSON or YAML: {e}")
    if not isinstance(doc, dict):
        raise ValueError("document must be a JSON/YAML object")
    return doc


def import_openapi(url: str | None = None, content: str | None = None) -> dict:
    """Fetch or parse an OpenAPI 3.0 document, validate it, return it.

    Exactly one of url/content is required. Raises ValueError on bad input
    or an unusable document; network failures surface as httpx.HTTPError.
    """
    if bool(url) == bool(content):
        raise ValueError("provide exactly one of 'url' or 'content'")
    if url:
        _public_url(url)
        resp = httpx.get(
            url, timeout=FETCH_TIMEOUT, headers={"User-Agent": "Spec2Run/0.1"}
        )
        resp.raise_for_status()
        if len(resp.content) > MAX_IMPORT_BYTES:
            raise ValueError("document too large (limit 2 MB)")
        text = resp.text
    else:
        if len(content.encode()) > MAX_IMPORT_BYTES:
            raise ValueError("document too large (limit 2 MB)")
        text = content
    doc = _parse(text)
    doc = {k: doc[k] for k in ("openapi", "info", "paths", "components") if k in doc}
    problems = validate_openapi(doc)
    if problems:
        raise ValueError("imported document is not usable OpenAPI 3.0: " + "; ".join(problems))
    return doc
