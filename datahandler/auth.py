from flask import jsonify, request
import requests
import os
from config import *
from auth import *

import sys

global current_token
current_token = None


def auth_header():
    return {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + current_token
    }

HEADERS = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }


def login():
    url = BASE_URL + 'auths/signin'
    
    data = {
        'email': os.getenv('DEFAULT_USERNAME'),
        'password': os.getenv('DEFAULT_PASSWORD')
    }
    
    try:
        response = requests.post(url, headers=HEADERS, json=data)
        global current_token
        current_token = response.json()["token"]
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
    
def signup():
    url = BASE_URL + 'auths/signup'

    data ={
    "name": os.getenv('DEFAULT_USERNAME'),
    "email": os.getenv('DEFAULT_USERNAME'),
    "password": os.getenv('DEFAULT_PASSWORD')
    }

    try:
        response = requests.post(url, headers=HEADERS, json=data)
        return login()
    except Exception as err:
        print(err, file=sys.stderr)
        return None
    

def get_api():
    url = BASE_URL + 'auths/api_key'

    try:
        response = requests.get(url, headers=auth_header())
        return response.json()
    except Exception as err:
        print(err, file=sys.stderr)
        return None  
    
def session():
    url = BASE_URL + 'auths/'

    try:
        response = requests.get(url, headers=HEADERS)
        if response.json()["detail"] == "Not authenticated":
            return None
        
        return response.json()
    except Exception as err:
        print(err, file=sys.stderr)
        return None
    
def auth_routes(app):    
    @app.route('/login', methods=['GET'])
    def token():
        return jsonify(auth())
