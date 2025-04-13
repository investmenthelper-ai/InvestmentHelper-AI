import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import TradingViewPage from "./pages/TradingViewPage/TradinViewPage";
import ScreenerPage from "./pages/ScreenerPage/ScreenerPage"
import NewsPage from "./pages/NewsPage/NewsPage";
import './global.css';
ReactDOM.createRoot(document.getElementById("app")!).render(
  <React.StrictMode>
    <Router>
      <Routes>
          <Route path="/" element={<ScreenerPage />} />
          <Route path="/screener" element={<ScreenerPage />} />
          <Route path="/tradingview/:stockId" element={<TradingViewPage />} />
          <Route path="/news" element={<NewsPage />} />
      </Routes>
    </Router>
  </React.StrictMode>
);
