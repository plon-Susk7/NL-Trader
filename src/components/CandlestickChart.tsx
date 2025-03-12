import React from 'react';
import {
  ChartCanvas,
  Chart,
  XAxis,
  YAxis,
  CandlestickSeries,
  LineSeries,
  MouseCoordinateX,
  MouseCoordinateY,
  CrossHairCursor,
  EdgeIndicator,
  OHLCTooltip,
  withDeviceRatio,
  withSize,
  IZoomAnchorOptions,
} from "react-financial-charts";
import { scaleLinear } from "d3-scale";

interface ChartData {
  Open_n: { [key: string]: number };
  High_n: { [key: string]: number };
  Low_n: { [key: string]: number };
  Close_n: { [key: string]: number };
  SMA_10?: { [key: string]: number };
  SMA_20?: { [key: string]: number };
  trades?: Array<{
    period: number;
    action: number;
    price: number;
    return: number;
    return_pct: number;
    trade_type: string;
    explanation?: string;
  }>;
  total_return?: number;
  metrics?: {
    total_trades: number;
    winning_trades: number;
    losing_trades: number;
    total_profit: number;
    total_loss: number;
    max_profit: number;
    max_loss: number;
    avg_profit: number;
    avg_loss: number;
    win_rate: number;
    profit_factor: number;
  };
}

interface Trade {
  action: number;
  price: number;
  return: number;
  return_pct: number;
  trade_type: string;
  period?: number;
  explanation?: string;
}

interface ChartDataPoint {
  time: number;
  originalTime: number;
  open: number;
  high: number;
  low: number;
  close: number;
  sma10?: number;
  sma20?: number;
  trade?: Trade;
}

interface TradingChartProps {
  readonly data: ChartData;
  readonly height: number;
  readonly width: number;
  readonly ratio: number;
}

interface ChartState {
  showSMA10: boolean;
  showSMA20: boolean;
  showTrades: boolean;
}

const consoleWarn = console.warn;
console.warn = (...args) => {
  if (args[0]?.includes('UNSAFE_')) return;
  consoleWarn(...args);
};

class CandlestickChart extends React.Component<TradingChartProps, ChartState> {
  state: ChartState = {
    showSMA10: true,
    showSMA20: true,
    showTrades: true  // Always show trades now
  };

  private processChartData(data: ChartData) {
    try {
      if (!data || !data.Open_n || Object.keys(data.Open_n).length === 0) {
        console.log("No valid data available for chart processing");
        return [];
      }
      
      // Get all indices and ensure they are valid numbers
      const indices = Object.keys(data.Open_n)
        .map(Number)
        .filter(i => !isNaN(i))
        .sort((a, b) => a - b);
      
      if (indices.length === 0) {
        console.log("No valid indices found in data");
        return [];
      }

      // Create a mapping of trades by period
      const tradesByPeriod = new Map();
      if (data.trades && Array.isArray(data.trades)) {
        console.log("Processing trades:", data.trades);
        data.trades.forEach(trade => {
          if (trade && typeof trade.period === 'number') {
            tradesByPeriod.set(trade.period, {
              ...trade,
              action: Number(trade.action),
              price: Number(trade.price),
              return: Number(trade.return),
              return_pct: Number(trade.return_pct)
            });
          }
        });
      }

      const processedData = indices.map((originalIndex, normalizedIndex) => {
        const trade = tradesByPeriod.get(originalIndex);
        
        return {
          time: normalizedIndex,
          originalTime: originalIndex,
          open: Number(data.Open_n[originalIndex]) || 0,
          high: Number(data.High_n[originalIndex]) || 0,
          low: Number(data.Low_n[originalIndex]) || 0,
          close: Number(data.Close_n[originalIndex]) || 0,
          sma10: data.SMA_10 ? Number(data.SMA_10[originalIndex]) || undefined : undefined,
          sma20: data.SMA_20 ? Number(data.SMA_20[originalIndex]) || undefined : undefined,
          trade: trade || undefined
        };
      });

      console.log("Processed chart data with trades:", processedData.filter(d => d.trade));
      return processedData;
    } catch (error) {
      console.error("Error processing chart data:", error);
      return [];
    }
  }

  render() {
    const { data, width, height, ratio } = this.props;
    const { showSMA10, showSMA20 } = this.state;
    
    try {
      console.log("Rendering with data:", data);  // Debug log
      const chartData = this.processChartData(data);

      if (!chartData || chartData.length === 0) {
        return (
          <div className="w-full h-full flex items-center justify-center text-gray-400">
            <div>No data available for chart</div>
          </div>
        );
      }

      const xAccessor = (d: ChartDataPoint) => d.time;
      const xExtents = [0, chartData.length - 1];

      return (
        <div className="flex flex-col">
          <div className="flex flex-col gap-4 mb-4 px-4">
            {/* Strategy Performance Metrics */}
            <div className="bg-gray-800 p-4 rounded-lg">
              <div className="flex items-center">
                <div className="text-white">
                  <div className="text-sm text-gray-400">Total Return</div>
                  <div className={`${(data.total_return || 0) >= 0 ? 'text-green-500' : 'text-red-500'} font-bold text-2xl`}>
                    {((data.total_return || 0) * 100).toFixed(2)}%
                  </div>
                </div>
              </div>
            </div>

            {/* Chart Controls */}
            <div className="flex gap-2">
              <button
                onClick={() => this.setState(prev => ({ showSMA10: !prev.showSMA10 }))}
                className={`px-3 py-1 rounded ${showSMA10 ? 'bg-blue-600' : 'bg-gray-600'} text-white`}
              >
                SMA 10
              </button>
              <button
                onClick={() => this.setState(prev => ({ showSMA20: !prev.showSMA20 }))}
                className={`px-3 py-1 rounded ${showSMA20 ? 'bg-yellow-600' : 'bg-gray-600'} text-white`}
              >
                SMA 20
              </button>
            </div>
          </div>

          <ChartCanvas
            height={height}
            ratio={ratio}
            width={width}
            margin={{ left: 50, right: 50, top: 10, bottom: 50 }}
            data={chartData}
            xAccessor={xAccessor}
            xScale={scaleLinear<number>()}
            xExtents={xExtents}
            seriesName="Price"
            displayXAccessor={xAccessor}
            mouseMoveEvent
            clamp={false}
            disableZoom={false}
          >
            <Chart id={1} yExtents={(d: ChartDataPoint) => [d.high * 1.1, d.low * 0.9]}>
              <XAxis tickFormat={(index) => `${index}`} />
              <YAxis />
              
              {/* OHLC Candlesticks */}
              <CandlestickSeries 
                fill={(d: ChartDataPoint) => d.close > d.open ? "#22c55e" : "#ef4444"}
                wickStroke={(d: ChartDataPoint) => d.close > d.open ? "#22c55e" : "#ef4444"}
                stroke={(d: ChartDataPoint) => d.close > d.open ? "#22c55e" : "#ef4444"}
              />
              
              {/* Moving Averages */}
              {showSMA10 && (
                <LineSeries
                  yAccessor={(d: ChartDataPoint) => d.sma10}
                  strokeStyle="#3b82f6"
                  strokeWidth={1}
                />
              )}
              {showSMA20 && (
                <LineSeries
                  yAccessor={(d: ChartDataPoint) => d.sma20}
                  strokeStyle="#eab308"
                  strokeWidth={1}
                />
              )}

              {/* Trade Triangles */}
              {chartData.map((d: ChartDataPoint, i) => {
                const trade = d.trade;
                if (trade) {
                  console.log(`Rendering trade at index ${i}:`, trade);  // Debug log
                  const isEntry = trade.action === 1;
                  const yPosition = d.low * 0.85;  // Position below candlesticks
                  const markerColor = isEntry ? "#22c55e" : "#ef4444";
                  const tradeInfo = `${trade.trade_type} @ ${trade.price.toFixed(2)}\nReturn: ${trade.return_pct.toFixed(2)}%`;
                  const triangleSize = 8;
                  
                  return (
                    <g key={`trade-${i}`} 
                       style={{ cursor: 'pointer' }}
                       onClick={() => {
                         const detailedInfo = `
Trade Details
------------
Type: ${trade.trade_type}
Price: ${trade.price.toFixed(2)}
Return: ${trade.return_pct.toFixed(2)}%
Period: ${d.originalTime}
                         `;
                         alert(detailedInfo);
                       }}>
                      {/* Upward pointing triangle for all trades */}
                      <path
                        d={`M ${xAccessor(d)} ${yPosition} L ${xAccessor(d) - triangleSize} ${yPosition + triangleSize} L ${xAccessor(d) + triangleSize} ${yPosition + triangleSize} Z`}
                        fill={markerColor}
                        stroke="white"
                        strokeWidth={1}
                      />
                      
                      {/* Hover Info */}
                      <title>{tradeInfo}</title>
                    </g>
                  );
                }
                return null;
              })}

              <MouseCoordinateX displayFormat={(index) => `Period ${index}`} />
              <MouseCoordinateY displayFormat={(price) => price.toFixed(2)} />
              
              <EdgeIndicator
                itemType="last"
                orient="right"
                edgeAt="right"
                yAccessor={(d: ChartDataPoint) => d.close}
                fill={(d: ChartDataPoint) => d.close > d.open ? "#22c55e" : "#ef4444"}
              />
              
              <OHLCTooltip origin={[-40, 0]} />
            </Chart>
            <CrossHairCursor />
          </ChartCanvas>
        </div>
      );
    } catch (error) {
      console.error("Error rendering chart:", error);
      return (
        <div className="w-full h-full flex items-center justify-center text-gray-400">
          <div>Error rendering chart</div>
        </div>
      );
    }
  }
}

// Add size and device ratio HOCs
const ChartWithSize = withSize({ style: { minHeight: 600 } })(withDeviceRatio()(CandlestickChart));
export default ChartWithSize;