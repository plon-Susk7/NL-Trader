# app.py
from flask import Flask, jsonify
from flask_socketio import SocketIO, send, emit
import google.generativeai as genai
import os

app = Flask(__name__)
socketio = SocketIO(app)
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")  # Initialize the model

@app.route('/hello')
def hello():
    global model  # Access the global model variable
    response = model.generate_content("Explain how AI works")
    print(response.text)
    return jsonify({"message": "Whatever!"})

@socketio.on('connect')
def handle_connect():
    send("Hey, you are connected!")

@socketio.on('message')
def handle_message(data):
    global model
    print("Received message: ", data)
    response = model.generate_content(data)
    send("Received message: " + response.text)
    

if __name__ == '__main__':
    socketio.run(app,debug=True)
