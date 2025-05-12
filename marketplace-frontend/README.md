📦 Campus Marketplace

A full-stack web application for a campus-based buy/sell platform using Flask (backend) and React (frontend).

🔧 Setup Instructions

🖥 Backend (Flask)

1. Navigate to the backend folder

cd path/to/backend

2. Create and activate a virtual environment (optional)

python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

3. Install required Python packages

pip install flask flask-cors flask-sqlalchemy werkzeug

4. (Optional) Reset the database

rm ./instance/database.db  # Windows: del .\instance\database.db

5. Run the Flask server

export FLASK_APP=app.py      # Windows: set FLASK_APP=app.py
flask run

The backend should now be running at: http://127.0.0.1:5000

The backend should now be running at: http://127.0.0.1:5000

🌐 Frontend (React)

1. Navigate to the frontend folder

cd path/to/frontend

2. Install frontend dependencies

npm install

3. Start the React development server

npm start

The frontend should now be running at: http://localhost:3000

🚀 Features

User signup & login

Listings creation, editing, and deletion

Dark/light theme toggle

Search and filter listings

Cart system

Buy & cancel transactions

Wallet deposit

Reviews per listing

Profile with purchase/sales history

📁 Project Structure

frontend/
  src/
    components/
      Home.js
      Listings.js
      ...
  public/
  package.json

backend/
  app.py
  models.py
  static/uploads/
  database.db (auto-generated)

🔄 API Endpoints (Flask)

POST /signup

POST /login

GET /listings

POST /listings

PUT /listings/<id>

DELETE /listings/<id>

POST /buy/<listing_id>

POST /cancel/<transaction_id>

GET /profile/<user_id>

GET /reviews/<listing_id>

POST /reviews/<listing_id>

GET /cart/<user_id>

POST /cart

DELETE /cart

POST /wallet/deposit

✅ Requirements

Python 3.7+

Node.js 14+

npm 6+

📬 Notes

Images are stored under /static/uploads/ on the backend.

The database uses SQLite and is created automatically.

Remember to enable CORS between frontend and backend.

📜 License

This project is built for educational/demo purposes.

