import urllib.request
from urllib.parse import urljoin
import re
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

base_url = "https://sanand0.github.io/tdsdata/crawl_html/"

visited = set()
queue = [base_url]
html_files = set()

while queue:
    url = queue.pop(0)
    if url in visited:
        continue
    visited.add(url)
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        res = urllib.request.urlopen(req, context=ctx)
        html = res.read().decode('utf-8')
        
        # We also want to record this file if it's an HTML file
        if url.endswith('.html'):
            html_files.add(url)
            
        links = re.findall(r'href=[\'"]([^\'"]+\.html)[\'"]', html)
        for link in links:
            full_url = urljoin(url, link)
            if full_url.startswith(base_url) and full_url not in visited:
                queue.append(full_url)
                
    except Exception as e:
        print(f"Error crawling {url}: {e}")

print(f"Total HTML files crawled: {len(html_files)}")
# Let's count how many file base names start with O-Y
count = 0
matched = []
for url in html_files:
    # get base filename
    filename = url.split('/')[-1]
    if not filename:
        continue
    first_letter = filename[0].upper()
    if 'O' <= first_letter <= 'Y':
        count += 1
        matched.append(filename)

print(f"Total starting with O-Y: {count}")
print("Matched files:", sorted(matched))
