from html_parser import parse_html
from fetcher import fetcher, RobotsCache
from queue import Queue
import heapq
import math
from url_utils import normalize_url, extract_domain_info
from collections import defaultdict, deque
from dataclasses import dataclass, field

@dataclass
class DomainInfo:
    queue:deque = field(default_factory=deque)
    pages:int = 0
    superdomain:str = ""
    status:str = "idle"
    def add_item(self, value:tuple[str,int], pages, superdomain, status):
        self.queue.append(value)
        self.pages = pages
        self.superdomain = superdomain
        self.status=status
        
class CrawlQueue:
    def __init__(self, seed_urls):
        self.priority_heap = []
        self.politeness_heap = []
        self.domain_table = defaultdict(DomainInfo)
        self.superdomain_counts = defaultdict(int)
        
    def novelty_score(self, p:int, s:int):
        return (1/(math.log2(p+2))) + (1/(math.log2(s+2))) #the benefit of new domains is higher
    def add_to_priority(self, domain:str):
        domain_obj = self.domain_table[domain]
        if not domain_obj: #if the domain is not being tracked then add it with the max score
            heapq.heappush(self.priority_heap,(self.novelty_score(0,0), domain))
        #if the domain exists then we have to get the counts
        return
    def add_url(self, url:str, depth:int):
        domain_info = extract_domain_info(url)
        if not domain_info:
            return
        full_domain, superdomain=domain_info
        domain_obj=self.domain_table.get(full_domain)
        if domain_obj:
            if domain_obj.status == "idle":
                domain_obj.status = "in_priority"
                score = self.novelty_score(domain_obj.pages, self.superdomain_counts[domain_obj.superdomain])
                heapq.heappush(self.priority_heap,(-score, full_domain))
            domain_obj.queue.append((url, depth))
            #the superdomain must be there
        else:
            novelty_score = self.novelty_score(0,0)
            self.domain_table[full_domain].add_item((url,depth),0, superdomain, "in_priority") #the pages is 0 as they are not crawled yet
            heapq.heappush(self.priority_heap,(-novelty_score, full_domain))
            super_counter = self.superdomain_counts.get(superdomain)
            if not super_counter:
                self.superdomain_counts[superdomain]=0
                
        
    

def main():
    robots_cache = RobotsCache()
    seen_urls = set()
    limit = 10
    queue:Queue[tuple[str,int]]= Queue()
    counter =0
    seed_test = normalize_url("https://falexsanchez.com")
    queue.put((seed_test["url"], 0))
    while counter < limit and not queue.empty():
        url, depth = queue.get()
        if url in seen_urls:
            continue
        seen_urls.add(url)
        result = fetcher(url, robots_cache)
        if not result:
            continue
        counter+=1
        status_code, content_size, full_url, links = result
        print(f"{counter}. {full_url}, status:{status_code}, size: {content_size}, depth: {depth}")
        if full_url not in seen_urls:
            seen_urls.add(full_url) #THis is the final url in case of redirects so needs to be added to seen
        if links: 
            for link in links:
                child_depth = depth + 1
                queue.put((link, child_depth))
            

if __name__ == "__main__":
    main()