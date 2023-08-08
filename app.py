import os
import collections
from flask import Flask, request, Response, jsonify
from dotenv import load_dotenv
from flask_cors import CORS, cross_origin
import redis
from redis.commands.json.path import Path
import json
from firebase_admin import credentials, firestore, initialize_app

load_dotenv()

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
PORT = os.environ.get('PORT')

# Redis Config
REDIS_HOST = os.environ.get('REDIS_HOST')
REDIS_PASS = os.environ.get('REDIS_PASS')
REDIS_PORT = os.environ.get('REDIS_PORT')

# Initialize redis cache
cache = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASS, db=0)

# cache.json().set('trie','$', {'*':'', 'end': False})
# cache.execute_command('JSON.SET', 'trie', '.', {'*':'', 'end': False})

# Initialize Firestore DB
cred = credentials.Certificate('key.json')
default_app = initialize_app(cred)
db = firestore.client()
todo_ref = db.collection('templates')

# Always contains '*' the curent string and 'end' if its an end of word, 
# else everything else are link letters

# Get Trie view
# print(cache.json().get('trie'))

# Helper function to traverse trie and get up to 5 possible autocomplete
def getSuggestions(search):
    suggestions = []
    queue = collections.deque()
    queue.append(search)

    while queue and len(suggestions) < 5:
        cur = queue.popleft()
        if cur['end']:
            suggestions.append({'value': cur['*']})
        del cur['*']
        del cur['end']
        for item in cur.values():
            queue.append(item)
    
    return suggestions


# Health check endpoint
@app.route('/api/v1/health', methods=['GET'])
@cross_origin()
def health():
    return {'message':'OK'}

# Search feature, queries trie for prefix and returns possible ends
@app.route('/api/v1/query', methods=['GET'])
@cross_origin()
def query():
    if 'diagnosis' in request.args:
        diagnosis = request.args["diagnosis"]
        suggestions = []
        # print(diagnosis)

        # Get query path
        path = ""
        for letter in diagnosis:
            path = path + "." + letter
        
        # get json/trie
        try:
            if path == "":
                curRedis = cache.execute_command('JSON.GET', 'trie')
            else:
                curRedis = cache.execute_command('JSON.GET', 'trie', path)
            # print(curRedis)
            suggestions = getSuggestions(curRedis)
        except:
            print('except')
            pass
        # print(suggestions)
        return {'suggestions': suggestions}
    
    return {"message":"No input given"}

# Gets template from firebase db
@app.route('/api/v1/retrievetemplate', methods=['GET'])
@cross_origin()
def getTemplate():
    try:
        # Check if ID was passed to URL query
        diagnosis_id = request.args.get('diagnosis')
        if diagnosis_id:
            template = todo_ref.document(diagnosis_id).get()
            return jsonify(template.to_dict()), 200
        else:
            return {"message": "No diagnosis passed."}
    except Exception as e:
        return f"An Error Occurred: {e}"

# Adds diagnosis to trie and then persists in firebase db
@app.route('/api/v1/create', methods=['POST', 'OPTIONS'])
@cross_origin()
def create():
    if request.method == "OPTIONS":
        print('OPTIONS')
    # add to redis trie
    diagnosis = request.get_json()['diagnosis'].lower()
    diagnosis = ''.join(filter(str.isalnum, diagnosis))

    path = ""
    for index, letter in enumerate(diagnosis):
        path = path + "." + letter
        try:
            reply = cache.execute_command('JSON.GET', 'trie', path)
            # print(reply)
        except redis.exceptions.ResponseError as e:
            # print(e)
            toAdd = {'*': diagnosis[:index+1], 'end' : (index==len(diagnosis)-1)}
            cache.execute_command('JSON.SET', 'trie', path, json.dumps(toAdd))
        # print(cache.json().get('trie'))

    # add to firebase
    try:
        todo_ref.document(diagnosis).set(request.json)
        return jsonify({"completed": True}), 200
    except Exception as e:
        return f"An Error Occurred: {e}"


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=PORT)