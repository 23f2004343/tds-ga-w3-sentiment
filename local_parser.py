from PyPDF2 import PdfReader
import re

reader = PdfReader("expenses_23f2004343.pdf")
text = ""
for page in reader.pages:
    text += page.extract_text() + "\n"

print(f"Total pages read: {len(reader.pages)}")

# Match cases like 9Jan, Jan9, January 9, 9 January etc regardless of case
# A general regex that looks for '9' and 'jan' close to each other
pattern = re.compile(r'(?i)(?:9\s*jan\w*)|(?:jan\w*\s*9)')
matches = pattern.findall(text)

print(f"Raw regex hits across all text: {len(matches)}")

# To get exactly the values: we know each line contains a transaction
# format is typically: ID  Date  Category Amount Currency
total = 0.0
count = 0
for line in text.split('\n'):
    if pattern.search(line):
        count += 1
        # Extract the amount and currency at the end of the line
        parts = line.strip().split()
        if len(parts) >= 2:
            currency = parts[-1]
            try:
                amt = float(parts[-2])
                if currency.lower() in ['usd', 'dollar', 'dollars', '$', 'dollar(s)']:
                    total += amt * 80
                    #print(f"Found: {line} -> + {amt*80} Rs")
                else:
                    total += float(amt)
                    #print(f"Found: {line} -> + {amt} Rs")
            except ValueError:
                # might be formatted differently, try to find the numbers
                # print(f"Could not parse: {line}")
                pass

print(f"Found {count} specific lines")
print(f"Calculated Total (Rs): {total}")
