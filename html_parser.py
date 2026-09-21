"""
Parses the HTML to extract the links
"""


import lxml.html
from urllib.parse import urljoin
from url_utils import normalize_url
import os

BLACKLIST_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.webp', '.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.csv', '.xml', '.json',
    '.zip', '.tar', '.gz', '.rar', '.exe', '.bin', '.mp3', '.mp4', '.avi', '.mov', '.mkv', '.css', '.js', '.txt', '.gitignore',
    '.iso', '.dmg', '.apk', '.img', '.deb', '.rpm', '.pkg', '.msi', '.7z', '.bz2', '.xz', '.wasm'
}


def parse_html(html_content: str, absolute_url: str) -> set[str]:
    """
    Here is where I will parse the html and only accept valid hrefs. Inspects the content for <base> tags to resolve relative urls to absolute.
    This also parses out urls with invalid extensions

    Args:
        html_content:str
        absolute_url:str

    Returns:
        [] An array of unique normalized urls
    """

    if not html_content or not html_content.strip():
        return set()

    links_set = set()
    try:
        tree = lxml.html.fromstring(html_content)
        base_tag = tree.find('.//base')
        base_url = absolute_url
        if base_tag is not None and base_tag.get('href') and isinstance(base_tag.get('href'), str):
            base_url = urljoin(absolute_url, str(base_tag.get('href')).strip())

        for a in tree.iter('a'):
            link_str = a.get('href')
            if not link_str or not isinstance(link_str, str):
                continue

            normalized_url = normalize_url(urljoin(base_url, link_str))
            if 'cgi' in normalized_url["path"]:
                continue  # The cgi substring can be omitted here

            clean_url = normalized_url.get("url")
            root, ext = os.path.splitext(normalized_url.get("path", "/"))
            if (normalized_url.get("scheme") in ("https", "http")) and ext.lower() not in BLACKLIST_EXTENSIONS:
                links_set.add(clean_url)

    except Exception:
        return set()

    return links_set
