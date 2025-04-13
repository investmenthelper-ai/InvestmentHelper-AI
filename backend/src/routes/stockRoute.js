const express = require("express");
const stockController = require("../controllers/stockController");

const router = express.Router();

// Route to get stock data
router.get("/", stockController.getStockData);

module.exports = router;
