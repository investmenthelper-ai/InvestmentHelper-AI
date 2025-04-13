const express = require("express");
const newsController = require("../controllers/newsController");

const router = express.Router();

// GET /api/news/:ticker
router.get("/", newsController.getAllFinanceNews);


// Route for Istanbul market news
router.get("/istanbul", newsController.getIstanbulMarketNews);

module.exports = router;
