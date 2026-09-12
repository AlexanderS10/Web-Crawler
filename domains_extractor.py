import tldextract

def extract_domain_info(url:str)->tuple[str,str]:
    value = tldextract.extract(url)
    superdomain = f"{value.domain}.{value.suffix}"
    if not value.suffix:
        superdomain = value.domain or "localhost" #my test gave me empty values on localhost or ips
    full_domain = value.fqdn or superdomain
    return (full_domain, superdomain)

if __name__=="__main__":
    print(extract_domain_info("https://news.bbc.co.uk/sport"))
