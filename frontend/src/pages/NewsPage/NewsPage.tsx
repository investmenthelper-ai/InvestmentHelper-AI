import React, { useEffect, useState } from "react";
import { List, Card, Typography, Spin } from "antd";
import axios from "axios";

const { Title } = Typography;

const FinanceNews = () => {
    const [news, setNews] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchNews = async () => {
            try {
                const response = await axios.get("YOUR_YAHOO_FINANCE_NEWS_API_URL");
                setNews(response.data.articles); // Adjust based on API response
                setLoading(false);
            } catch (error) {
                console.error("Error fetching finance news:", error);
                setLoading(false);
            }
        };

        fetchNews();
    }, []);

    return (
        <div style={{ padding: "20px", maxWidth: "800px", margin: "auto" }}>
            <Title level={2}>Latest Finance News</Title>

            {loading ? (
                <Spin size="large" />
            ) : (
                <List
                    grid={{ gutter: 16, column: 1 }}
                    dataSource={news}
                    renderItem={(item) => (
                        <List.Item>
                            <Card
                                title={item.title}
                                extra={<a href={item.url} target="_blank" rel="noopener noreferrer">Read More</a>}
                                style={{ width: "100%" }}
                            >
                                <p>{item.description}</p>
                            </Card>
                        </List.Item>
                    )}
                />
            )}
        </div>
    );
};

export default FinanceNews;
