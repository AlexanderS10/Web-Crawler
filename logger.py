"""
Crawler Logger with thread safe logic so to log a lock should be acquired
"""

from collections import defaultdict
import csv
import threading


class CrawlLogger:
    """
    Thread safe csv writter for logging the results of http requests with their required metrics.

    Fields:
        filepath:str = Path to the output csv log file
        lock:threading.Lock = Mutex lock protecting file writes and metric counters
        file:TextIOWrapper = File handle open for writing the csv log
        writer:csv.writer = CSV writer instance
        status_counts:dict[int, int] = Mapping of HTTP return code to total count (e.g. 200: 180, 404: 12, 0: 3)
        total_bytes:int = Running sum of content body sizes in bytes across all visited pages
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
            filepath:str = Optional file name but the default is set
        """

        self.filepath = filepath
        self.lock = threading.Lock()
        self.file = open(filepath, mode="w", newline="", encoding="utf-8")
        self.writer = csv.writer(self.file)
        self.writer.writerow(self.HEADERS)
        self.file.flush()
        self.status_counts: dict[int, int] = defaultdict(int)
        self.total_bytes: int = 0

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
            self.status_counts[return_code] += 1
            self.total_bytes += size_bytes
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

    def write_summary(self, total_time: float) -> None:
        """
        Writes crawl statistisc at the end of the log file and flushes it

        Args:
            total_time:float = Total execution time in seconds
        """
        with self.lock:
            self.file.write("\n CRAWL SUMMARY STATISTICS \n")
            self.file.write(f"Total Time Taken: {total_time:.2f} seconds\n")
            total_pages = sum(self.status_counts.values())
            self.file.write(f"Total URL Attempts Logged: {total_pages}\n")
            self.file.write(
                f"200 OK (Pages Crawled): {self.status_counts.get(200, 0)}\n")
            self.file.write(
                f"404 Not Found: {self.status_counts.get(404, 0)}\n")
            self.file.write(
                f"403 Forbidden: {self.status_counts.get(403, 0)}\n")
            self.file.write(
                f"Transport/Timeout Failures (Code 0): {self.status_counts.get(0, 0)}\n")
            other_codes = sum(
                v for k, v in self.status_counts.items() if k not in (200, 404, 403, 0))
            self.file.write(f"Other HTTP Statuses: {other_codes}\n")
            self.file.write(
                f"Total Data Downloaded: {self.total_bytes / (1024 * 1024):.2f} MB ({self.total_bytes} bytes)\n")
            rate = self.status_counts.get(
                200, 0) / total_time if total_time > 0 else 0
            self.file.write(f"Crawl Rate: {rate:.2f} pages per second\n")
            self.file.flush()

    def close(self) -> None:
        with self.lock:
            if not self.file.closed:
                self.file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
