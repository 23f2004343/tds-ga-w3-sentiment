import asyncio
from playwright.async_api import async_playwright
import re

async def get_sum(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)
        
        try:
            # Wait for at least one table
            await page.wait_for_selector('table', timeout=10000)
        except Exception:
            pass

        # small wait to ensure JS is executed
        await page.wait_for_timeout(2000)

        # In Playwright, we can evaluate a script on the page
        table_sum = await page.evaluate(r'''() => {
            let total = 0;
            const tables = document.querySelectorAll('table');
            for (const table of tables) {
                const cells = table.querySelectorAll('td, th'); // th also sometimes contains numbers
                for (const cell of cells) {
                    const text = cell.innerText.trim();
                    if (text) {
                        const val = parseFloat(text);
                        if (!isNaN(val)) {
                            // Check if it's strictly a number or if we need more logic
                            if (/^-?[0-9]+(?:\.[0-9]+)?$/.test(text)) {
                                total += val;
                            }
                        }
                    }
                }
            }
            return total;
        }''')
        await browser.close()
        return table_sum

async def main():
    # As requested: Seeds 42, 43, 44, 45, 46, 47, 48, 49, 50, 51. 
    # That is range(42, 52)
    seeds = range(42, 52)
    total_sum = 0
    for seed in seeds:
        url = f"https://sanand0.github.io/tdsdata/js_table/?seed={seed}"
        try:
            s = await get_sum(url)
            print(f"Seed {seed}: {s}")
            if s is not None:
                total_sum += s
        except Exception as e:
            print(f"Failed for seed {seed}: {e}")
            
    print(f"Total sum over seeds 42-51: {total_sum}")

if __name__ == "__main__":
    asyncio.run(main())
