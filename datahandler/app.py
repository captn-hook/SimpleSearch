from flask import Flask, request, jsonify, send_file
import requests
import base64
from urllib.parse import unquote as URLDecoder
import os


username = 'absolutelyanadmin@me.com'
password = 'theRealPasswordMan'

# curl -X 'POST'   'http://open-webui:8080/api/v1/auths/signin'   -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '{
#   "email": "absolutelyanadmin@me.com",
#   "password": "theRealPasswordMan"
# }'

def login(username, password):
    url = 'http://open-webui:8080/api/v1/auths/signin'
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }
    data = {
        'email': username,
        'password': password
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()['accessToken']

token = login(username, password)
print(token)

app = Flask(__name__)

BASE_DIRECTORY = '/app/data/'

@app.route('/')
def explorer():
    return open('index.html').read()

@app.route('/dir/<path:path>', methods=['GET'])
def get_dir(path):
    return open('index.html').read()

@app.route('/file/<path:path>', methods=['GET'])
def get_file(path):
    return open('display.html').read()

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.getenv('FLASK_PORT', 5000))