from html_parser import parse_html
from fetcher import fetcher, RobotsCache
from queue import Queue
import heapq
import math
from url_utils import normalize_url, extract_domain_info
from collections import defaultdict, deque
from dataclasses import dataclass, field
import time
import threading


@dataclass
class DomainInfo:
    queue: deque = field(default_factory=deque)
    pages: int = 0
    superdomain: str = ""
    status: str = "idle"

    def add_item(self, value: tuple[str, int], pages, superdomain, status):
        self.queue.append(value)
        self.pages = pages
        self.superdomain = superdomain
        self.status = status


class CrawlQueue:
    def __init__(self, seed_urls):
        self.lock = threading.Lock()
        self.priority_heap: list = []
        self.politeness_heap: list = []
        self.domain_table = defaultdict(DomainInfo)
        self.superdomain_counts = defaultdict(int)
        self.seen_urls: set[str] = set()
        self.active_workers: int = 0

        if seed_urls:
            for url in seed_urls:
                clean_url = normalize_url(url)["url"]
                self.add_url(clean_url, 0)

    def novelty_score(self, p: int, s: int):
        # the benefit of new domains is higher
        return (1/(math.log2(p+2))) + (1/(math.log2(s+2)))

    def add_to_priority(self, domain: str):
        domain_obj = self.domain_table[domain]
        if not domain_obj:  # if the domain is not being tracked then add it with the max score
            heapq.heappush(self.priority_heap,
                           (self.novelty_score(0, 0), domain))
        # if the domain exists then we have to get the counts
        return

    def add_url(self, url: str, depth: int):
        if not url or not isinstance(url, str):
            return False
        clean_url = normalize_url(url)["url"]
        domain_info = extract_domain_info(clean_url)
        if not domain_info:
            return False
        full_domain, superdomain = domain_info
        # Threading lock
        with self.lock:
            if clean_url in self.seen_urls:
                return False
            self.seen_urls.add(clean_url)
            if full_domain in self.domain_table:
                domain_obj = self.domain_table[full_domain]
                domain_obj.queue.append((clean_url, depth))

                # sleeping domain
                if domain_obj.status == "idle":
                    domain_obj.status = "in_priority"
                    score = self.novelty_score(
                        domain_obj.pages, self.superdomain_counts[domain_obj.superdomain])
                    heapq.heappush(self.priority_heap, (-score, full_domain))
            else:  # New domain
                if superdomain not in self.superdomain_counts:
                    self.superdomain_counts[superdomain] = 0
                new_domain = DomainInfo(
                    superdomain=superdomain, status="in_priority")
                new_domain.queue.append((clean_url, depth))
                self.domain_table[full_domain] = new_domain
                score = self.novelty_score(
                    0, self.superdomain_counts[superdomain])
                heapq.heappush(self.priority_heap, (-score, full_domain))
            return True

    def get_url(self) -> tuple[str | None, int, str | None, float]:
        """
        Returns url, depth, domain, wait_time (taking into consideration the politeness and novelty scores)

        Returns None if there is no url to crawl
        """
        with self.lock:
            now = time.monotonic()
            # check if there is a url in the politeness heap and put it back in the priority heap
            while self.politeness_heap and self.politeness_heap[0][0] <= now:
                ready_time, domain = heapq.heappop(self.politeness_heap)
                domain_obj = self.domain_table[domain]
                score = self.novelty_score(
                    domain_obj.pages, self.superdomain_counts[domain_obj.superdomain])
                heapq.heappush(self.priority_heap, (-score, domain))
                domain_obj.status = "in_priority"
            # if the domain is ready in priority then can be popped
            if self.priority_heap:
                neg_score, domain = heapq.heappop(self.priority_heap)
                domain_obj_priority = self.domain_table[domain]
                url, depth = domain_obj_priority.queue.popleft()
                domain_obj_priority.status = "active"
                self.active_workers += 1
                return url, depth, domain, 0.0
            # edge case if no domain in the priority heap but some in the politeness
            if self.politeness_heap:
                earliest_ready = self.politeness_heap[0][0]
                wait_time = max(earliest_ready - now, 0.05)
                return None, 0, None, wait_time
            # edge case where heaps are empty but workers are going at it
            if self.active_workers > 0:
                return None, 0, None, 0.1

            return None, 0, None, -0.1

    def finish_url(self, domain: str, delay: float = 1.0):
        """
         To be called after the url has been downloaded for a domain, this will update the counters and move the domain to politeness
        """
        with self.lock:
            self.active_workers-=1
            domain_obj = self.domain_table[domain]
            domain_obj.pages += 1
            self.superdomain_counts[domain_obj.superdomain] += 1
            if len(domain_obj.queue) > 0:
                ready_time = time.monotonic() + delay
                heapq.heappush(self.politeness_heap, (ready_time, domain))
                domain_obj.status = "in_politeness"
            else:
                domain_obj.status = "idle"


def main():
    robots_cache = RobotsCache()
    seen_urls = set()
    limit = 10
    queue: Queue[tuple[str, int]] = Queue()
    counter = 0
    seed_urls = ["https://falexsanchez.com"]
    crawl_queue = CrawlQueue(seed_urls)
    while counter < limit:
        item = crawl_queue.get_url()
        if not item:
            print("Empty queue of urls")
            break
        url, depth, domain = item

        if url in seen_urls:
            continue
        seen_urls.add(url)

        result = fetcher(url, robots_cache)
        crawl_queue.finish_url(domain, 1.0)
        if not result:
            continue
        status, content_size, full_url, links = result
        # This will add the final url if redirects occured
        seen_urls.add(full_url)
        if status != 200:
            print(f"Failed to fetch {full_url} with status code {status}")
            continue
        counter += 1

        print(f"{counter}. url: {full_url}, size: {content_size}, depth:{depth}")
        # New urls are to be put in the url
        if links:
            child_depth = depth+1
            for link in links:
                if link not in seen_urls:
                    crawl_queue.add_url(link, child_depth)


if __name__ == "__main__":
    main()
