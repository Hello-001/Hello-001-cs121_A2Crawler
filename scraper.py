import re
from urllib.parse import urlparse, urljoin, quote
import urllib.robotparser
from bs4 import BeautifulSoup

# testing if push/pull works

def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    links = []
    try:
        soup = BeautifulSoup(resp.raw_response.content, "html.parser")
        for anchor in soup.find_all("a", href=True):
            absolute_link = urljoin(url, anchor["href"])  # Convert relative links to absolute
            links.append(absolute_link)
    except Exception as e:
        print(f"Error extracting links from {url}: {e}")
    
    return links # // returns a list;

def is_valid(url):
    try:
        parsed = urlparse(url)
        # check if the URL is an HTTP or HTTPS link
        if parsed.scheme not in {"http", "https"}:
            return False

        # in the project requirement prof asks for us to only crawl the following domains
        # made a set of allowed domains to check if the URL belongs to one of them
        # if it doesn't belong to any of them, return False
        allowed_domains = {"ics.uci.edu", "cs.uci.edu", "informatics.uci.edu", "stat.uci.edu"}
        if not any(parsed.netloc.endswith(domain) for domain in allowed_domains):
            return False  
        # and this one excludes common non-HTML file formats
        invalid_extensions = re.compile(
            r".*\.(css|js|bmp|gif|jpg|jpeg|png|tiff|mp2|mp3|mp4|wav|avi|mov|mpeg|pdf|doc|docx|xls|xlsx|ppt|pptx|zip|tar|gz|7z|iso)$",
            re.IGNORECASE,
        )
        if invalid_extensions.match(parsed.path):
            return False
        
        return True
    except Exception:
        return False

def is_crawler_trap(url):
    parsed = urlparse(url) # parse the URL
    path_components = parsed.path.split("/") # split the path into components

    # this one simply avoids URLs with execessive repeating patterns
    # a bit iffy on these first two checks but hopefully works!
    if len(path_components) > 10:
        return True
    # this one just avoids URL with super long query parameters LOL
    # I'm not sure if this is a good idea but it's a simple check, aka dyanmic trap
    if len(parsed.query) > 100:
        return True
    # this will avoid session IDs in the URL like we learned in class where it has session, sid, phpsessid, jsessionid, sessid, or token in the query
    if re.search(r"(session|sid|phpsessid|jsessionid|sessid|token)=[a-zA-Z0-9]+", parsed.query, re.IGNORECASE):
        return True
    # this will avoid calendar traps like we learned in class where the URL has a date, year, month, day, or calendar in the query
    if re.search(r"(date|year|month|day|calendar)=\d{1,4}\b", parsed.query, re.IGNORECASE):
        return True
    if re.search('date|year|month|day|calender|event|events',parsed.query, re.IGNORECASE):
        return True
    # this one will redirect loops, which are URLs containing redirect or similar keywordss
    if "redirect" in parsed.path.lower() or "redirect" in parsed.query.lower(): # check if its in the path or the query too
        return True
    return False
