Alexander Sanchez, fas6502, Assignment 1

Files Manifest

    - main.py: Entry point, multi-threaded coordinator, priority/politeness queues.
    - fetcher.py: HTTP downloader with timeout handling and RobotsCache.
    - html_parser.py: Fast lxml.html parser, <base> tag handling, extension filtering.
    - url_utils.py: url normalization and tldextract superdomain extraction.
    - logger.py: Thread safe CSV crawl access logger.
    - search_util.py: DuckDuckGo query seed generator.
    - requirements.txt: Python dependencies.

Setup & Run Instructions
    
    - Python version tested (3.14)
    - Install the dependencies with: pip install -r requirements.txt
    - Execution: python3 main.py
    - Search: Type a query or hit enter to use the default links used for testing

Parameters

    - Threads counts and the limit of pages to be crawled is in main.py 

