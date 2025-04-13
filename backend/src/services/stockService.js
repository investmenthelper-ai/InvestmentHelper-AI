const yahooFinance = require("yahoo-finance2").default;

const normalizePrice = (quote) => {
    const price = quote.regularMarketPrice;
    const high = quote.fiftyTwoWeekHigh || 0;

    // Heuristic: price is likely in kuruş if it's 5x higher than 52W high and currency is TRY
    if (
        quote.currency === "TRY" &&
        price > 1000
    ) {
        return price / 1000;
    }

    return price;
};

const formatMarketCap = (num) => {
    if (num >= 1e9) return (num / 1e9).toFixed(2) + "B";
    if (num >= 1e6) return (num / 1e6).toFixed(2) + "M";
    return num.toString();
};

const fetchStockData = async (symbols) => {
    try {
        const results = await Promise.all(
            symbols.map(async (symbol) => {
                try {
                    const quote = await yahooFinance.quote(symbol);

                    const history1mo = await yahooFinance.historical(symbol, {
                        period1: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
                        interval: "1d",
                    });

                    const history1y = await yahooFinance.historical(symbol, {
                        period1: new Date(new Date().getFullYear(), 0, 1), // YTD
                        interval: "1d",
                    });

                    const calcChange = (data) => {
                        if (data && data.length > 1) {
                            const first = data.find(d => d.close !== null)?.close;
                            const last = [...data].reverse().find(d => d.close !== null)?.close;
                            if (first && last) return (last - first) / first;
                        }
                        return 0;
                    };

                    return {
                        ticker: quote.symbol,
                        company: quote.longName || quote.symbol,
                        price: normalizePrice(quote),
                        dayChange: quote.regularMarketChangePercent,
                        monthChange: calcChange(history1mo),
                        yearChange: calcChange(history1y),
                        marketCap: formatMarketCap(quote.marketCap),
                    };
                } catch (err) {
                    console.error(`Error fetching ${symbol}:`, err.message);
                    return null;
                }
            })
        );

        return results
            .filter(Boolean)
            .sort((a, b) => b.price - a.price); // sort descending by price

    } catch (error) {
        console.error("Error in fetchStockData:", error.message);
        throw new Error("Failed to fetch stock data");
    }
};

module.exports = {
    fetchStockData,
};
