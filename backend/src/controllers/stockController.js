const stockService = require("../services/stockService");
const constants = require("../constants");

const getStockData = async (req, res) => {
    try {
        // Flatten all BIST100 symbols

        const sectors = constants["Borsa İstanbul"];
        const symbols = Object.values(sectors)
            .map(sector => Object.keys(sector))
            .flat();

        const stockData = await stockService.fetchStockData(symbols);
        res.json(stockData);
    } catch (error) {
        console.error("Error fetching BIST 100 stock data:", error.message);
        res.status(500).json({ error: "Failed to fetch BIST 100 stock data" });
    }
};

module.exports = {
    getStockData,
};
