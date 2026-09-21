"""
Web Page fetches and the class for the RobotsCache using urllib.robotparser
"""

from html_parser import parse_html
import requests
from urllib.robotparser import RobotFileParser
from urllib.parse import urlsplit


DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
}
DEFAULT_TIMEOUT = (0.8, 2.5)


class RobotsCache:
    """
    In memory cache for the robots.txt file stored per domain for fast access.
    """

    def __init__(self, default_timeout=DEFAULT_TIMEOUT):
        """
        Initializes the robots cache.

        Args:
            default_timeout: Tuple of (connect_timeout, read_timeout) in seconds.
        """

        self.cache: dict = {}
        self.timeout = default_timeout
        self.user_agent: str = "*"

    def can_crawl(self, domain: str, url: str) -> bool:
        """
        Checks if the crawler is allowed to fetch a url by checking robots.txt.

        This also fetches the robots.txt files if not already in cache

        Args:
            domain: The hostname/FQDN of the website.
            url: The full URL to check permissions for.

        Returns:
            True if crawling is allowed or robots.txt is unavailable/empty; False otherwise.
        """
        if domain not in self.cache:
            self._fetch_robots_file(domain, url)
        return self.cache[domain].can_fetch(self.user_agent, url)

    def _fetch_robots_file(self, domain: str, url: str) -> None:
        """
        Downloads and parses the robots.txt file.

        If the server does not return a 200 response then it is parsed by empty rules and thus allowing crawling

        Args:
            domain: str
            url: str    Full url including the scheme. 
        """
        robot_parser = RobotFileParser()
        try:
            robots_req = requests.get(
                f"{urlsplit(url).scheme}://{domain}/robots.txt",
                headers=DEFAULT_HEADERS,
                timeout=self.timeout
            )
            if robots_req.status_code == 200:
                robot_parser.parse(robots_req.text.splitlines())
            else:
                robot_parser.parse([])
            self.cache[domain] = robot_parser
        except requests.RequestException as e:
            print("The robots.txt file failed to fetch")
            robot_parser.parse([])
            self.cache[domain] = robot_parser


def fetcher(url: str):
    """
    Args:
        url:str = The web page URL to retrieve.

    Returns:
        On Success -> tuple(status_code:int, content_lenght:int, final_url:str, links_set:[])

        On Error -> None
    """
    try:
        with requests.get(url, timeout=DEFAULT_TIMEOUT,
                          headers=DEFAULT_HEADERS, stream=True) as req:
            if req.status_code == 200:
                context_type = req.headers.get("Content-Type", "")
                if "text/html" in context_type:
                    content_length = req.headers.get("Content-Length")
                    try:
                        if content_length and int(content_length) > 10 * 1024 * 1024:
                            return (req.status_code, 0, req.url, None)
                    except ValueError:
                        pass
                    links = parse_html(req.text, req.url)
                    return (req.status_code, len(req.content), req.url, links)
                return (req.status_code, 0, req.url, None)  # 403 or 500 etc
            else:
                return (req.status_code, 0, req.url, None)
    except requests.exceptions.Timeout:
        print(f"Server took too long to respond")
        return
    except requests.exceptions.RequestException as e:
        print(f"The request gave a timeout {e}")
        return


if __name__ == "__main__":
    robots_cache = RobotsCache()
    fetcher("https://localhost:4321")
