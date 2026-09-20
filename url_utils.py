"""
URL Utilities Files

Provides helper functions for extracting the domains, super domains and normalizing urls (defragmentization)
"""

import tldextract
from urllib.parse import urlsplit, urlunsplit


def extract_domain_info(url: str) -> tuple[str, str] | None:
    """
    Extracts the full domains and the superdomains which uses tldextract to find them out.

    Args:
        url: str

    Retuns: 
        (full_domain, superdomain):tuple|None
        None if the urls does not have a valid domain/suffix
    """

    value = tldextract.extract(url)
    if not value.suffix or not value.domain:
        # my test gave me empty values on localhost or ips
        return None
    superdomain = f"{value.domain}.{value.suffix}"
    full_domain = value.fqdn or superdomain
    return (full_domain, superdomain)


def normalize_url(url: str) -> dict[str, str]:
    """
    Normalize the urls to lower cases and remove fragments like class ids

    Args:
        url:str

    Returns:
        {url:str, path:str, scheme:str}:dict
    """

    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    domain = parts.netloc.lower()
    path = parts.path
    if not path and (scheme in ("http", "https")):
        path = "/"
    fragment = ""
    return {"url": urlunsplit((scheme, domain, path, parts.query, fragment)), "path": path, "scheme": scheme}


if __name__ == "__main__":
    print(extract_domain_info("https://news.bbc.co.uk/sport"))
