# app.py
from flask import Flask, jsonify
from flask_socketio import SocketIO, send, emit
from flask_cors import CORS
import google.generativeai as genai
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain.chains import ConversationChain
from langchain.prompts import PromptTemplate

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")
# genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
# model = genai.GenerativeModel("gemini-2.0-flash-exp")  # Initialize the model

model = ChatGoogleGenerativeAI(
    model = "gemini-2.0-flash-exp",
)


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

prompt_template = '''
You are best at writing python code and have good knowledge about finance. You'll assist people in converting their trading strategies into code.
You are provided with dataset containing information about financial and trading indicators. 
The dataset contains the following variables related to financial trading and technical indicators.
Strictly return python code when Human gives a strategy or asks to change the previous strategy, else ask them to provide a strategy.

{dataset_context}

Current conversation:
{history}
Human: {input}.
Assistant: Let me help you with that.

'''


# Create the prompt template with correct input variables
PROMPT = PromptTemplate(
    input_variables=["history", "input"],  # Removed 'context'
    template=prompt_template,
    partial_variables={"dataset_context": dataset_context}  # Add context as a partial variable
)

# Initialize memory
memory = ConversationBufferWindowMemory(
    k=10,
    return_messages=True,
    memory_key="history"
)

# Create conversation chain
conversation = ConversationChain(
    prompt=PROMPT,
    llm=model,
    memory=memory,
    verbose=True
)

@app.route('/hello')
def hello():
    response = model.invoke("Explain how AI works")
    return jsonify({"message": response.content})

@socketio.on('connect')
def handle_connect():
    welcome_message = "Welcome to Numin platform! I'll help you write python code for financial trading strategies. I don't like chitchats so let's get started!"
    send(welcome_message)

@socketio.on('message')
def handle_message(data):
    try:
        # Simply pass the input data
        response = conversation.predict(input=data)
        send(response)
    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        print(error_message)
        send(error_message)

if __name__ == '__main__':
    socketio.run(app, debug=True)
