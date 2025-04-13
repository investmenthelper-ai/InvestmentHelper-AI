const { fetchYahooFinanceNews,fetchIstanbulMarketNews } = require("../services/newsServices");

const getAllFinanceNews = async (req, res) => {
    try {
        const news = await fetchYahooFinanceNews();
        res.json(news);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
};

const getIstanbulMarketNews = async (req, res) => {
    try {
        const news = await fetchIstanbulMarketNews();

        if (!news.length) {
            return res.status(404).json({ message: "No Istanbul market news found" });
        }

        res.json(news);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
};



module.exports = { getAllFinanceNews,getIstanbulMarketNews };
