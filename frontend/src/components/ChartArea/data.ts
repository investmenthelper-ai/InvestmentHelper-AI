import { BrushableAreaData } from '../../plugins/brushable-area-series/data';
import { UTCTimestamp } from 'lightweight-charts';

export const generateLineData = (): BrushableAreaData[] => {
    const data: BrushableAreaData[] = [];
    const startTime = Math.floor(Date.now() / 1000) - 60 * 60 * 24 * 30; // 30 days ago

    let currentValue = 100; // Starting value

    for (let i = 0; i < 500; i++) {
        // Simulate daily fluctuation: random change between -5 and +5
        const fluctuation = Math.random() * 10 - 5;
        currentValue = Math.max(50, Math.min(150, currentValue + fluctuation)); // Keep within 50-150 range

        data.push({
            time: (startTime + i * 60 * 60 * 24) as UTCTimestamp, // Increment by 1 day
            value: parseFloat(currentValue.toFixed(2)), // Keep two decimal places
        });
    }

    return data;
};
