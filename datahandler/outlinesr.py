from openai import AsyncOpenAI
import json
from outlines import models
from outlines.models.openai import OpenAIConfig

import requests
from flask import request, jsonify
import sys
from urllib.parse import unquote as URLDecoder


# curl http://localhost:11434/v1/chat/completions     -H "Content-Type: application/json"     -d '{
#         "model": "llama3.2:3b",
#         "messages": [
#             {
#                 "role": "system",
#                 "content": "You are a helpful assistant."
#             },
#             {
#                 "role": "user",
#                 "content": "Hello!"
#             }
#         ]
#     }'

from outlines import generate
import os


client = AsyncOpenAI(
    base_url="http://ollama:11434/v1",
    api_key=os.environ.get("PROVIDER_KEY"),
)

def get_model(model_name="llama3.2:3b"):
    config = OpenAIConfig(model_name)
    model = models.openai(client, config)
    return model


example_schema = """{
    "$defs": {
        "Status": {
            "enum": ["success", "failure"],
            "title": "Status",
            "type": "string"
        }
    },
    "properties": {
        "status": {
            "$ref": "#/$defs/Status"
        },
        "response": {
            "type": "string"
        }
    },
    "required": ["status", "response"],
    "title": "Structured Response",
    "type": "object"
}"""

file_schema = """{
    "$defs": {
        "Chapter": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string"
                },
                "page": {
                    "type": "integer"
                }
            },
            "required": ["title"]
        }
    },
    "properties": {
        "title": {
            "type": "string"
        },
        "date": {
            "type": "string",
            "format": "date-time"
        },
        "chapters": {
            "type": "array",
            "items": {
                "$ref": "#/$defs/Chapter"
            }
        },
        "summary": {
            "type": "string"
        }
    },
    "required": ["title", "chapters"],
    "title": "Document",
    "type": "object",
    "description": "A structured representation of a document with chapters and a summary."
}"""

home_schema = """{
    "properties": {
        "address": {
            "type": "string"
        },
        "bedrooms": {
            "type": "integer"
        },
        "bathrooms": {
            "type": "integer"
        },
        "square_footage": {
            "type": "integer"
        },
        "year_built": {
            "type": "integer"
        },
        "type": {
            "type": "string"
        },
        "stories": {
            "type": "integer"
        },
        "basement": {
            "type": "boolean"
        },
        "garage": {
            "type": "boolean"
        },
        "pool": {
            "type": "boolean"
        },
        "roof_type": {
            "type": "string"
        },
        "location": {
            "type": "string"
        }
    },
    "required": ["address", "type"],
    "title": "Home",
    "type": "object"
}"""

def outlines_request(query, model='llama3.2:3b', form=example_schema):
    
    if isinstance(form, dict):
        form = json.dumps(form)

    generator = generate.json(get_model(model), form)
    result = generator(query)
    print(result, file=sys.stderr)
    return result

def file_handler(file):

    # Check if a file was selected
    if file.filename == '':
        print("No file selected", file=sys.stderr)
        return jsonify({"error": "No file selected"}), 400

    # Save the file to a temporary location
    temp_path = os.path.join('/tmp', file.filename)
    file.save(temp_path)

    # if the file is plain text, read it
    if file.content_type == 'text/plain':
        with open(temp_path, 'r') as f:
            file_content = f.read()
    elif file.content_type == 'application/pdf':
        # extract with tika
        url = "http://tika:9998/tika"
        headers = {
            'Content-Type': 'application/pdf',
            'Accept': 'text/plain'
        }
        
        with open(temp_path, 'rb') as f:
            pdf_data = f.read()
        response = requests.put(url, data=pdf_data, headers=headers)
        if response.status_code == 200:
            file_content = response.text
        else:
            print(f"Error extracting PDF: {response.status_code}", file=sys.stderr)
            return jsonify({"error": "Error extracting PDF"}), 500

    os.remove(temp_path)
    
    return file_content

def outlines_routes(app):
    @app.route('/outlines', methods=['POST'])
    def outlines_route():
        
        print(request.json, file=sys.stderr)
        
        query = request.json.get('query', 'Are you there?')
        model = request.json.get('model', 'llama3.2:3b')
        form = request.json.get('form', example_schema)        
       
        response = outlines_request(query, model, form)
        
        print(response, file=sys.stderr)

        return jsonify(response)
        
    @app.route('/upload', methods=['POST'])
    def upload_file():

        # Check if a file is included in the request
        if 'file' not in request.files:
            print("No file part in the request", file=sys.stderr)
            return jsonify({"error": "No file part in the request"}), 400

        file_content = file_handler(request.files['file'])

        # Extract additional data from the form
        query = request.form.get('query', 'Summarize this file.')
        model = request.form.get('model', 'llama3.2:3b')
        form = request.form.get('form', file_schema)
        
        #print(file_content, file=sys.stderr)
        print(query, file=sys.stderr)
        print(model, file=sys.stderr)
        print(form, file=sys.stderr)

        response = outlines_request(query + ' File: ' + file_content, model, form)
        print(response, file=sys.stderr)
        return jsonify(response)
    
    @app.route('/home', methods=['POST'])
    def home_route():
        
        if 'file' not in request.files:
            print("No file part in the request", file=sys.stderr)
            return jsonify({"error": "No file part in the request"}), 400
        
        file_content = file_handler(request.files['file'])
        
        # Extract additional data from the form
        query = request.form.get('query', 'Summarize this home inspection.')
        model = request.form.get('model', 'llama3.2:3b')
        form = request.form.get('form', home_schema)
        
        #print(file_content, file=sys.stderr)
        print(query, file=sys.stderr)
        print(model, file=sys.stderr)
        print(form, file=sys.stderr)
        
        response = outlines_request(query + ' File: ' + file_content, model, form)
        print(response, file=sys.stderr)
        return jsonify(response)