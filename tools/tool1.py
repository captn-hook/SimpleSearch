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

appliances_schema = """{
    "$defs": {
        "Appliance": {
            "properties": {
                "type": {
                    "type": "string"
                },
                "brand": {
                    "type": "string"
                },
                "model": {
                    "type": "string"
                },
                "location": {
                    "type": "string"
                },
            }
        },
    },
    "properties": {
        "appliances": {
            "items": {
                "$ref": "#/$defs/Appliance"
            },
            "type": "array"
        }
    },
    "required": ["appliances"],
    "title": "Appliances",
    "type": "object"
}"""

home_schema = """{
    "properties": {
        "address": {
            "type": "string"
        },
        bedrooms: {
            "type": "integer"
        },
        bathrooms: {
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
    }
    "required": ["address", "type"]
    "title": "Home",
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
        if response_data.get("status") == "success":
            return response_data.get("response")
        else:
            raise ValueError("Failure: " + response_data.get("response", "Unknown error"))
    except Exception as e:
        print(f"Error occurred: {e}")
        return {"error": str(e)}

class Tools:
    def __init__(self):
        pass
   
    async def appliance_form(
        self,
        message: str = "",
        __event_emitter__: str = "",
        __event_call__: str = "",
        __user__: dict = {},
        __metadata__: dict = {},
        __messages__: list = [],
        __files__: list = [],
        __model__: str = ""
    ) -> dict:
        """
        This function is used to format appliance data from unstructured sources,
        such as home inspection reports or attached files. It returns a list of 
        appliance objects, which include details like type, brand, model, and 
        location in the home.
        :param message: Any string containing relevant appliance information.
        :return: List of appliances with their details.
        """
        # If there are files, append their content to the message
        if __files__:
            print(f"Files received: {__files__}")
            for file in __files__:
                print(f"File content: {file['content']}")
                message += f"\n\n{file['name']}: {file['content']}"
    
        response = get_response(
            query=message,
            model=__model__.get('id'),
            form=appliances_schema
        )
    
        return response
    