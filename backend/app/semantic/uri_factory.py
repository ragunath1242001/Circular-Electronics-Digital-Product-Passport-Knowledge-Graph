import re
import unicodedata

from rdflib import URIRef

RESOURCE_BASE = "https://example.org/dpp/resource/"


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    if not slug:
        raise ValueError("A stable URI cannot be generated from an empty identifier")
    return slug


def resource_uri(kind: str, identifier: str) -> URIRef:
    return URIRef(f"{RESOURCE_BASE}{slugify(kind)}/{slugify(identifier)}")

