from openai import AsyncOpenAI
import json
from outlines import models
from outlines.models.openai import OpenAIConfig

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


def outlines_request(query, model='llama3.2:3b', form=example_schema):
    
    if isinstance(form, dict):
        form = json.dumps(form)

    generator = generate.json(get_model(model), form)
    result = generator(query)
    print(result, file=sys.stderr)
    return result


def outlines_routes(app):
    @app.route('/outlines', methods=['POST'])
    def outlines_route():
        
        print(request.json, file=sys.stderr)
        
        query = request.json.get('query', 'Are you there?')
        model = request.json.get('model', 'llama3.2:3b')
        form = request.json.get('form', example_schema)        
       
        response = outlines_request(query, model, form)
        
        print(response, file=sys.stderr)

        return jsonify({"response": response})