import React, { useEffect, useRef, memo } from 'react';
import Navbar from '../../components/Navbar/Navbar';
import './TradingViewPage.css';

function TradingViewWidget() {
    const chartRef = useRef(null);

    useEffect(() => {
        const script = document.createElement("script");
        script.src = "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
        script.type = "text/javascript";
        script.async = true;
        script.innerHTML = `
        {
            "autosize": true,
            "symbol": "KCHOL",
            "interval": "D",
            "support_host": "https://www.tradingview.com",
            "timezone": "Etc/GMT+3",
            "theme": "light",
            "style": "1",
            "withdateranges": true,
            "hide_side_toolbar": false,
            "save_image": true,
            "show_popup_button": true,
            "popup_width": "1000",
            "popup_height": "650"
        }`;

        if (chartRef.current) {
            chartRef.current.innerHTML = "";
            chartRef.current.appendChild(script);
        }
    }, []);

    return (
        <div className="trading-view-page">
            <Navbar />
            <div className="chart-container">
                <div
                    ref={chartRef}
                    className="tradingview-widget-container"
                    style={{ width: '100%', height: '100%' }}
                >
                    <div className="tradingview-widget-container__widget" style={{ width: '100%', height: '100%' }}></div>
                </div>
            </div>
        </div>
    );
}

export default memo(TradingViewWidget);
