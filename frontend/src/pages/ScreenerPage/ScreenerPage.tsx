import React, { useState, useEffect } from "react";
import axios from "axios";
import { Table, Tabs, Input, Spin, Card, Row, Col } from "antd";
import {LineChart, Line, ResponsiveContainer, YAxis} from "recharts";
import { StarOutlined, StarFilled, SearchOutlined, RiseOutlined, FallOutlined } from "@ant-design/icons";
import Navbar from "../../Components/Navbar/Navbar";
import type { ColumnsType } from "antd/es/table";
import { useNavigate } from "react-router-dom";
import "./ScreenerPage.css";




const { TabPane } = Tabs;

// Sample market index data with graph points
const marketData = [
    {
        name: "S&P 500",
        value: "5,648.40",
        change: "+0.44%",
        graphData: [{ value: 5600 }, { value: 5625 }, { value: 5648 }, { value: 5640 }, { value: 5650 }],
    },
    {
        name: "Nasdaq 100",
        value: "17,713.53",
        change: "+1.13%",
        graphData: [{ value: 17600 }, { value: 17680 }, { value: 17713 }, { value: 17700 }, { value: 17750 }],
    },
    {
        name: "VIX",
        value: "15.00",
        change: "-4.15%",
        graphData: [{ value: 16.5 }, { value: 15.8 }, { value: 15.0 }, { value: 14.9 }, { value: 14.5 }],
    },
];


// Table columns
const columns: ColumnsType<any> = [
    { title: "#", dataIndex: "key", width: 50 },
    {
        title: "Company",
        dataIndex: "company",
        render: (text, record) => (
            <div>
                <strong>{text}</strong>
                <div style={{ fontSize: "0.8rem", color: "#888" }}>{record.ticker}</div>
            </div>
        ),
    },
    { title: "Price", dataIndex: "price", render: (price) => `$${price.toFixed(2)}` },
    {
        title: "1D %",
        dataIndex: "day",
        render: (value) => (
            <span style={{ color: value >= 0 ? "green" : "red", fontWeight: "bold" }}>
                {value > 0 ? `+${value.toFixed(2)}%` : `${value.toFixed(2)}%`}
            </span>
        ),
    },
    {
        title: "1M %",
        dataIndex: "month",
        render: (value) => (
            <span style={{ color: value >= 0 ? "green" : "red", fontWeight: "bold" }}>
                {value > 0 ? `+${value.toFixed(2)}%` : `${value.toFixed(2)}%`}
            </span>
        ),
    },
    {
        title: "YTD %",
        dataIndex: "year",
        render: (value) => (
            <span style={{ color: value >= 0 ? "green" : "red", fontWeight: "bold" }}>
                {value > 0 ? `+${value.toFixed(2)}%` : `${value.toFixed(2)}%`}
            </span>
        ),
    },
    { title: "M Cap", dataIndex: "marketCap" },
];




const ScreenerPage: React.FC = () => {
    const [stockData, setStockData] = useState([]);
    const [filteredData, setFilteredData] = useState([]);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();
    const handleRowClick = (record: any) => {
        navigate(`/tradingView/${record.ticker}`); // Redirect to TradingViewPage with ticker
    };
    const onSearch = (value: string) => {
        const filtered = stockData.filter((item) =>
            item.company.toLowerCase().includes(value.toLowerCase())
        );
        setFilteredData(filtered);
    };

    useEffect(() => {
        const fetchData = async () => {
            try {
                setLoading(true); // start loading
                const res = await axios.get("http://localhost:5000/api/stocks/");
                const withKeys = res.data.map((item, index) => ({
                    ...item,
                    key: index + 1,
                    day: item.dayChange,
                    month: item.monthChange * 100,
                    year: item.yearChange * 100,
                }));
                setStockData(withKeys);
                setFilteredData(withKeys);
            } catch (error) {
                console.error("Failed to fetch stock data", error);
            } finally {
                setLoading(false); // end loading
            }
        };

        fetchData();
    }, []);

    return (
        <div className="screener-page">
            {/* Navbar */}
            <Navbar />

            {/* Market Cards */}
            <div className="market-cards">
                <Row justify="center" style={{  gap: "24px 24px" }}> {/* Add consistent gap */}
                    {marketData.map((item, index) => (
                        <Col key={index} xs={24} sm={12} md={8} lg={6} style={{ display: "flex", justifyContent: "center" }}>
                            <div className="market-card">
                                <div className="market-title">{item.name}</div>
                                <div className="market-value">{item.value}</div>
                                <div
                                    className={`market-change ${
                                        item.change.startsWith("-") ? "negative" : "positive"
                                    }`}
                                >
                                    {item.change}
                                </div>
                                <div style={{cursor: "pointer"}}> {/* Add cursor style here */}
                                    <ResponsiveContainer width="100%" height={40}>
                                        <LineChart data={item.graphData}>
                                            <YAxis hide domain={["dataMin - 1", "dataMax + 1"]}/>
                                            <Line
                                                type="monotone"
                                                dataKey="value"
                                                stroke={item.change.startsWith("-") ? "red" : "green"}
                                                dot={false}
                                                strokeWidth={2}
                                            />
                                        </LineChart>
                                    </ResponsiveContainer>
                                </div>
                            </div>
                        </Col>
                    ))}
                </Row>
            </div>

            {/* Tabs */}
            <div className="screener-tabs">
                <Tabs defaultActiveKey="1">
                    <TabPane tab="Companies" key="1">
                        <Spin spinning={loading}>
                            <div className="screener-header">
                                <Input
                                    placeholder="Search..."
                                    prefix={<SearchOutlined />}
                                    onChange={(e) => onSearch(e.target.value)}
                                    style={{ width: "300px", marginBottom: "1rem" }}
                                />
                            </div>
                            <Table
                                columns={columns}
                                dataSource={filteredData}
                                pagination={false}
                                rowKey="key"
                                onRow={(record) => ({
                                    onClick: () => handleRowClick(record),
                                    style: { cursor: "pointer" },
                                })}
                            />
                        </Spin>
                    </TabPane>
                    <TabPane tab="Sectors" key="2">
                        <p>Sector data...</p>
                    </TabPane>
                    <TabPane tab="Industries" key="3">
                        <p>Industry data...</p>
                    </TabPane>
                    <TabPane tab="Trending" key="4">
                        <p>Trending data...</p>
                    </TabPane>
                    <TabPane tab="Gainers & Losers" key="5">
                        <p>Gainers & Losers data...</p>
                    </TabPane>
                    <TabPane tab="Most Visited" key="6">
                        <p>Most visited data...</p>
                    </TabPane>
                </Tabs>
            </div>
        </div>
    );
};

export default ScreenerPage;