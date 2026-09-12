# Crawler Architecture

## Packages installed that are third-party

1. beautifulsoup4: This is for extracting the hyperlinks rather than a custom parser

2. tldextractz: Extract the superdomains from subdomains for the accurate count

3. duckduckgo_search: This will be the search engine used for the seed since it is free.

## The crawler architecture

The idea of this crawler is a hybrid system where:

### Data Structures

* Main data structure is a priority heap for the domains with the score rank.

* Domain table holding a FIFI queue holding the urls pointing to the domain that still need to be downloaded (DomainInfo)

* Politeness heap where I will put domains crawled so they cooldown to not spam them.

* Seen set so a page is not re-crawled

* Super domain table where a count of the super domains is kept that will be used for the score

* Robots table holding the cache of a robots.txt so it is not reparsed all the time or fetched

### Concurrency

* Single threading.Lock protecting the heaps and dictionaries. The domain table will have a status field so a domain cannot be put in the heap multiple times.

* A worker only acquires the lock to pop or push into the data structures and not while waiting the request's response.

### Flow

1. Check if the politeness heap has a current_time >= ready_time and if this is true then move it to the Priority heap.

2. Pop the top of the Priority Queue and mark it as Active. Pop the next item in the FIFO queue.

3. Request and Robots: This is outside the locks and this checks the cache for the existence of the robots.txt file or fetches it. Requests the page with a strict timeout. Verify it is the correct type: Html or txt.

4. Parse the html using the beautifulsoup4 package to extract urls.

    * TODO: Handle the fact that some are relative urls so they need to be joined.

5. Update State (under a lock).

    * For each discovered link that is not in the Seen set we add it to the Domain Table and increment the depth + 1 to keep track of it. We also add it to the seen set as that would prevent a new record from coming to it.

    * Increment the superdomain count

    * Compute the new novelty score: Novelty(Domain) - Penalty(Superdomain)

    * If the domain has urls then it gets placed into the politeness heap or if epty mark it as dormant

6. Log access is logging to the text file or log file as the assignment required (URL, size, timestamp, return code, priority score, depth).
