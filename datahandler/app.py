from flask import Flask, jsonify, send_file, redirect
import requests
from urllib.parse import unquote as URLDecoder
import os
import sys
import time
import json


BASE_DIRECTORY = '/app/data/docs/'

wiki_dir = '/app/data/wiki/'

wiki_url = 'https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-pages-articles-multistream.xml.bz2'
index = 'https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-pages-articles-multistream-index.txt.bz2'

base_url = 'http://open-webui:8080/api/v1/'

global current_token
current_token = None

def auth_header():
    return {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + current_token
    }

headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }

def signup():
    print('Signing up as default user', file=sys.stderr)
    url = base_url + 'auths/signup'

    data ={
    "name": os.getenv('DEFAULT_USERNAME'),
    "email": os.getenv('DEFAULT_USERNAME'),
    "password": os.getenv('DEFAULT_PASSWORD')
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        return login()
    except Exception as err:
        print(err, file=sys.stderr)
        return None

def login():
    print('Logging in as default user', file=sys.stderr)
    url = base_url + 'auths/signin'
    
    data = {
        'email': os.getenv('DEFAULT_USERNAME'),
        'password': os.getenv('DEFAULT_PASSWORD')
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        global current_token
        current_token = response.json()["token"]
        return response.json()

    except Exception as err:
        print(err, file=sys.stderr)
        return None
    
def get_api():
    url = base_url + 'auths/api_key'

    try:
        response = requests.get(url, headers=auth_header())
        return response.json()
    except Exception as err:
        print(err, file=sys.stderr)
        return None  
    
def session():
    url = base_url + 'auths/'

    try:
        response = requests.get(url, headers=headers)
        if response.json()["detail"] == "Not authenticated":
            return None
        
        return response.json()
    except Exception as err:
        print(err, file=sys.stderr)
        return None
    
def auth():
    # if we have a valid token, return it
    global current_token
    if current_token is not None and get_api() is not None:
        return {"token": current_token}
    
    # get session -> if not exist -> login -> if not exist -> signup
    session_data = session()
    if session_data is None:
        login_data = login()
        if login_data is None:
            signup_data = signup()
            return signup_data
        else:
            return login_data
    else:
        return session_data

app = Flask(__name__)

@app.route('/login', methods=['GET'])
def token():
    return jsonify(auth())

@app.route('/')
def explorer():
    return open('index.html').read()

@app.route('/dir/<path:path>', methods=['GET'])
def get_dir(path):
    return open('index.html').read()

@app.route('/file/<path:path>', methods=['GET'])
def get_file(path):
    return open('display.html').read()

@app.route('/sync/', methods=['GET'])
def sync_root():
    files = []
    directories = [BASE_DIRECTORY]

    while directories:
        current_directory = directories.pop()
        for entry in os.listdir(current_directory):
            full_path = os.path.join(current_directory, entry)
            if os.path.isdir(full_path):
                directories.append(full_path)
            else:
                files.append(full_path)

    knowledgeid = sync('Default', files)
    return redirect('/knowledge/' + knowledgeid)

@app.route('/sync/dir/<path:path>', methods=['GET'])
def sync_dir(path):
    files = []
    for file in os.listdir(BASE_DIRECTORY + path):
        if os.path.isdir(os.path.join(BASE_DIRECTORY + path, file)):
            continue
        files.append(os.path.join(BASE_DIRECTORY + path, file))
    knowledgeid = sync(path.split('/')[-1], files)
    return redirect('/knowledge/' + knowledgeid)


@app.route('/get/<path:path>', methods=['GET'])
def get_file_content(path):
    try:
        path = URLDecoder(path)
        return send_file(BASE_DIRECTORY + path)
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404

@app.route('/list_files/<path:path>', methods=['GET'])
def list_files_dynamic(path):
    return list_files(path)

@app.route('/list_files', methods=['GET'])
def list_files_root():
    return list_files('')

@app.route('/list_knowledge', methods=['GET'])
def list_knowledge_dynamic():
    knowledge = list_knowledge()
    if knowledge is None:
        knowledge = list_knowledge()
    if knowledge is None:
        return jsonify([]), 404
    return jsonify(knowledge)

@app.route('/knowledge/<string:id>', methods=['GET'])
def get_knowledge(id):
    url = base_url + 'knowledge/' + id

    try:
        response = requests.get(url, headers=auth_header())
        return response.json()
    except Exception as err:
        print(err, file=sys.stderr)
        return None
    

def list_files(path):
    directory = BASE_DIRECTORY + path
    try:
        files = []
        dirs = []
        for file in os.listdir(directory):
            if os.path.isdir(os.path.join(directory, file)):
                dirs.append(file)
            else:
                files.append(file)
        return jsonify({"files": files, "dirs": dirs}), 200
    except FileNotFoundError:
        return jsonify({"error": "Directory not found"}), 404
    
def list_knowledge():
    url = base_url + 'knowledge/list'

    try:
        response = requests.get(url, headers=auth_header())
        return response.json()
    except Exception as err:
        print(err, file=sys.stderr)
        return None
    
def create_knowledge(name, description):
    url = base_url + 'knowledge/create'

    data = {
        "name": name,
        "description": description
        }
    
    try:
        response = requests.post(url, headers=auth_header(), json=data)
        return response.json()
    except Exception as err:
        print(err, file=sys.stderr)
        return None
    
def upload_file(file):
    url = base_url + 'files/'
    global current_token
    headers = {
        'accept': 'application/json',
        'Authorization': 'Bearer ' + current_token
    }
    
    file_metadata = {
        'name': file.split('/')[-1],
        'description': ''
    }
    
    files = { 
        'file': (file, open(file, 'rb')),
    }

    try:
        response = requests.post(url, headers=headers, files=files)
        return response.json()
    except Exception as err:
        print(err, file=sys.stderr)
        return None
    
def add_files_to_knowledge(knowledge_id, files):
    url = base_url + 'knowledge/' + knowledge_id + '/file/add'

    for file in files:
        res = upload_file(file)
        if res is not None:
            data = {
                'file_id': res['id']
            }
            try:
                response = requests.post(url, headers=auth_header(), json=data)
            except Exception as err:
                print(err, file=sys.stderr)
                return None
    return requests.get(base_url + 'knowledge/' + knowledge_id, headers=auth_header()).json()

def sync(name, files):
    id = None
    knowledge_list = list_knowledge()
    if knowledge_list is None:
        knowledge_list = list_knowledge()

    for knowledge in knowledge_list:
        if knowledge['name'] == name:
            id = knowledge['id']
            break

    if id is None:
        knowledge = create_knowledge(name, '')
        id = knowledge['id']

    add_files_to_knowledge(id, files)
    return id

if __name__ == '__main__':
    
    # If we dont have wikipedia, grab it
    if not os.path.exists(wiki_dir):
        os.makedirs(wiki_dir)
        if not os.path.exists(wiki_dir + wiki_url.split('/')[-1]):
            print('Downloading wikipedia', file=sys.stderr)
            os.system('wget ' + wiki_url + ' -P ' + wiki_dir)
            print('Downloaded wikipedia', file=sys.stderr)
            # Get the index
            print('Downloading wikipedia index', file=sys.stderr)
            os.system('wget ' + index + ' -P ' + wiki_dir)
            print('Downloaded wikipedia index', file=sys.stderr)
            # Sync to the database
            print('Syncing wikipedia', file=sys.stderr)
            sync_wiki(wiki_dir)
    print('Trying to authenticate', file=sys.stderr)
    print(auth())

    app.run(host='0.0.0.0', port=os.getenv('FLASK_PORT', 5000))