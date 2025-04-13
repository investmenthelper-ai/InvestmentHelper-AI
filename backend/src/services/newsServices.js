const yahooFinance = require("yahoo-finance2").default;

const puppeteer = require("puppeteer-extra");

const StealthPlugin = require("puppeteer-extra-plugin-stealth");

puppeteer.use(StealthPlugin())

const fetchYahooFinanceNews = async () => {
    try {
        const browser = await puppeteer.launch({
            headless: false, // Open browser for debugging
            args: ["--no-sandbox", "--disable-setuid-sandbox"],
        });

        const page = await browser.newPage();
        await page.setUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
        );

        // Prevent redirects
        await page.goto("https://finance.yahoo.com/", {
            waitUntil: "domcontentloaded",
            timeout: 60000,
            referer: "https://finance.yahoo.com",
        });

        // Block ads, images, and unnecessary resources
        await page.setRequestInterception(true);
        page.on("request", (req) => {
            if (["image", "stylesheet", "font", "script", "xhr"].includes(req.resourceType())) {
                req.abort();
            } else {
                req.continue();
            }
        });

        // Wait for news section to load
        await page.waitForSelector("h3 a", { timeout: 30000 });

        // Delay before scraping to prevent frame detachment
        await page.waitForTimeout(3000);

        const news = await page.evaluate(() => {
            let articles = [];
            document.querySelectorAll("div.js-stream-content h3 a").forEach((item) => {
                const title = item.innerText;
                const link = item.href.startsWith("http")
                    ? item.href
                    : `https://finance.yahoo.com${item.href}`;
                articles.push({ title, link });
            });

            return articles.slice(0, 20);
        });

        console.log("Scraped News:", news); // Debugging: Print news to console

        await browser.close();
        return news;
    } catch (error) {
        console.error("Yahoo Finance Scraping Error:", error);
        throw new Error("Failed to fetch Yahoo Finance news");
    }
};



const fetchIstanbulMarketNews = async () => {
    try {
        const response = await yahooFinance.search("Borsa Istanbul",{ count: 20 }); // Focus on Turkey
        return response.news || [];
    } catch (error) {
        console.error("Yahoo Finance API Error:", error);
        throw new Error("Failed to fetch Istanbul market news");
    }
};



module.exports = { fetchYahooFinanceNews,fetchIstanbulMarketNews };
