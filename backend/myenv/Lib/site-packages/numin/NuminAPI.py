import pandas as pd
import requests
from io import StringIO
import os
import base64
import io 
import pickle
from .backtest_wrapper import UserBacktestStrategy
from .utils import Backtest, DataFeed, discretize_features_feed, add_addl_features_feed, add_logical_features_feed
import warnings
import anvil.server
import anvil.media
from anvil import BlobMedia

warnings.filterwarnings('ignore')

# Class Definition

class NuminAPI():
    def __init__(self, api_key: str = None):
        """
        Initializes the NuminAPI instance.

        Parameters:
        - api_key (str, optional): The API key for authenticating requests.
        """
        
        self.api_key = api_key
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.discretizer_path = os.path.join(current_dir, "utils", "discretizers.pickle")
        
        # with open (self.discretizer_path, 'rb') as f:
        #     self.discretizer = pickle.load(f)
        
        # Published Anvil app's URL
        # https://familiar-subtle-comment.anvil.app
        # self.base_url = "https://beneficial-absolute-depth.anvil.app/_/api" # TEST
        # self.base_url = "https://familiar-subtle-comment.anvil.app/_/api" # Numin BUILD
        self.base_url = "https://numin-tournament.anvil.app/_/api" # Numin PROD

    def get_data(self, data_type: str):
        """
        Fetches the specified type of data (e.g., 'training' or 'round') from the server 
        and returns it as a DataFrame.

        Parameters:
        - data_type (str): The type of data to fetch. Must be 'training' or 'round' or 'validation'.

        Returns:
        - pd.DataFrame: Data from the CSV file.
        """
        if data_type not in ["training", "round", "validation"]:
            return {"error": "Invalid data_type. Must be 'training', 'round' or 'validation'."}

        url = f"{self.base_url}/download_data"
        response = requests.post(url, json={"type": data_type})  # Send type as JSON payload

        if response.status_code == 200:
            if data_type == "round" or data_type == "validation":
                # The endpoint returns the file content; we'll treat response.text as CSV.
                return pd.read_csv(StringIO(response.text))
            elif data_type == "training":
                # Treat the response as a ZIP file and return it as a file-like object
                return io.BytesIO(response.content)
        else:
            return {"error": f"Failed to fetch {data_type} data: {response.text}"}

    def submit_predictions(self, file_path: str):
        """
        Submits predictions to the server by uploading a CSV file.
        Requires API key authentication.

        Parameters:
        - file_path (str): Path to the CSV file with columns ["id", "predictions", "round_no"].

        Returns:
        - dict: JSON response from the server.
        """
        if not self.api_key:
            return {"error": "API key is required to submit predictions."}

        if not os.path.exists(file_path):
            return {"error": f"No such file: '{file_path}'"}

        # Check if required columns are present
        required_columns = ["id", "predictions", "round_no"]
        df = pd.read_csv(file_path, nrows=1)
        if not all(column in df.columns for column in required_columns):
            return {"error": f"CSV file must contain columns: {required_columns}"}

        url = f"{self.base_url}/upload_predictions"
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "text/csv")}
            data = {"api_key": self.api_key}
            
            file_content = base64.b64encode(f.read()).decode('utf-8')

            # Create JSON payload
            payload = {
                "api_key": self.api_key,
                "file_name": os.path.basename(file_path),
                "file_content": file_content,
                "content_type": "text/csv"
            }
                        
            response = requests.post(url, json=payload)

        # return response.text
        try:
            response_data = response.json()  # Parse JSON response
        except ValueError:
            print(f"Raw server response: {response.text}")  # Debugging
            return {"error": f"Server returned non-JSON response: {response.text}"}

        if response.status_code == 200:
            if response_data.get("status") == "success":
                return response_data
            else:
                return {"error": f"Failed to submit predictions: {response_data.get('message', 'Unknown error')}"}
        else:
            return {"error": f"Failed to submit predictions: {response.text}"}

    def get_current_round(self):
        """
        Fetches the current round number from the server.

        Returns:
        - str: The current round number.
        """
        
        url = f"{self.base_url}/get_current_round"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                return data.get("message")
            else:
                return {"error": f"Failed to get current round: {data.get('message')}"}
        else:
            return {"error": f"Failed to get current round: {response.text}"}
    
    def fetch_validation_data(self, date):
        """
        Fetches validation data for a given date from the Anvil API.

        Parameters:
        - date (str): Date in 'YYYY-MM-DD' format.

        Returns:
        - pd.DataFrame: Validation data if successful.
        - dict: Error message if unsuccessful.
        """
        url = f"{self.base_url}/download_validation_data"
        payload = {"date": date}
        
        try:
            response = requests.post(url, json=payload)

            if response.status_code == 200:
                # If server returns a JSON error message, handle it
                if "application/json" in response.headers.get("Content-Type", ""):
                    return response.json()
                
                # Otherwise, assume it's a CSV file
                return pd.read_csv(io.StringIO(response.text))

            return {"status": "error", "message": f"Failed to fetch validation data: {response.text}"}

        except requests.RequestException as e:
            return {"status": "error", "message": f"Request failed: {str(e)}"} 
    
    def get_validation_dates(self):
        """
        Fetches the list of dates for which a validation CSV file is available from the server.

        Returns:
        - list: List of date strings in 'YYYY-MM-DD' format if successful.
        - dict: An error message dictionary if an error occurs.
        """
        url = f"{self.base_url}/get_validation_dates"
        try:
            response = requests.get(url, timeout=10)
        except requests.RequestException as req_err:
            return {"error": f"Request failed: {str(req_err)}"}

        if response.status_code == 200:
            try:
                data = response.json()
            except ValueError:
                return {"error": f"Non-JSON response received: {response.text}"}
            
            if data.get("status") == "success":
                dates = data.get("dates")
                if dates is None:
                    return {"error": "No dates key in response."}
                return dates
            else:
                return {"error": f"Server error: {data.get('message', 'Unknown error')}"}
        else:
            return {"error": f"Failed to fetch validation dates. HTTP Status {response.status_code}: {response.text}"}

    
    def run_backtest(self, user_strategy, date=None, val_data=None, result_type="results"):
        """
        Runs backtesting on a given user strategy.

        Parameters:
        - user_strategy (function, required): A function that takes a pandas DataFrame and returns predictions.
        - date (str, required): Date in 'YYYY-MM-DD' format (mandatory).
        - val_data (str, optional): Path to a CSV file containing validation data. If provided, `date` must also be given.
        - result_type (str): "results" to return bt.results, "returns" to return bt.returns.

        Returns:
        - dict: Backtest results or returns based on `result_type`.
        """

        # Validation: `date` is mandatory
        if not date:
            raise ValueError("You must provide a 'date' (YYYY-MM-DD).")

        # Validation: If `val_data` is given, `date` must also be given (which is already ensured above)
        if val_data and not os.path.exists(val_data):
            raise FileNotFoundError(f"File not found: {val_data}")

        # Load validation data
        if val_data:  # Load from CSV
            print(f"Loading data from provided CSV: {val_data}")
            df = pd.read_csv(val_data)
        else:  # Fetch from Anvil API
            print(f"Fetching validation data from Anvil for date: {date}")
            df = self.fetch_validation_data(date)

            # If API returns an error (dict instead of DataFrame), stop execution
            if isinstance(df, dict) and df.get("status") == "error":
                return df

        # Convert tradeframe (ensure proper column formatting)
        self._convert_tradeframe(df, date=date)

        # Create DataFeed object
        tickers_list = list(df["id"].unique())
        dataFeed = DataFeed(tickers=tickers_list[:50], dfgiven=True, df=df)

        # Add additional features
        add_addl_features_feed(feed=dataFeed, tickers=dataFeed.tickers, drop_ta=False)
        _ = add_logical_features_feed(dataFeed)

        # Load discretizers
        # with open(self.discretizer_path, "rb") as f:
        #     discretizers = pickle.load(f)
        # DkD = discretizers[2]

        # # Discretize features
        # discretize_features_feed(dataFeed, DkD, "alllog")

        # Initialize Backtest object
        bt = Backtest(
            dataFeed,
            tickers=dataFeed.tickers,
            add_features=False,
            target=0.05,
            stop=0.01,
            txcost=0.001,
            loc_exit=False,
            scan=True,
            topk=10,
            deploy=True,
            save_dfs=False,
            t_limit=10
        )

        # Initialize user strategy wrapper
        user_strategy_wrapper = UserBacktestStrategy(user_strategy)

        # Run backtest
        bt.run_all(tickers=dataFeed.tickers, model=user_strategy_wrapper)

        # Return requested result
        if result_type == "results":
            return bt.results
        elif result_type == "returns":
            return bt.returns
        else:
            raise ValueError("Invalid result_type. Must be 'results' or 'returns'.")

    
    def _convert_tradeframe(self, df, date):
        """
        Converts the raw validation DataFrame into the proper tradeframe format.
        """
        df["Open"] = df["Open_n"]
        df["High"] = df["High_n"]
        df["Low"] = df["Low_n"]
        df["Close"] = df["Close_n"]
        df["ticker"] = df["id"]
        df["Volume"] = 1
        basedt = pd.to_datetime(f"{date} 09:15:00")

        def setdt(row):
            if row["row_num"] < 75:
                return basedt - pd.Timedelta(days=1) + pd.Timedelta(minutes=5 * row["row_num"])
            else:
                return basedt + pd.Timedelta(minutes=5 * (row["row_num"] - 75))

        def getdt(row):
            return row["Datetime"].strftime("%d-%b-%Y")

        df["Datetime"] = df.apply(setdt, axis=1)
        df["Date"] = df.apply(getdt, axis=1)
      
    def upload_file(self, file, user_id=None, filename=None):
        try:
            # Get filename
            final_filename = user_id + "_" + (filename if filename else file.filename)
            print(final_filename)
            # Connect to Anvil server
            anvil.server.connect("FMQBTGZ2T6DRDZISLDZ3XMIH-BRX4OESLV4HADBHN-CLIENT")
            # anvil.server.connect(os.getenv("ANVIL_CLIENT_KEY"))
            print("Connected to Anvil server")
            # Convert uploaded file directly to anvil media
            file_content = file.read()
            anvil_file = BlobMedia("application/python", file_content, name=final_filename)
            success = anvil.server.call('upload_files_remote', anvil_file)
            print("File uploaded successfully")
            if not success:
                error_msg = "Failed to upload file to remote storage"
                return {"error": error_msg}

            success_msg = f"File uploaded successfully as {final_filename}"
            return {"message": success_msg}
            
        except Exception as e:
            error_msg = f"Upload error: {str(e)}"
            return {"error": error_msg}

    def deploy_file(self, filename: str, user_id: str):
        try:
            # anvil.server.connect(os.getenv("ANVIL_CLIENT_KEY"))
            anvil.server.connect("FMQBTGZ2T6DRDZISLDZ3XMIH-BRX4OESLV4HADBHN-CLIENT")
            print("Server Connected!")
            success = anvil.server.call('deploy_file_remote', filename, user_id)
            print("File deployed successfully")
            if not success:
                error_msg = "Failed to deploy file"
                return {"error": error_msg}
            
            success_msg = f"File deployed successfully for user: {user_id}"
            return {"message": success_msg}
        except Exception as e:
            error_msg = f"Deployment error: {str(e)}"
            return {"error": error_msg}
