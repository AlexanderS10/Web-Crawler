from html_parser import parse_html
from fetcher import fetcher, RobotsCache
from urllib.robotparser import RobotFileParser
import requests
from urllib.parse import urlsplit


def main():
    robots_cache = RobotsCache()
    r = fetcher('http://localhost:4321', robots_cache)


if __name__ == "__main__":
    main()
