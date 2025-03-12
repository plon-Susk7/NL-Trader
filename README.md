# **NL-Trader**

**NL-Trader** is a project where my colleague and I aim to develop a chatbot capable of generating Python code for trading strategies based on instructions provided by traders in natural language.  

This tool bridges the gap between trading experts and coding by automating strategy implementation.

---

## **Project Structure**

We are using a monorepo structure:  

- **Backend**: Written in Python (Flask), located in the `backend` directory.  
- **Frontend**: A React.js application (TypeScript), located in the root directory.

---

## **Setup Instructions**

### **Backend Setup**

1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy contents of .env.local and paste your `Google API KEY` in a new file called .env
   
4. Start the Flask server:
   ```bash
   flask run
   ```

## **Frontend Setup**

1. Navigate to the root directory.
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```
