const axios = require("axios");

const fetchNews = async (query) => {
    try {
        const response = await axios.post("https://api.newsfilter.io/public/actions", {
            type: "filterArticles",
            queryString: `title:${query} OR description:${query} OR symbols:${query}`,
        });

        console.log("🔍 Queried News Articles:");
        console.log(response.data);
    } catch (error) {
        console.error("🚨 Query API Error:", error.response ? error.response.data : error.message);
    }
};

// Fetch news for a specific stock or keyword
fetchNews("AAPL"); // Change "AAPL" to any stock symbol or keyword
ef577c1ad4fd404685c037567bb1d59d