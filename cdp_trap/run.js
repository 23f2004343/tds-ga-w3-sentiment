const puppeteer = require('puppeteer');

(async () => {
    const browser = await puppeteer.launch({ headless: 'new' });
    const page = await browser.newPage();

    let errorPages = new Set();
    let firstErrorPage = null;

    page.on('pageerror', err => {
        const currentUrl = page.url();
        const pageNameMatch = currentUrl.match(/([^\/?#]+)(?:\?|#|$)/);
        const pageName = pageNameMatch ? pageNameMatch[1] : 'unknown';
        errorPages.add(pageName);
        if (!firstErrorPage) {
            firstErrorPage = pageName;
        }
    });

    const startUrl = 'https://sanand0.github.io/tdsdata/cdp_trap/index.html?student=23f2004343%40ds.study.iitm.ac.in';
    const baseUrl = 'https://sanand0.github.io/tdsdata/cdp_trap/';

    let queue = [startUrl];
    let visited = new Set();

    while (queue.length > 0) {
        let currentUrl = queue.shift();

        // Remove any hash fragments for comparison
        let normalizedUrl = currentUrl.split('#')[0];

        if (visited.has(normalizedUrl)) {
            continue;
        }

        visited.add(normalizedUrl);
        await page.goto(currentUrl, { waitUntil: 'load' });

        // Wait 3000ms to catch async errors
        await new Promise(r => setTimeout(r, 4000));

        // Extract links
        const links = await page.evaluate(() => {
            return Array.from(document.querySelectorAll('a')).map(a => a.href);
        });

        for (let link of links) {
            if (link.startsWith(baseUrl)) {
                let nLink = link.split('#')[0];
                if (!visited.has(nLink) && !queue.includes(link)) {
                    queue.push(link);
                }
            }
        }
    }

    console.log(`TOTAL_PAGES_VISITED=${visited.size}`);
    console.log(`TOTAL_ERRORS=${errorPages.size}`);
    console.log(`FIRST_ERROR_PAGE=${firstErrorPage || 'None'}`);

    await browser.close();
})();
