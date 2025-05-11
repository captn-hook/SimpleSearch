import os
import sys
import requests
from flask import jsonify, send_file
from urllib.parse import unquote as URLDecoder
from flask import redirect

from auth import *

from config import *

def knowledge_routes(app):
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
        url = BASE_URL + 'knowledge/' + id

        try:
            response = requests.get(url, headers=auth_header())
            return response.json()
        except Exception as err:
            print(err, file=sys.stderr)
            return None
        
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
        print(files, file=sys.stderr)
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

def sync(name, files):
    id = None
    knowledge_list = list_knowledge()
    if knowledge_list is None:
        knowledge_list = list_knowledge()

    for knowledge in knowledge_list:
        if knowledge['name'] == name:
            id = knowledge['id']
            add_files_to_knowledge(id, files)
            return id

    if id is None:
        knowledge = create_knowledge(name, '')
        id = knowledge['id']

    add_files_to_knowledge(id, files)
    return id

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
    url = BASE_URL + 'knowledge/list'

    try:
        response = requests.get(url, headers=auth_header())
        return response.json()
    except Exception as err:
        print(err, file=sys.stderr)
        return None
    
def create_knowledge(name, description):
    url = BASE_URL + 'knowledge/create'

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
    
def get_all_files():
    url = BASE_URL + 'files/'

    try:
        response = requests.get(url, headers=auth_header())
        return response.json()
    except Exception as err:
        print(err, file=sys.stderr)
        return None
    
def upload_file(file, fileList=None, rename=None):
    from app import current_token
    url = BASE_URL + 'files/'
    headers = {
        'accept': 'application/json',
        'Authorization': 'Bearer ' + current_token
    }
    name = file.split('/')[-1]
    if rename is not None:
        name = rename

    file_metadata = {
        'name': name,
        'description': ''
    }
    
    files = { 
        'file': (file, open(file, 'rb')),
    }
    fileD = None
    # check if file exists
    try:
        if fileList is None: # filelist is passed in to make batch processing faster
            fileList = get_all_files()
        for f in fileList:
            if f['filename'] == file_metadata['name']:
                fileD = f
                break        
    except Exception as err:
        print(err, file=sys.stderr)

    if fileD is not None:
        # decide if we want to update it
        # for now, return the existing file
        return fileD
    else: # create file 
        try:
            response = requests.post(url, headers=headers, files=files)
            return response.json()
        except Exception as err:
            print(err, file=sys.stderr)
            return None
        
def add_files_to_knowledge(knowledge_id, files):
    url = BASE_URL + 'knowledge/' + knowledge_id + '/file/add'

    for file in files:
        res = upload_file(file, get_all_files())
        if res is not None:
            if res.get('id') is not None:
                data = { 
                    'file_id': res['id']
                }
                try:
                    response = requests.post(url, headers=auth_header(), json=data)
                except Exception as err:
                    print(err, file=sys.stderr)
                    return None
            else:
                print('Failed to upload, response: ' + str(res), file=sys.stderr)
    return requests.get(BASE_URL + 'knowledge/' + knowledge_id, headers=auth_header()).json()