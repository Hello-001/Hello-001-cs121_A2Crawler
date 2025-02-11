import re
from urllib.parse import urlparse, urljoin, quote
import urllib.robotparser
from bs4 import BeautifulSoup

# testing if push/pull works

def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp):
    links = set()  # using a set here would avoid duplicates
    # although the project specification says to use a list, I think a set is better here
    # in the end, we can convert the set back into a list, which may seem inefficient 
    # converting a set to list is O(n) and it's simpler to implement
    # meanwhile having duplication checks in a list would be O(n) as well but more complex implementation
    
    # check if the response is valid and has a raw response
    try:
        if resp.status != 200 or not resp.raw_response:
            return []
        
        # here we use BeautifulSoup to parse the HTML content as professor 
        soup = BeautifulSoup(resp.raw_response.content, "html.parser")

        # find all the anchor tags in the HTML content
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"].strip()

            # resolve relative URLs
            absolute_link = urljoin(url, href).split("#")[0]  # Remove fragments

            # quote the URL to handle special characters
            absolute_link = quote(absolute_link, safe=":/?=&")
            # calling is_valid and is_crawler_trap to check if the URL is valid and not a crawler trap
            # this should work as long as is_valid is implemented correctly
            # was having problems earlier but it should be good now? KEEP WATCH
            if is_valid(absolute_link) and not is_crawler_trap(absolute_link):
                ###############################################
                # addind something for the robots.txt
                url_added = urllib.robotparser.RobotFileParse()
                if url_added.can_fetch('*', absolute_link):
                    url_added.set_url(f'{absolute_link}/robot.txt')
                    links.add(url_added)
                else:
                    links.add(absolute_link)
        
    # catch any exceptions that may occur during the parsing nicely
    except Exception:
        pass # could include sum error message here later

    # except Exception is too broad can implement more specific error checking later

    return list(links)  # finally i convert set back to list before returning

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
    if re.search(r"(date=|year=|month=|day=|calendar=)", parsed.query, re.IGNORECASE):
        return True
    # this one will redirect loops, which are URLs containing redirect or similar keywordss
    if "redirect" in parsed.path.lower() or "redirect" in parsed.query.lower(): # check if its in the path or the query too
        return True
    return False
