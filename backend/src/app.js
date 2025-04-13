const express = require("express");
const cors = require("cors");
const stockRoutes = require("./routes/stockRoute");
const newsRoutes = require("./routes/newsRoute");

const app = express();

// Middleware
app.use(express.json());
app.use(cors());

// Routes
app.use("/api/stocks", stockRoutes);
app.use("/api/news", newsRoutes);

module.exports = app;
