"""
title: Home Health Record Framework
author: Tristan Hook
author_url: https://captn-hook.github.io/
git_url: https://github.com/captn-hook/SimpleSearch
description: This tool uses outlines to structure Home Health Record.
required_open_webui_version: 0.4.0
requirements:
version: 0.4.0
licence: MIT
"""
import json
import requests

default_model = "llama3.2:3b"

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

list_schema = """{
    "$defs": {
        "Item": {
            "properties": {
                "name": {
                    "type": "string"
                },
                "type": {
                    "type": "string"
                },
                "score": {
                    "type": "number"
                }
            }
        }
    },
    "properties": {
        "items": {
            "items": {
                "$ref": "#/$defs/Item"
            },
            "type": "array"
        }
    },
    "required": ["items"],
    "title": "List",
    "type": "object"
}"""    

def get_response(query, model, form):
    """
    This function sends a request to the data handler API and returns the response.
    
    :param query: The query string to be sent to the API.
    :param model: The model to be used for the request.
    :param form: The form data to be sent in the request.
    :return: The response from the API.
    """
    print("Starting get_response function")
    url = "http://datahandler:5000/outlines"

    try:
        json_data = {
            "query": query,
            "model": model,
            "form": form
        }
        headers = {
            "Content-Type": "application/json"
        }
        response = requests.post(url, json=json_data, headers=headers)
        response.raise_for_status()  # Raise an error for bad responses
        response_data = response.json()
        print("Response received:", response_data)
        return response_data.get("response")
    except Exception as e:
        print(f"Error occurred: {e}")
        return {"error": str(e)}

class Tools:
    def __init__(self):
        pass
   
    async def list_response(
        self,
        message: str = "",
        __files__: list = []
    ) -> dict:
        """
        This tool is used to create lists of items. If a user
        asks for a list, use this tool to structure the list
        and return all the requested items to the user.
        :param message: The message to be processed.
        :param __files__: The files to be processed.
        :return: The structured response.
        """
        
        print("Starting list_response function")
        model = default_model
        form = list_schema
        query = message
        
        if __files__:
            print("Files provided:", __files__)
            query += " " + " File: ".join(__files__)
            

        response = get_response(query, model, form)
        return response
    