import os
import collections
from flask import Flask, request
from dotenv import load_dotenv
from flask_cors import CORS, cross_origin
import redis
from redis.commands.json.path import Path
import json

load_dotenv()

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
PORT = os.environ.get('PORT')
cache = redis.Redis(host='localhost', port=6379, db=0)

# Always contains '*' the cuurent string and 'end' if its an end of word, 
# else everything else are link letters

toAdd = {'*': 'a', 'end' : False}
# cache.json().set('trie','$', toAdd)
# print(cache.json().get('trie'))
# cache.json().get('trie')["next"].append({'word': 'a', 'end' : False, 'next': [None] * 26})
# print(cache.json().get('trie')['next'])

# cache.execute_command('JSON.SET', 'trie', '.', json.dumps(toAdd))
# cache.execute_command('JSON.SET', 'trie', '.a', json.dumps(toAdd))
# reply = json.loads(cache.execute_command('JSON.GET', 'trie', '.a.b'))
# print(reply)

# helper function to traverse trie and get up to 5 possible autocomplete
def getSuggestions(search):
    suggestions = []
    queue = collections.deque()
    queue.append(search)

    while queue and len(suggestions) < 5:
        cur = queue.popleft()
        if cur['end']:
            suggestions.append(cur['*'])
        del cur['*']
        del cur['end']
        for item in cur.values():
            queue.append(item)
    
    return suggestions


@app.route('/api/v1/health', methods=['GET'])
@cross_origin()
def health():
    return {'message':'OK'}

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
                curRedis = json.loads(cache.execute_command('JSON.GET', 'trie'))
            else:
                curRedis = json.loads(cache.execute_command('JSON.GET', 'trie', path))
            suggestions = getSuggestions(curRedis)
        except:
            print('except')
            pass

        return {'suggestions': suggestions}
    
    return {"message":"No input given"}

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=PORT)