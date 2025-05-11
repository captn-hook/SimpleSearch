from flask import Flask, jsonify, send_file, redirect, request
import requests
from requests.auth import HTTPBasicAuth # for opensearch if we enable security
from urllib.parse import unquote as URLDecoder
import os
import sys
import time

from knowledge import knowledge_routes, sync
from opensearch import get_opensearch
from auth import *
from wiki import wiki_routes
from outlinesr import outlines_routes

from config import *

app = Flask(__name__)

auth_routes(app)
wiki_routes(app)
knowledge_routes(app)
outlines_routes(app)

@app.route('/')
def explorer():
    return open('index.html').read()

    
if __name__ == '__main__':
    
    time.sleep(10) # docker depend-on isnt waiting for the api to be ready
    print('Trying to authenticate')
    print(auth())
    while get_api() is None:
        print('Trying to authenticate')
        print(auth())
        time.sleep(5)
    time.sleep(1)

    # make sure opensearch is ready
    while get_opensearch() is None:
        print('Waiting for OpenSearch')
        time.sleep(5)

    # run start up sync
    if os.getenv('SYNC_ON_STARTUP', 'false').lower() == 'true':
        print('Syncing wiki')
       # print(sync_wiki())
        print('Syncing root')
        files = []
        if not os.path.exists(BASE_DIRECTORY):
            print(f"Base directory '{BASE_DIRECTORY}' does not exist. Creating it.", file=sys.stderr)
            os.makedirs(BASE_DIRECTORY)
        if not os.path.exists(WIKI_DIR):
            print(f"Wiki directory '{WIKI_DIR}' does not exist. Creating it.", file=sys.stderr)
            os.makedirs(WIKI_DIR)
        
        directories = [BASE_DIRECTORY]

        while directories:
            current_directory = directories.pop()
            for entry in os.listdir(current_directory):
                full_path = os.path.join(current_directory, entry)
                if os.path.isdir(full_path):
                    directories.append(full_path)
                else:
                    files.append(full_path)
        print(files, file=sys.stderr)
        sync('Default', files)

    app.run(host='0.0.0.0', port=os.getenv('FLASK_PORT', 5000))