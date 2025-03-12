# app.py
from flask import request, Flask, jsonify, render_template
from flask_socketio import SocketIO, send
from flask_cors import CORS
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv
import pandas as pd
import time
from numin import NuminAPI
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent    
from langgraph.checkpoint.memory import MemorySaver
import traceback
import json

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

socketio = SocketIO(
    app, 
    cors_allowed_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000"],
    async_mode=None,  # Changed from 'threading' to None
    logger=True,
    engineio_logger=True,
    ping_timeout=60000,
    ping_interval=25000,
    always_connect=True,  # Added to ensure connections are accepted
    transports=['websocket', 'polling']  # Explicitly specify transports
)

# Get API keys from environment variables
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
NUMIN_API_KEY = os.getenv('NUMIN_API_KEY', "4b0ad9d1-a18f-2be3-da30-29da07c9b20c")

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable is not set")

dataset_context = '''
Price and Price Relationships
High_n, Low_n, Open_n, Close_n: High, low, opening, and closing prices for period n.
High_n-Low_n: Range between high and low prices in period n.
Open_n-Close_n: Difference between opening and closing prices in period n.

Simple Moving Averages (SMAs)
SMA_10, SMA_20: 10-period and 20-period Simple Moving Averages.
SMA_20-SMA_10: Difference between 20-period and 10-period SMAs.

Change Length Indicators
Variables representing the periods over which changes occur:
Open_n_changelen, High_n_changelen, Low_n_changelen, Close_n_changelen: Change length for opening, high, low, and closing prices.
SMA_20-SMA_10_changelen: Change length of SMA differences.
Close_n_slope_3_changelen, Close_n_slope_5_changelen, Close_n_slope_10_changelen: Change length of closing price slopes over 3, 5, and 10 periods.

Price Slopes
Close_n_slope_3, Close_n_slope_5, Close_n_slope_10: Slopes (rates of change) of the closing price over 3, 5, and 10 periods.

Valuation Variables
Variables representing absolute values of indicators or prices:
Open_n_val, High_n_val, Low_n_val, Close_n_val: Absolute values for opening, high, low, and closing prices.
SMA_10_val, SMA_20_val: Absolute values of SMAs.
CMO_14_val, RSI_14_val: Absolute values of momentum and strength indicators.

Technical Indicators
VOL_SMA_20: 20-period Simple Moving Average of volume.
RSI_14: Relative Strength Index (momentum) over 14 periods.
CMO_14: Chande Momentum Oscillator over 14 periods.
BBL_5_2.0, BBM_5_2.0, BBU_5_2.0: Bollinger Bands (Lower, Middle, and Upper) over 5 periods with 2.0 standard deviation.
BBB_5_2.0, BBP_5_2.0: Bollinger Band Width and Percentage.
MACD_12_26_9: Moving Average Convergence Divergence line.
MACDh_12_26_9, MACDs_12_26_9: MACD histogram and signal line.

VWAP and Momentum
VWAP_D: Volume Weighted Average Price for the day.
MOM_30: Momentum indicator over 30 periods.

Targets
target_5, target_10: Targets for 5-period and 10-period predictions.
target_5_val, target_10_val: Numerical values of these targets.

Miscellaneous
row_num: Row index or identifier.
era: Period grouping (e.g., week, month, year).
id: Unique identifier for data rows.

Following code structure should be followed:
def exponential_moving_average_prediction(df, span=15):
    """
    Calculate predictions for target_5 and target_10 based on EMA and other indicators.
    Uses pre-calculated values from the dataframe.
    
    Args:
        df: DataFrame containing the price data and indicator values
        span: EMA span parameter
    
    Returns:
        tuple: (target_5_prediction, target_10_prediction) between -1 and 1
    """
    # Get latest row of data
    current = df.iloc[-1]
    
    # Initialize prediction scores
    score_5 = 0
    score_10 = 0
    
    ### Code here

    ### End of code

    return score_5, score_10
'''

SYSTEM_PROMPT = f"""
You are best at writing python code and have good knowledge about finance. 
You'll assist people in converting their trading strategies into code.
You are provided with dataset containing information about financial and technical indicators.

Available dataset context:
{dataset_context}

Strictly return python code only when Human gives a strategy or asks to change the previous strategy and don't provide code explanations.
If the instruction is ambiguous ask for more detailed strategy else reply generally.
When generating code just generate code and nothing else.
"""

model = ChatGoogleGenerativeAI(
    model = "gemini-2.0-flash-exp",
    google_api_key=GOOGLE_API_KEY,
)

# Create agent
memory = MemorySaver()
tools = []
agent_executor = create_react_agent(model, tools, checkpointer=memory, state_modifier=SYSTEM_PROMPT)
config = {"configurable":{"thread_id":"abc124"}}

def create_function_from_string(function_string):
    namespace = {}
    
    try:
        # Execute the function string in the namespace
        exec(function_string, namespace)
        
        # Find the function in the namespace
        function_name = function_string.split('def')[1].split('(')[0].strip()
        return namespace[function_name]
    
    except Exception as e:
        raise ValueError(f"Error converting function string: {e}")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/test')
def test():
    return jsonify({"status": "Server is running"}), 200

@app.route('/backtest', methods=['POST'])
def run_backtest():
    try:
        if not request.json or 'code' not in request.json:
            return jsonify({'error': 'No code provided in request'}), 400

        date = "2025-01-03"  # Set date explicitly in YYYY-MM-DD format
        print(f"Received backtest request for date: {date}")
        
        try:
            exponential_moving_average_prediction = create_function_from_string(request.json['code'])
            print("Successfully created strategy function")
            
            def process_round_data(df, current_round):
                """Process round data using exponential moving average strategy."""
                try:
                    print("\nDEBUG - Process Round Data Input:")
                    print(f"Type of input data: {type(df)}")
                    
                    if not isinstance(df, pd.DataFrame):
                        print("Converting input to DataFrame...")
                        df = pd.DataFrame(df)
                    
                    print(f"DataFrame shape: {df.shape}")
                    print(f"DataFrame columns: {df.columns.tolist()}")
                    
                    # Initialize empty list for predictions
                    predictions = []
                    
                    # Process each ticker
                    for ticker in df['id'].unique():
                        ticker_data = df[df['id'] == ticker].copy()
                        # Get predictions for this ticker
                        target_5, target_10 = exponential_moving_average_prediction(ticker_data)
                        predictions.append({
                            "id": ticker,
                            "predictions": float(target_5),  # Ensure prediction is float
                            "round_no": int(current_round)  # Use current_round as specified
                        })
                    
                    # Convert to DataFrame
                    predictions_df = pd.DataFrame(predictions)
                    
                    # Force column types
                    predictions_df['id'] = predictions_df['id'].astype(str)
                    predictions_df['predictions'] = predictions_df['predictions'].astype(float)
                    predictions_df['round_no'] = predictions_df['round_no'].astype(int)
                    
                    return predictions_df
                except Exception as e:
                    print(f"Error in process_round_data: {str(e)}")
                    print("Traceback:", traceback.format_exc())
                    raise

            # Initialize API and get data
            api_client = NuminAPI(api_key=NUMIN_API_KEY)
            
            print(f"Fetching validation data for date: {date}")
            validation_df = api_client.fetch_validation_data(date)  # Returns DataFrame
            
            if validation_df is None or validation_df.empty:
                return jsonify({'error': 'No validation data available'}), 400
            
            print("Running backtest...")
            backtest_results = api_client.run_backtest(
                user_strategy=process_round_data,
                date=date,
                result_type="results"
            )
            print("Backtest completed. Results:", json.dumps(backtest_results, indent=2))
            print(backtest_results)
            
            selected_asset = request.json.get('selected_asset')
            available_assets = list(backtest_results.keys())
            
            if not selected_asset or selected_asset not in available_assets:
                selected_asset = available_assets[0] if available_assets else None

            if not selected_asset:
                return jsonify({'error': 'No assets available'}), 500

            # Get asset specific data
            asset_df = validation_df[validation_df['id'] == selected_asset].copy()
            asset_df['row_num'] = asset_df['row_num'].astype(int)
            asset_df = asset_df.sort_values('row_num')

            # Process trades from backtest results
            asset_trades = backtest_results[selected_asset]
            print(f"Processing trades for asset: {selected_asset}")
            print(f"Asset trades data: {json.dumps(asset_trades, indent=2)}")
            
            # Get the date-specific data
            date_key = '03-Jan-2025'
            if date_key not in asset_trades:
                return jsonify({'error': f'No data available for date {date_key}'}), 400
                
            trades_data = asset_trades[date_key]
            print(f"Trades data for {date_key}: {json.dumps(trades_data, indent=2)}")

            # Process trades and rewards
            trades = []
            if trades_data.get('acts') and trades_data.get('rew'):
                print("Processing trades data:")
                print(f"Acts: {trades_data['acts']}")
                print(f"Rewards: {trades_data['rew']}")

                # Create mappings for acts and rewards using trade_id as key
                acts_map = {}
                for act in trades_data['acts']:
                    # act structure: [action, param1, param2, trade_id]
                    if len(act) >= 4:
                        action, _, _, trade_id = act
                        acts_map[trade_id] = action

                rew_map = {}
                for rew in trades_data['rew']:
                    # rew structure: [trade_id, reward_value, round_no]
                    if len(rew) >= 3:
                        trade_id, reward, round_no = rew
                        rew_map[trade_id] = (reward, round_no)

                print(f"Acts mapping: {acts_map}")
                print(f"Rewards mapping: {rew_map}")

                # Process each trade that has both an action and a reward
                for trade_id in set(acts_map.keys()) & set(rew_map.keys()):
                    action = acts_map[trade_id]  # Get action (1=buy, -1=sell)
                    reward, round_no = rew_map[trade_id]  # Get reward and round number
                    
                    # Get price at the trade point
                    trade_data = asset_df[asset_df['row_num'] == round_no]
                    if not trade_data.empty:
                        price = float(trade_data['Close_n'].iloc[0])
                        
                        trade_info = {
                            'period': int(round_no),
                            'action': int(action),
                            'price': float(price),
                            'return': float(reward),
                            'return_pct': float(reward) * 100,
                            'trade_type': 'BUY' if action == 1 else 'SELL',
                            'trade_id': str(trade_id)
                        }
                        
                        print(f"Adding trade: {trade_info}")
                        trades.append(trade_info)

            print(f"Final processed trades: {json.dumps(trades, indent=2)}")
            print(f"Total return from trades_data: {trades_data.get('tot')}")

            # Initialize price data with the total return from backtest results
            price_data = {
                'Open_n': asset_df.set_index('row_num')['Open_n'].to_dict(),
                'High_n': asset_df.set_index('row_num')['High_n'].to_dict(),
                'Low_n': asset_df.set_index('row_num')['Low_n'].to_dict(),
                'Close_n': asset_df.set_index('row_num')['Close_n'].to_dict(),
                'SMA_10': asset_df.set_index('row_num')['SMA_10'].to_dict() if 'SMA_10' in asset_df.columns else {},
                'SMA_20': asset_df.set_index('row_num')['SMA_20'].to_dict() if 'SMA_20' in asset_df.columns else {},
                'trades': trades,
                'total_return': float(trades_data.get('tot', 0.0))
            }

            response_data = {
                'data': price_data,
                'available_assets': available_assets,
                'selected_asset': selected_asset,
                'trades_summary': {
                    'total_trades': len(trades),
                    'buy_trades': sum(1 for t in trades if t['action'] == 1),
                    'sell_trades': sum(1 for t in trades if t['action'] == -1),
                    'total_return': float(trades_data.get('tot', 0.0))
                }
            }

            print(f"Final response data: {json.dumps(response_data, indent=2)}")
            return jsonify(response_data)
                
        except Exception as api_error:
            print(f"API Error: {str(api_error)}")
            print("Full traceback:", traceback.format_exc())
            return jsonify({'error': f'API Error: {str(api_error)}'}), 500
            
    except Exception as e:
        print(f"Exception in /backtest: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/submit', methods=['POST'])
def submit_code():
    try:
        # Create function from submitted code
        exponential_moving_average_prediction = create_function_from_string(request.json['code'])
        
        def process_round_data(df, current_round):
            """Process round data using exponential moving average strategy."""
            print("\nDEBUG - Process Round Data Input:")
            print(f"Type of input data: {type(df)}")
            
            # Convert input to DataFrame if it's a list
            if isinstance(df, list):
                print("Converting list to DataFrame...")
                df = pd.DataFrame(df)
            
            print(f"DataFrame shape: {df.shape}")
            print(f"DataFrame columns: {df.columns.tolist()}")
            
            # Initialize empty list for predictions
            predictions = []
            
            # Process each ticker
            for ticker in df['id'].unique():
                ticker_data = df[df['id'] == ticker].copy()
                # Get predictions for this ticker
                target_5, target_10 = exponential_moving_average_prediction(ticker_data)
                predictions.append({
                    "id": ticker,
                    "predictions": float(target_5),  # Ensure prediction is float
                    "round_no": int(current_round)  # Ensure round_no is int
                })
            
            # Convert to DataFrame
            predictions_df = pd.DataFrame(predictions)
            
            print("\nDEBUG - Predictions Output:")
            print(f"Predictions DataFrame shape: {predictions_df.shape}")
            print(f"Predictions columns: {predictions_df.columns.tolist()}")
            print(f"First prediction: {predictions_df.iloc[0].to_dict() if len(predictions_df) > 0 else 'Empty'}")
            
            # Verify required columns exist
            required_cols = {"id", "predictions", "round_no"}
            if not required_cols.issubset(predictions_df.columns):
                missing = required_cols - set(predictions_df.columns)
                print(f"ERROR: Missing required columns: {missing}")
                raise ValueError(f"Predictions DataFrame missing required columns: {missing}")
            
            return predictions_df

        # Initialize API and get data
        API_KEY = "aaeb0b4f-9caa-b317-56ed-771b4fdb9fc1"
        api_client = NuminAPI(api_key=API_KEY)
        
        # Get current round
        current_round = api_client.get_current_round()
        if isinstance(current_round, dict) and "error" in current_round:
            return jsonify({"error": f"Failed to get round: {current_round['error']}"}), 500
            
        # Get round data
        round_data = api_client.get_data(data_type="round")
        if isinstance(round_data, dict) and "error" in round_data:
            return jsonify({"error": f"Failed to get round data: {round_data['error']}"}), 500

        # Process predictions
        predictions = process_round_data(pd.DataFrame(round_data), current_round)
        
        # Create temp directory and save predictions
        os.makedirs("API_submission_temp", exist_ok=True)
        temp_csv_path = "API_submission_temp/predictions.csv"
        pd.DataFrame(predictions).to_csv(temp_csv_path, index=False)

        # Submit predictions
        submission_response = api_client.submit_predictions(temp_csv_path)
        
        # Clean up temp file
        if os.path.exists(temp_csv_path):
            os.remove(temp_csv_path)
        if os.path.exists("API_submission_temp"):
            os.rmdir("API_submission_temp")

        if isinstance(submission_response, dict) and "error" in submission_response:
            return jsonify({"error": f"Submission failed: {submission_response['error']}"}), 500
            
        return jsonify({"status": "Strategy submitted successfully", "round": current_round}), 200

    except ValueError as ve:
        # Clean up temp files in case of error
        if os.path.exists("API_submission_temp/predictions.csv"):
            os.remove("API_submission_temp/predictions.csv")
        if os.path.exists("API_submission_temp"):
            os.rmdir("API_submission_temp")
        error_details = traceback.format_exc()
        print(f"ValueError in /submit: {str(ve)}\nDetails: {error_details}")
        return jsonify({"error": f"ValueError: {str(ve)}", 'details': error_details}), 400 # Return 400 for bad code

    except Exception as e:
        # Clean up temp files in case of error
        if os.path.exists("API_submission_temp/predictions.csv"):
            os.remove("API_submission_temp/predictions.csv")
        if os.path.exists("API_submission_temp"):
            os.rmdir("API_submission_temp")
        error_details = traceback.format_exc()
        print(f"Exception in /submit: {str(e)}\nDetails: {error_details}")
        return jsonify({"error": str(e), 'details': error_details}), 500

@socketio.on('connect')
def handle_connect():
    welcome_message = "Welcome to Numin platform! I'll help you write python code for financial trading strategies. Let's get started!"
    send(welcome_message)

@socketio.on('message')
def handle_message(data):
    try:
        response = agent_executor.invoke({"messages": [HumanMessage(content=data)]},config)

        send(response['messages'][-1].content)
    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        print(error_message)
        send(error_message)

@app.route('/hello')
def hello():
    response = model.invoke("Explain how AI works")
    return jsonify({"message": response.content})

if __name__ == '__main__':
    socketio.run(app, 
        host='127.0.0.1',
        port=5000,
        debug=True,
        allow_unsafe_werkzeug=True,
        use_reloader=False  # Disable reloader to prevent duplicate Socket.IO instances
    )