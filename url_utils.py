import tldextract
from urllib.parse import urlsplit, urlunsplit

def extract_domain_info(url:str)->tuple[str,str]:
    """
    retuns: full_domain, superdomain
    """
    
    value = tldextract.extract(url)
    superdomain = f"{value.domain}.{value.suffix}"
    if not value.suffix:
        superdomain = value.domain or "localhost" #my test gave me empty values on localhost or ips
    full_domain = value.fqdn or superdomain
    return (full_domain, superdomain)


def normalize_url(url:str) -> dict[str,str]:
    """
    Normalize the urls to lower cases and remove fragments like class ids
    
    return a dict: url:str, path: str, scheme:str
    """
    
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    domain = parts.netloc.lower()
    path = parts.path
    if not path and (scheme in ("http", "https")):
        path = "/"
    fragment = ""
    return {"url":urlunsplit((scheme, domain, path, parts.query, fragment)), "path":path, "scheme":scheme}

if __name__=="__main__":
    print(extract_domain_info("https://news.bbc.co.uk/sport"))
