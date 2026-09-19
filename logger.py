import csv
import threading
import time
from typing import Optional


class CrawlLogger:
    """
    Decided to add a class for the logger and use a lock 
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
        self.filepath = filepath
        self.lock = threading.Lock()
        self.file = open(filepath, mode="w", newline="", encoding="utf-8")
        self.writer = csv.writer(self.file)
        self.writer.writerow(self.HEADERS)
        self.file.flush()

    def log(self, url: str, size_bytes: int, access_time: str, return_code: int, page_score: float, domain_score: float, depth: int) -> None:
        """
        Write the row to the document
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
