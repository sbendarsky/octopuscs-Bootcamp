from flask import Flask, render_template, redirect, url_for, request
from pymongo import MongoClient
import os


# Initialize Flask app and specify template folder
app = Flask(__name__, template_folder='templates')


# Fetching MongoDB credentials from environment variables
mongo_username = os.environ.get('MONGO_INITDB_ROOT_USERNAME')
mongo_password = os.environ.get('MONGO_INITDB_ROOT_PASSWORD')
mongo_host = os.environ.get('MONGO_HOST')
mongo_port = os.environ.get('MONGO_PORT')


# Constructing MongoDB URI if all environment variables are present
if all([mongo_username, mongo_password, mongo_host, mongo_port]):
    mongo_uri = f'mongodb://{mongo_username}:{mongo_password}@{mongo_host}:{mongo_port}/'
    app.config["MONGO_URI"] = mongo_uri
else:
    # Including MongoDB URI in the ValueError message
    mongo_uri_msg = f'mongodb://{mongo_username}:{mongo_password}@{mongo_host}:{mongo_port}/'
    raise ValueError(f"MongoDB environment variables are not properly set. MongoDB URI: {mongo_uri_msg}")


# Initialize MongoDB client
mongo = MongoClient(app.config["MONGO_URI"])


# Check if the voting_db database exists, if not, create it
if "voting_db" not in mongo.list_database_names():
    db = mongo["voting_db"]
    # Create collections for votes and user votes
    db.create_collection("votes")
    db.create_collection("user_votes")
else:
    db = mongo["voting_db"]


# Initialize the voting collection if it doesn't exist
if "candidates" not in db.list_collection_names():
    db.create_collection("candidates")
    # Insert initial data for biden and trump
    db.candidates.insert_many([
        {'name': 'biden', 'votes': 0},
        {'name': 'trump', 'votes': 0}
    ])


# Home page
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        biden_choice = request.form.get('biden')
        trump_choice = request.form.get('trump')
       
        # Update database with user's choices
        db.votes.insert_one({'name': name, 'biden_choice': biden_choice, 'trump_choice': trump_choice})
        db.user_votes.insert_one({'name': name, 'biden_choice': biden_choice, 'trump_choice': trump_choice})
       
        # Increment vote counts for selected candidates
        if biden_choice == "1":
            db.candidates.update_one({'name': 'biden'}, {'$inc': {'votes': 1}})
        elif trump_choice == "1":
            db.candidates.update_one({'name': 'trump'}, {'$inc': {'votes': 1}})
       
        # Redirect to dashboard
        return redirect(url_for('dashboard'))
    return render_template('home.html')


# Dashboard page
@app.route('/dashboard')
def dashboard():
    # Get all votes from database
    votes = list(db.user_votes.find())
    candidates = list(db.candidates.find())
    return render_template('dashboard.html', votes=votes, candidates=candidates)


# Run the app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)