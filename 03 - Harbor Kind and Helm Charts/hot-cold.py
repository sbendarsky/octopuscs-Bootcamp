# hot-cold.py

from flask import Flask

app = Flask(__name__)

# Route for the root page
@app.route('/')
def root():
    return '<html><body><h1>Welcome to the Hot/Cold App!</h1></body></html>'

# Route for the hot page
@app.route('/hot')
def hot():
    return '<html><body style="background-color:red;"><h1>This is the Hot page!</h1></body></html>'

# Route for the cold page
@app.route('/cold')
def cold():
    return '<html><body style="background-color:blue;"><h1>This is the Cold page!</h1></body></html>'

if __name__ == '__main__':
    # Run the Flask app
    app.run(host='0.0.0.0', port=8080)