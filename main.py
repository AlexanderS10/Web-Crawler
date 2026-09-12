from html_parser import parse_html
from fetcher import fetcher, RobotsCache
from urllib.robotparser import RobotFileParser
from queue import Queue
from urllib.parse import urlsplit
from html_parser import normalize_url

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
                depth +=1
                queue.put((link, depth))
            

if __name__ == "__main__":
    main()