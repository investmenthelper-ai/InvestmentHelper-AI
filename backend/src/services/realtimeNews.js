const api = require("realtime-newsapi")();

// Listen for new articles in real time
api.on("articles", (articles) => {
    console.log("🔴 Real-Time News Update:");
    console.log(articles);
});

// Handle errors
api.on("error", (error) => {
    console.error("🚨 Real-Time API Error:", error);
});
