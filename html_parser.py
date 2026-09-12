from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlsplit, urldefrag, urlunsplit
import os

BLACKLIST_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.webp', '.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.csv', '.xml', '.json',
    '.zip', '.tar', '.gz', '.rar', '.exe', '.bin','.mp3', '.mp4', '.avi', '.mov', '.mkv','.css', '.js', '.txt'
}

def normalize_url(url:str) -> dict[str,str]:
    """
    Normalize the urls to lower cases and remove fragments like class ids
    
    return a dict: url:str, path: str, scheme:str
    """
    
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    domain = parts.netloc.lower()
    path = parts.path
    if not path and (scheme in ("http", "https")):
        path = "/"
    fragment = ""
    return {"url":urlunsplit((scheme, domain, path, parts.query, fragment)), "path":path, "scheme":scheme}
    
def parse_html(html_content, absolute_url):
    """
    Here is where I will parse the html and only accept valid hrefs
    https://beautiful-soup-4.readthedocs.io/en/latest/
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    links_set = set()
    base_tag = soup.find('base')
    base_url = ''
    if base_tag and base_tag.get('href') and isinstance(base_tag.get('href'),str):
        base_url = urljoin(absolute_url, str(base_tag.get('href')).strip())
    else:
        base_url = absolute_url
    for link in soup.find_all('a'):
        link_str = link.get('href')
        if link_str and isinstance(link_str, str):
            normalized_url = normalize_url(urljoin(base_url, link_str)) 
            link_str = normalized_url.get("url")
            root, ext = os.path.splitext(normalized_url.get("path","/"))
            if (normalized_url.get("scheme") == "https" or normalized_url.get("scheme") == "http") and ext.lower() not in BLACKLIST_EXTENSIONS:
                links_set.add(link_str)
    return links_set
