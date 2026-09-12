from html_parser import parse_html
import requests
from urllib.robotparser import RobotFileParser
from urllib.parse import urlsplit

class RobotsCache:
    """
    The class for the cache object 
    """

    def __init__(self, default_timeout=3):
        self.cache:dict = {}
        self.timeout:int = default_timeout
        self.user_agent:str = "*"

    def can_crawl(self, domain:str, url:str) -> bool:
        if domain not in self.cache:
            self._fetch_robots_file(domain, url)
        return self.cache[domain].can_fetch(self.user_agent, url)

    def _fetch_robots_file(self, domain:str, url:str) -> None:
        robot_parser = RobotFileParser()
        try:
            robots_req = requests.get(
                f"{urlsplit(url).scheme}://{domain}/robots.txt", timeout=3)
            if robots_req.status_code == 200:
                robot_parser.parse(robots_req.text.splitlines())
            else:
                robot_parser.parse([])
            self.cache[domain] = robot_parser
        except requests.RequestException as e:
            print("The robots.txt file failed to fetch")
            robot_parser.parse([])
            self.cache[domain] = robot_parser

def fetcher(url:str, robots_cache:RobotsCache):
    try:
        domain = urlsplit(url).netloc
        if not robots_cache.can_crawl(domain,url):
            return
        req = requests.get(url, timeout=3)
        if req.status_code == 200:
            context_type = req.headers.get("Content-Type","")
            if "text/html" in context_type:
                links = parse_html(req.text, req.url)    
                return (req.status_code, len(req.content), req.url, links)
            return
        else:
            return (req.status_code, 0, req.url, None)
    except requests.exceptions.Timeout:
        print(f"Server took too long to respond")
    except requests.exceptions.RequestException as e:
        print(f"The request gave a timeout {e}")
    
if __name__== "__main__":
    robots_cache = RobotsCache()
    fetcher("https://localhost:4321", robots_cache)