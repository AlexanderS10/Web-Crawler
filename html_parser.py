from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlsplit, urldefrag
import os

BLACKLIST_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.webp', '.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.csv', '.xml', '.json',
    '.zip', '.tar', '.gz', '.rar', '.exe', '.bin','.mp3', '.mp4', '.avi', '.mov', '.mkv','.css', '.js', '.txt'
}


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
        base_url = urljoin(absolute_url, base_tag.get('href').strip())
    else:
        base_url = absolute_url
    for link in soup.find_all('a'):
        link_str = link.get('href')
        if link_str and isinstance(link_str, str):
            link_str = urldefrag(urljoin(base_url, link_str)).url
            link_stripped = urlsplit(link_str)
            root, ext = os.path.splitext(link_stripped.path)
            if (link_stripped.scheme == "https" or link_stripped.scheme == "http") and ext.lower() not in BLACKLIST_EXTENSIONS:
                links_set.add(link_str)
    return links_set
