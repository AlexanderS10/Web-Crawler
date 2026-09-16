from ddgs import DDGS

def get_search_seeds(query: str, max_results: int = 10) -> list[str]:
    seeds = []
    try:
        # Using context manager preserves cookies and connection pooling
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=max_results)
            if results:
                for r in results:
                    url = r.get("href")
                    if url:
                        seeds.append(url)
    except Exception as e:
        print(f"Search warning: {e}")

    return seeds
