import ssl
import urllib.request
import re

url = "https://sanand0.github.io/tdsdata/crawl_html/"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    html = urllib.request.urlopen(req, context=ctx).read().decode('utf-8')
    
    # Extract all href links that end with .html
    links = re.findall(r'href=[\'"]([^\'"]+\.html)[\'"]', html)
    
    # Filter links starting with O-Y (case-insensitive)
    # The links might be relative like "O/something.html" or just "object.html"
    # Even if they are in subdirectories, we usually look at the filename itself.
    # The prompt says: "Its crawler stores HTML files in alphabetized folders. Estimate workload by counting how many files fall between letters O and Y... files begin with letters from O to Y?"
    # If the file is 'O/foo.html' or 'orange.html'. I'll look at just the base filename.
    
    count = 0
    matched_files = []
    
    for link in links:
        # get base filename
        filename = link.split('/')[-1]
        if not filename:
             continue
        first_letter = filename[0].upper()
        
        # Check if first letter is between O and Y (inclusive)
        if 'O' <= first_letter <= 'Y':
            count += 1
            matched_files.append(filename)
            
    print(f"Total links found: {len(links)}")
    print(f"Files starting with O-Y: {count}")
    print("Sample matched:", matched_files[:5])

except Exception as e:
    print(f"Error: {e}")
