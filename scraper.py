import re
from urllib.parse import urlparse, urljoin, unquote
import urllib.robotparser
from bs4 import BeautifulSoup
from simhash import Simhash

robots_cache = {}
visited_hashes = set()  # Store SimHashes instead of full URLs

def normalize_url(url):
    while True:
        decoded_url = unquote(url)
        if decoded_url == url:  # stop if no more decoding needed
            break
        url = decoded_url  

    url = url.lower().strip()  
    url = re.sub(r"/+", "/", url)  
    url = url.rstrip("/")  
    return url

def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

def fetch_robots_txt(domain):
    temp_value = f"https://{domain}/robots.txt"
    url_added = urllib.robotparser.RobotFileParser()
    url_added.set_url(temp_value)
    try:
        url_added.read()
        robots_cache[domain] = url_added
    except Exception:
        robots_cache[domain] = None  # Assume allowed if fetch fails

def extract_next_links(url, resp):
    links = set()
    try:
        if getattr(resp, 'status', None) != 200 or not getattr(resp, 'raw_response', None):
            return []

        url = normalize_url(url)

        # Compute SimHash of the page content
        page_text = BeautifulSoup(resp.raw_response.content, "html.parser").get_text()
        page_hash = Simhash(page_text).value

        # Check if a similar page already exists (near-duplicate detection)
        for existing_hash in visited_hashes:
            if Simhash(existing_hash).distance(Simhash(page_hash)) < 3:  # Allow small variations
                return []  # Skip duplicate page

        visited_hashes.add(page_hash)  # Store new page hash

        soup = BeautifulSoup(resp.raw_response.content, "html.parser")

        for anchor in soup.find_all("a", href=True):
            href = anchor["href"].strip()
            absolute_link = normalize_url(urljoin(url, href).split("#")[0])

            # **Keep ALL existing crawler trap checks**
            if is_crawler_trap(absolute_link):
                continue

            domain = urlparse(absolute_link).netloc
            if domain not in robots_cache:
                fetch_robots_txt(domain)

            if robots_cache.get(domain) and not robots_cache[domain].can_fetch('*', absolute_link):
                continue  # Skip if robots.txt blocks access

            links.add(absolute_link)

    except Exception:
        pass

    return list(links)

def is_valid(url):
    try:
        parsed = urlparse(url)

        # **Check all crawler trap conditions first!**
        if is_crawler_trap(url):
            return False  

        if parsed.scheme not in {"http", "https"}:
            return False

        allowed_domains = {"ics.uci.edu", "cs.uci.edu", "informatics.uci.edu", "stat.uci.edu"}
        if not any(parsed.netloc.endswith(domain) for domain in allowed_domains):
            return False  

        invalid_extensions = re.compile(
            r".*\.(css|js|bmp|gif|jpg|jpeg|png|tiff|mp2|mp3|mp4|wav|avi|mov|mpeg|doc|docx|xls|xlsx|ppt|pptx|zip|tar|gz|7z|iso)$",
            re.IGNORECASE,
        )
        if invalid_extensions.match(parsed.path):
            return False
        
        return True
    except Exception:
        return False

def is_crawler_trap(url):
    parsed = urlparse(url)
    decoded_query = unquote(parsed.query)  # Decode query before checking
    path_components = parsed.path.split("/")

    # **All original crawler trap checks remain**
    if len(path_components) > 10:
        return True

    if len(decoded_query) > 100:
        return True

    if re.search(r"%25{3,}", url) or re.search(r"%2[EFef]", url, re.IGNORECASE):
        return True

    if re.search(r"(%[0-9A-Fa-f]{2}){5,}", url):  # 5+ consecutive encodings
        return True

    if re.search(r"(session|sid|phpsessid|jsessionid|sessid|token)=[a-zA-Z0-9]+", decoded_query, re.IGNORECASE):
        return True

    if re.search(r"(tab_files|do|ns)=.*", decoded_query, re.IGNORECASE):
        return True  

    if re.search(r"(date|year|month|day|calendar)=\d{1,4}\b", decoded_query, re.IGNORECASE):
        return True

    if re.search(r"(date|year|month|day|calendar|event|events)", decoded_query, re.IGNORECASE):
        return True

    if "redirect" in parsed.path.lower() or "redirect" in decoded_query.lower():
        return True

    return False
