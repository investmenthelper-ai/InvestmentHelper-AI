import React, { useEffect, useRef, useState } from 'react';
import {
    createChart,
    IChartApi,
    UTCTimestamp,
    WhitespaceData,
    MouseEventParams
} from 'lightweight-charts';
import { BrushableAreaSeries } from '../../plugins/brushable-area-series/brushable-area-series';
import { BrushableAreaData } from '../../plugins/brushable-area-series/data';
import { BrushableAreaStyle } from '../../plugins/brushable-area-series/options';
import { DeltaTooltipPrimitive } from '../../plugins/delta-tooltip/delta-tooltip';
import { generateLineData } from './data';
import { TrendLine } from '../../plugins/trend-line/trend-line';
import Sidebar from '../Sidebar/Sidebar';

const ChartArea: React.FC = () => {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const [isSidebarOpen, setSidebarOpen] = useState(false);
    const [isTrendLineActive, setIsTrendLineActive] = useState(false);
    const [trendlineStart, setTrendlineStart] = useState<{ time: UTCTimestamp; price: number } | null>(null);
    const brushAreaSeriesRef = useRef<BrushableAreaSeries | null>(null);
    const overlayCanvasRef = useRef<HTMLCanvasElement>(null);
    const chartRef = useRef<IChartApi | null>(null);
    useEffect(() => {
        if (!chartContainerRef.current) return;

        // Create the chart
        const chart: IChartApi = createChart(chartContainerRef.current, {
            width: chartContainerRef.current.clientWidth,
            height: chartContainerRef.current.clientHeight,
            layout: {
                backgroundColor: '#ffffff',
            },
            grid: {
                vertLines: {
                    visible: false,
                },
                horzLines: {
                    visible: false,
                },
            },
            timeScale: {
                borderVisible: false,
            },
            rightPriceScale: {
                borderVisible: false,
            },
            handleScale: false,
            handleScroll: false,
        });
        chartRef.current = chart;
        // Define styles
        const greenStyle: Partial<BrushableAreaStyle> = {
            lineColor: 'rgb(4,153,129)',
            topColor: 'rgba(4,153,129, 0.4)',
            bottomColor: 'rgba(4,153,129, 0)',
            lineWidth: 3,
        };

        const redStyle: Partial<BrushableAreaStyle> = {
            lineColor: 'rgb(239,83,80)',
            topColor: 'rgba(239,83,80, 0.4)',
            bottomColor: 'rgba(239,83,80, 0)',
            lineWidth: 3,
        };

        const fadeStyle: Partial<BrushableAreaStyle> = {
            lineColor: 'rgba(40,98,255, 0.2)',
            topColor: 'rgba(40,98,255, 0.05)',
            bottomColor: 'rgba(40,98,255, 0)',
        };

        const baseStyle: Partial<BrushableAreaStyle> = {
            lineColor: 'rgb(40,98,255)',
            topColor: 'rgba(40,98,255, 0.4)',
            bottomColor: 'rgba(40,98,255, 0)',
        };

        // Add the brushable area series
        const customSeriesView = new BrushableAreaSeries();
        const brushAreaSeries = chart.addCustomSeries(customSeriesView, {
            ...baseStyle,
            priceLineVisible: false,
        });
        brushAreaSeriesRef.current = brushAreaSeries;
        // Generate sample data
        const data: (BrushableAreaData | WhitespaceData)[] = generateLineData();
        brushAreaSeries.setData(data);

        // Add tooltip primitive
        const tooltipPrimitive = new DeltaTooltipPrimitive({
            lineColor: 'rgba(0, 0, 0, 0.2)',
        });
        brushAreaSeries.attachPrimitive(tooltipPrimitive);

        // Fit the chart content to the visible area
        chart.timeScale().fitContent();


        // Handle active range changes
        tooltipPrimitive.activeRange().subscribe(activeRange => {
            if (activeRange === null) {
                brushAreaSeries.applyOptions({
                    brushRanges: [],
                    ...baseStyle,
                });
                return;
            }
            brushAreaSeries.applyOptions({
                brushRanges: [
                    {
                        range: {
                            from: activeRange.from,
                            to: activeRange.to,
                        },
                        style: activeRange.positive ? greenStyle : redStyle,
                    },
                ],
                ...fadeStyle,
            });
        });

        // Handle resizing
        const handleResize = () => {
            chart.resize(
                chartContainerRef.current!.clientWidth,
                chartContainerRef.current!.clientHeight
            );
            chart.timeScale().fitContent();
        };

        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            chart.remove();
        };
    }, []);

    const handleMouseClick = (params: MouseEventParams) => {
        console.log('Mouse click detected:', params);

        // Ensure required fields are present
        if (!params.time || params.point === undefined) return;

        const { time } = params;
        const { x, y } = params.point;

        // Extract series data
        if (params.seriesData && params.seriesData.size > 0) {
            const seriesEntry = [...params.seriesData.entries()][0];
            const { value } = seriesEntry[1];
            console.log('Clicked Value:', value, 'Clicked Time:', time);
        }

        if (isTrendLineActive) {
            if (!trendlineStart) {
                setTrendlineStart({ time: time as UTCTimestamp, price: params.seriesData.values().next().value?.value || 0 });
            } else {
                const trendlineOptions = {
                    lineColor: 'red',
                    width: 2,
                    showLabels: true,
                    labelBackgroundColor: 'rgba(255, 255, 255, 0.8)',
                    labelTextColor: 'black',
                };

                const trendline = new TrendLine(
                    chartRef.current!,
                    brushAreaSeriesRef.current!,
                    trendlineStart,
                    { time: time as UTCTimestamp, price: params.seriesData.values().next().value?.value || 0 },
                    trendlineOptions
                );

                brushAreaSeriesRef.current!.attachPrimitive(trendline);
                setTrendlineStart(null); // Reset state
            }
        }
    };

    useEffect(() => {
        if (chartRef.current) {
            chartRef.current.subscribeClick(handleMouseClick);
        }

        return () => {
            if (chartRef.current) {
                chartRef.current.unsubscribeClick(handleMouseClick);
            }
        };
    }, [handleMouseClick, isTrendLineActive, trendlineStart]);



    const handleTrendLineToggle = () => {
        console.log('Toggling isTrendLineActive...');
        setIsTrendLineActive((prev) => {
            console.log('Previous value:', prev);
            return !prev;
        });
    };



    return (
        <div >

            return (
            <div style={{ display: 'flex', height: '100vh' }}>
                {/* Sidebar */}
                <Sidebar
                    isOpen={isSidebarOpen}
                    setSidebarOpen={setSidebarOpen}
                    isTrendLineActive={isTrendLineActive}
                    onTrendLineToggle={handleTrendLineToggle}// Enable drawing mode
                />

                {/* Chart Container */}
                <div
                    ref={chartContainerRef}
                    style={{
                        flex: 1,
                        position: 'relative',
                    }}
                />
            </div>
            );

            {/* Chart container */}
            <div
                ref={chartContainerRef}
                style={{
                    position: 'absolute',
                    top: '60px', // Offset by navbar height
                    bottom: 0,
                    left: 0,
                    right: 0,
                    overflow: 'hidden',
                }}
            />

            {/* Overlay canvas */}
            <canvas
                ref={overlayCanvasRef}
                style={{
                    position: 'absolute',
                    top: '60px', // Offset by navbar height
                    left: 0,
                    pointerEvents: 'none',
                    width: '100%',
                    height: 'calc(100vh - 60px)', // Adjust canvas height
                }}
            />
        </div>
    );
};

export default React.memo(ChartArea);

