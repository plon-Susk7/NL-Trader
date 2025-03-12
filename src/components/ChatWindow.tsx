import { useEffect, useRef, useState } from "react";
import { io } from "socket.io-client";
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { dark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import axios from "axios";
import Markdown from "react-markdown";
import CandlestickChart from "./CandlestickChart";

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
    explanation?: string;
  }>;
  total_return?: number;
}

const CodeBlock = (codeString: string) => {
  let cleanCode = codeString.trim().replace("```python", "");
  cleanCode = cleanCode.replace("```", "");
  return (
    <SyntaxHighlighter language="python" style={dark}>
      {cleanCode}
    </SyntaxHighlighter>
  )
}

export const ChatWindow = () => {
  const [socket, setSocket] = useState<any>(null);
  const [messages, setMessages] = useState<Array<[string, boolean]>>([]);
  const [chartData, setChartData] = useState<ChartData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [chatWidth, setChatWidth] = useState(400);
  const [isDragging, setIsDragging] = useState(false);
  const [lastCodeBlock, setLastCodeBlock] = useState<string | null>(null);
  const [availableAssets, setAvailableAssets] = useState<string[]>([]);
  const [selectedAsset, setSelectedAsset] = useState<string>('');

  const handleSubmit = async () => {
    const message = inputRef.current?.value.trim();
    if (message) {
      setMessages((prevMessages) => [...prevMessages, [message, true]]);
    }
    if (message && socket) {
      socket.emit("message", message);
      inputRef.current!.value = "";
    }
  }

  const handleBacktest = async (code: string, assetId?: string) => {
    setIsLoading(true);
    setError(null);
    let cleanCode = code.trim().replace("```python", "").replace("```", "");
    
    try {
      console.log("Starting backtest request...");
      const response = await axios.post("http://127.0.0.1:5000/backtest", {
        code: cleanCode,
        selected_asset: assetId || selectedAsset || undefined,
        date: "2025-01-03"
      }, {
        timeout: 30000,  // 30 second timeout
        headers: {
          'Content-Type': 'application/json'
        }
      });

      console.log("Received response:", response);

      if (!response.data) {
        throw new Error("No data received from server");
      }

      // Parse the data
      try {
        const responseData = response.data;
        console.log("Processing response data:", responseData);
        
        const parsedData = typeof responseData.data === 'string' 
          ? JSON.parse(responseData.data) 
          : responseData.data;

        console.log("Parsed chart data:", parsedData);

        // Set available assets and selected asset
        if (responseData.available_assets) {
          console.log("Setting available assets:", responseData.available_assets);
          setAvailableAssets(responseData.available_assets);
          if (responseData.available_assets.length > 0) {
            const newSelectedAsset = responseData.selected_asset || responseData.available_assets[0];
            console.log("Setting selected asset:", newSelectedAsset);
            setSelectedAsset(newSelectedAsset);
          }
        }

        // Convert data format for chart
        const chartDataTemp: ChartData = {
          Open_n: parsedData.Open_n || {},
          High_n: parsedData.High_n || {},
          Low_n: parsedData.Low_n || {},
          Close_n: parsedData.Close_n || {},
          trades: parsedData.trades || [],
          total_return: parsedData.total_return,
          SMA_10: parsedData.SMA_10,
          SMA_20: parsedData.SMA_20
        };

        // Log trade signals for debugging
        if (parsedData.trades) {
          console.log("Trade signals:", parsedData.trades);
        }
        console.log("Total return:", parsedData.total_return);

        console.log("Setting chart data:", chartDataTemp);
        setChartData(chartDataTemp);
        setLastCodeBlock(code);

      } catch (e) {
        console.error("Error processing response data:", e);
        throw new Error("Failed to process chart data: " + (e instanceof Error ? e.message : String(e)));
      }

    } catch (error) {
      console.error("Backtest request error:", error);
      let errorMessage = "An error occurred running the backtest";
      
      if (axios.isAxiosError(error)) {
        if (error.code === 'ECONNABORTED') {
          errorMessage = "Request timed out. Please try again.";
        } else if (error.response) {
          // Server responded with error
          errorMessage = error.response.data?.error || error.response.statusText;
        } else if (error.request) {
          // Request made but no response
          errorMessage = "No response from server. Please check if the server is running.";
        } else {
          // Request setup error
          errorMessage = error.message;
        }
      } else if (error instanceof Error) {
        errorMessage = error.message;
      }
      
      setError(errorMessage);
      setChartData(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmitCode = async () => {
    if (lastCodeBlock) {
      try {
        const response = await axios.post("http://127.0.0.1:5000/submit", {
          code: lastCodeBlock.trim().replace("```python", "").replace("```", "")
        });
        console.log("Strategy submission response:", response.data);
      } catch (error) {
        console.error("Error submitting strategy:", error);
      }
    }
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    e.preventDefault();
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isDragging) {
        const newWidth = Math.max(200, Math.min(800, e.clientX));
        setChatWidth(newWidth);
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging]);

  useEffect(() => {
    const socketInstance = io("http://127.0.0.1:5000", {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
      timeout: 60000
    });

    setSocket(socketInstance);

    socketInstance.on("connect", () => {
      console.log("Connected to the server");
    });

    socketInstance.on("connect_error", (error) => {
      console.error("Socket connection error:", error);
    });

    socketInstance.on("disconnect", (reason) => {
      console.log("Disconnected from server:", reason);
    });

    socketInstance.on("message", (data) => {
      setMessages((prevMessages) => [...prevMessages, [data, false]]);
    });

    return () => {
      socketInstance.disconnect();
    };
  }, []);

  const handleAssetChange = async (assetId: string) => {
    setSelectedAsset(assetId);
    setIsLoading(true);
    setError(null);
    
    if (lastCodeBlock) {
      try {
        console.log("Changing asset to:", assetId);
        const response = await axios.post("http://127.0.0.1:5000/backtest", {
          code: lastCodeBlock.trim().replace("```python", "").replace("```", ""),
          selected_asset: assetId,
          date: "2025-01-03"
        }, {
          timeout: 30000,
          headers: {
            'Content-Type': 'application/json'
          }
        });

        if (!response.data) {
          throw new Error("No data received from server");
        }

        // Update available assets if they're in the response
        if (response.data.available_assets) {
          setAvailableAssets(response.data.available_assets);
        }

        // Set the chart data directly from response
        setChartData(response.data.data);
        
        // Add message to chat about asset change
        const returnText = response.data.data.total_return * 100;
        const message = `Switched to asset ${assetId}. Total return: ${returnText.toFixed(2)}%`;
        setMessages(prev => [...prev, [message, false]]);

      } catch (error) {
        console.error("Error changing asset:", error);
        let errorMessage = "An error occurred while changing asset";
        
        if (axios.isAxiosError(error)) {
          if (error.code === 'ECONNABORTED') {
            errorMessage = "Request timed out. Please try again.";
          } else if (error.response) {
            errorMessage = error.response.data?.error || error.response.statusText;
          } else if (error.request) {
            errorMessage = "No response from server. Please check if the server is running.";
          } else {
            errorMessage = error.message;
          }
        } else if (error instanceof Error) {
          errorMessage = error.message;
        }
        
        setError(errorMessage);
        // Add error message to chat
        setMessages(prev => [...prev, [`Error: ${errorMessage}`, false]]);
      } finally {
        setIsLoading(false);
      }
    }
  };

  return (
    <div className="flex h-screen w-screen bg-gray-900 relative">
      <div
        className="h-full border-r border-gray-700 flex flex-col bg-gray-800 relative"
        style={{ width: `${chatWidth}px` }}
      >
        <div className="flex-grow overflow-y-auto">
          {messages.map((message, index) => (
            <div key={index} className={`p-2 m-2 ${message[1] ? 'ml-auto' : 'mr-auto'} max-w-[90%]`}>
              <div className={`rounded-lg p-3 ${message[1]
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-100'
                }`}>
                {message[0].includes("```python") ? (
                  <>
                    {CodeBlock(message[0])}
                    <div className="flex gap-2 mt-2">
                      <button
                        onClick={() => handleBacktest(message[0])}
                        className="flex-1 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition-colors"
                        disabled={isLoading}
                      >
                        {isLoading ? 'Running...' : 'Backtest Strategy'}
                      </button>
                      <button
                        onClick={handleSubmitCode}
                        className="flex-1 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                        disabled={isLoading}
                      >
                        Submit Strategy
                      </button>
                    </div>
                  </>
                ) : (
                  <div><Markdown>{message[0]}</Markdown></div>
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="p-4 border-t border-gray-700">
          <div className="flex gap-2">
            <input
              type="text"
              ref={inputRef}
              placeholder="Type your message..."
              className="flex-grow p-2 rounded bg-gray-700 text-white border border-gray-600 focus:border-blue-500 focus:outline-none"
              onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
            />
            <button
              onClick={handleSubmit}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
            >
              Send
            </button>
          </div>
        </div>
      </div>

      <div
        className={`w-1 bg-gray-600 hover:bg-blue-500 cursor-col-resize absolute top-0 bottom-0 z-10 ${isDragging ? 'bg-blue-500' : ''}`}
        style={{ left: `${chatWidth - 2}px` }}
        onMouseDown={handleMouseDown}
      />

      <div className="flex-grow h-full bg-gray-900">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-gray-400">
              <svg className="animate-spin h-8 w-8 mr-3" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span>Processing trading strategy...</span>
            </div>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-red-400 max-w-md text-center p-4">
              <div className="text-xl mb-2">Error</div>
              <div>{error}</div>
            </div>
          </div>
        ) : chartData ? (
          <div className="w-full h-[600px] p-4">
            <div className="mb-4 flex items-center gap-4">
              <label className="text-white">Select Asset:</label>
              <select
                value={selectedAsset}
                onChange={(e) => handleAssetChange(e.target.value)}
                className="bg-gray-700 text-white rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {availableAssets.map((asset) => (
                  <option key={asset} value={asset}>
                    {asset}
                  </option>
                ))}
              </select>
            </div>
            <CandlestickChart data={{
              ...chartData,
              trades: chartData.trades?.map(trade => ({
                ...trade,
                return_pct: trade.return * 100,
                trade_type: trade.action === 1 ? 'BUY' : 'SELL'
              }))
            }} />
          </div>
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-gray-400 max-w-md text-center p-4">
              <div className="text-xl mb-2">No Chart Data</div>
              <div>Submit a trading strategy to visualize results</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};