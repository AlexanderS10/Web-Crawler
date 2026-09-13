from bs4 import BeautifulSoup
from urllib.parse import urljoin 
from url_utils import normalize_url
import os

BLACKLIST_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.webp', '.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.csv', '.xml', '.json',
    '.zip', '.tar', '.gz', '.rar', '.exe', '.bin','.mp3', '.mp4', '.avi', '.mov', '.mkv','.css', '.js', '.txt', '.gitignore'
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
        base_url = urljoin(absolute_url, str(base_tag.get('href')).strip())
    else:
        base_url = absolute_url
    for link in soup.find_all('a'):
        link_str = link.get('href')
        if link_str and isinstance(link_str, str):
            normalized_url = normalize_url(urljoin(base_url, link_str)) 
            if 'cgi' in normalized_url["path"]:
                continue #The cgi substring can be ommitted here
            link_str = normalized_url.get("url")
            root, ext = os.path.splitext(normalized_url.get("path","/"))
            if (normalized_url.get("scheme") == "https" or normalized_url.get("scheme") == "http") and ext.lower() not in BLACKLIST_EXTENSIONS:
                links_set.add(link_str)
    return links_set
