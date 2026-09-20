"""
Crawler Logger with thread safe logic so to log a lock should be acquired
"""

import csv
import threading
from typing import Optional


class CrawlLogger:
    """
    Thread safe csv writter for logging the results of http requests with their required metrics.
    """
    HEADERS = [
        "url",
        "size",
        "access_time",
        "return_code",
        "page_score",
        "domain_score",
        "depth"
    ]

    def __init__(self, filepath: str = "crawl_log.csv"):
        """
        Initializes the csv file and writes the headers out

        Args:
            Optional file name but the default is set
        """

        self.filepath = filepath
        self.lock = threading.Lock()
        self.file = open(filepath, mode="w", newline="", encoding="utf-8")
        self.writer = csv.writer(self.file)
        self.writer.writerow(self.HEADERS)
        self.file.flush()

    def log(self, url: str, size_bytes: int, access_time: str, return_code: int, page_score: float, domain_score: float, depth: int) -> None:
        """
        Writes the row to the csv file

        Args:
            url:str = Visited page URL
            size_bytes:int = Content size of the response body in bytes
            access_time:str = Timestamp of access formatted as 'YYYY-MM-DD HH:MM:SS'
            return_code:int = HTTP status code or 0 for transport failure
            page_score:float = Page novelty score
            domain_score: Superdomain novelty score
            depth: BFS graph distance from seed pages
        """
        with self.lock:
            self.writer.writerow([
                url,
                size_bytes,
                access_time,
                return_code,
                f"{page_score:.3f}",
                f"{domain_score:.3f}",
                depth,
            ])
            self.file.flush()

    def close(self) -> None:
        with self.lock:
            if not self.file.closed:
                self.file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
