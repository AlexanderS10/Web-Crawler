from fetcher import fetcher, RobotsCache
import heapq
import math
from url_utils import normalize_url, extract_domain_info
from collections import defaultdict, deque
from dataclasses import dataclass, field
import time
import threading
from search_util import get_search_seeds
from logger import CrawlLogger


@dataclass
class DomainInfo:
    queue: deque = field(default_factory=deque)
    pages: int = 0
    superdomain: str = ""
    status: str = "idle"

    def add_item(self, value: tuple[str, int], pages, superdomain, status):
        self.queue.append(value)  # the queue has the url and the depth
        self.pages = pages
        self.superdomain = superdomain
        self.status = status


class CrawlQueue:
    W_Page: float = 1.0  # Wight for the pages within the same subdomain
    W_Super: float = 3.0  # Weight for the super domain (extra boost)

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
        page_term = 1/(math.log2(p+2))
        super_term = 1/(math.log2(s+2))
        return (self.W_Page * page_term) + (self.W_Super*super_term)

    def add_to_priority(self, domain: str):
        domain_obj = self.domain_table[domain]
        if not domain_obj:  # if the domain is not being tracked then add it with the max score
            heapq.heappush(self.priority_heap,
                           (self.novelty_score(0, 0), domain))
        # if the domain exists then we have to get the counts
        return

    def add_url(self, url: str, depth: int):
        """
        Here I add a url to the FIFO queue

        returns None
        """

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
                    pages=0, superdomain=superdomain, status="in_priority")
                new_domain.queue.append((clean_url, depth))
                self.domain_table[full_domain] = new_domain
                score = self.novelty_score(
                    0, self.superdomain_counts[superdomain])
                heapq.heappush(self.priority_heap, (-score, full_domain))
            return True

    def get_url(self) -> tuple[str | None, int, str | None, float, float, float]:
        """
        Returns url, depth, domain, page_score, domain_score, wait_time (taking into consideration the politeness and novelty scores)

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
                p = domain_obj_priority.pages
                s = self.superdomain_counts[domain_obj_priority.superdomain]
                page_score = self.W_Page / math.log2(p + 2)
                domain_score = self.W_Super / math.log2(s + 2)
                return url, depth, domain, page_score, domain_score, 0.0
            # edge case if no domain in the priority heap but some in the politeness
            if self.politeness_heap:
                earliest_ready = self.politeness_heap[0][0]
                wait_time = max(earliest_ready - now, 0.05)
                return None, 0, None, 0.0, 0.0, wait_time
            # edge case where heaps are empty but workers are going at it
            if self.active_workers > 0:
                return None, 0, None, 0.0, 0.0, 0.1

            return None, 0, None, 0.0, 0.0, -0.1

    def get_next_url_for_domain(self, domain: str):
        """
        This one is to pop the next url since robots blocking a url request should pop the next url in that domain
        """
        with self.lock:
            domain_obj = self.domain_table[domain]
            if domain_obj.queue:
                return domain_obj.queue.popleft()
            return None

    def finish_url(self, domain: str, delay: float = 1.0, success: bool = True):
        """
         To be called after the url has been downloaded for a domain, this will update the counters and move the domain to politeness
        """
        with self.lock:
            self.active_workers -= 1
            domain_obj = self.domain_table[domain]
            if success:
                domain_obj.pages += 1
                self.superdomain_counts[domain_obj.superdomain] += 1
            if len(domain_obj.queue) > 0:
                ready_time = time.monotonic() + delay
                heapq.heappush(self.politeness_heap, (ready_time, domain))
                domain_obj.status = "in_politeness"
            else:
                domain_obj.status = "idle"

    def mark_seen(self, url: str):
        "Moved this from main to keep the locks in the class"
        clean_url = normalize_url(url)["url"]
        with self.lock:
            self.seen_urls.add(clean_url)


def worker(worker_id: int, crawl_queue: CrawlQueue, robots_cache: RobotsCache, limit: int | None, shared_counter: list[int], counter_lock: threading.Lock, stop_event: threading.Event, crawl_logger: CrawlLogger):
    while not stop_event.is_set():
        url, depth, domain, page_score, domain_score, wait_time = crawl_queue.get_url()
        if url is None or domain is None:
            if wait_time < 0:
                stop_event.set()
                break
            time.sleep(min(wait_time, 0.5))
            continue

        while not robots_cache.can_crawl(domain, url):
            next_item = crawl_queue.get_next_url_for_domain(domain)
            if next_item is None:
                url = None
                break
            url, depth = next_item
        if url is None:  # if for soem reason all the urls in the queue were in robots
            crawl_queue.finish_url(domain, delay=0.0, success=False)
            continue
        result = fetcher(url)
        is_success = (result is not None and result[0] == 200)
        crawl_queue.finish_url(domain, 0.5, success=is_success)
        access_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        if not result:
            crawl_logger.log(url, 0, access_time, 0,
                             page_score, domain_score, depth)
            continue
        status, content_size, full_url, links = result
        crawl_queue.mark_seen(full_url)

        crawl_logger.log(url, content_size, access_time,
                         status, page_score, domain_score, depth)
        if status != 200:
            continue
        with counter_lock:
            shared_counter[0] += 1
            if limit is not None and shared_counter[0] >= limit:
                stop_event.set()
                break

        if links:
            child_depth = depth+1
            for link in links:
                crawl_queue.add_url(link, child_depth)


def main():
    robots_cache = RobotsCache()
    limit: int | None = 200
    threads_count: int = 20

    query = input("Search: ").strip()
    seed_urls = []
    if query:
        print("Fetching results")
        seed_urls = get_search_seeds(query, max_results=15)
        print(f"Returned {len(seed_urls)} results")
    else:
        seed_urls = [
            "https://en.wikipedia.org/wiki/IPhone_Duo",
            "https://www.apple.com/iphone-duo/",
            "https://www.apple.com/newsroom/2026/09/apple-unveils-iphone-duo/",
            "https://www.t-mobile.com/cell-phone/apple-iphone-duo",
            "https://www.apple.com/iphone-duo/specs/",
            "https://www.verizon.com/smartphones/apple-iphone-duo/",
            "https://mashable.com/tech/iphone-duo-foldable-announcement-apple-event-2026",
            "https://www.att.com/buy/phones/apple-iphone-duo.html",
            "https://www.cnn.com/2026/09/09/tech/apple-announces-iphone-duo-first-foldable-iphone",
            "https://www.techradar.com/phones/iphone/iphone-duo-hands-on",
            "https://www.gsmarena.com/apple_iphone_duo_fold-13804.php",
            "https://www.macrumors.com/2026/09/09/apple-announces-foldable-iphone-duo/",
            "https://www.tomsguide.com/phones/iphones/iphone-duo-hands-on-apple-nailed-it-and-just-put-everyone-else-on-notice",
            "https://www.macrumors.com/2026/09/09/iphone-duo-start-at-2000/",
            "https://www.cnet.com/tech/mobile/yes-the-iphone-duo-is-a-first-generation-phone-thats-why-you-should-get-one-if-you-can/"
        ]
    for seed in seed_urls:
        print(f"Seed url: {seed}")
    crawl_queue = CrawlQueue(seed_urls)
    shared_counter = [0]
    counter_lock = threading.Lock()
    stop_event = threading.Event()

    print(
        f"Starting the crawl with {threads_count} threads, and with a limit of {limit} pages")
    start_time = time.time()
    threads = []
    logger = CrawlLogger("crawl_log.csv")
    for i in range(threads_count):
        t = threading.Thread(target=worker, args=(
            i+1,
            crawl_queue,
            robots_cache,
            limit,
            shared_counter,
            counter_lock,
            stop_event,
            logger
        ))
        t.start()
        threads.append(t)
    # Added a keyboard interrupt to end all threads otherwise they will hang
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("Force stop: ending threads")
        stop_event.set()
        for t in threads:
            t.join()

    total_time = time.time() - start_time
    pages_crawled = shared_counter[0]
    rate = pages_crawled / total_time if total_time > 0 else 0
    print("CRAWL COMPLETE")
    print(f"Threads used: {threads_count}")
    print(f"Time: {total_time} seconds")
    print(f"Pages crawled: {pages_crawled}")
    print(f"Rate: {rate} pages per second")


if __name__ == "__main__":
    main()
