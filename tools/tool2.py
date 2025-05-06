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
from pydantic import BaseModel, Field
from typing import List
import urllib.parse
import json


class Appliance(BaseModel):
    name: str = Field(
        default="",
        description="The name of the appliance.",
    )
    serial_number: str = Field(
        default="",
        description="The serial number of the appliance.",
    )
    warranty: str = Field(
        default="",
        description="The warranty information of the appliance.",
    )
    age: int = Field(
        default=0,
        description="The age of the appliance in years.",
    )
    room: str = Field(
        default="",
        description="The room where the appliance is located.",
    )
    installation_date: str = Field(
        default="",
        description="The installation date of the appliance.",
    )

class Sensor(BaseModel):
    name: str = Field(
        default="",
        description="The name of the sensor.",
    )
    type: str = Field(
        default="",
        description="The type of sensor (e.g., temperature, humidity, smoke).",
    )
    location: str = Field(
        default="",
        description="The location of the sensor in the home.",
    )

class HomeHealthRecord(BaseModel):
    home_address: str = Field(
        default="",
        description="The home address of the patient.",
    )
    home_type: str = Field(
        default="",
        description="The type of home (e.g., apartment, detached, semi-detached, terraced).",
    )
    year_built: int = Field(
        default=0,
        description="The year the home was built.",
    )
    location: str = Field(
        default="",
        description="The location of the home (latitude and longitude).",
    )
    soil_type: str = Field(
        default="",
        description="The type of soil the home is built on (e.g., clay, sand, stone).",
    )
    square_footage: int = Field(
        default=0,
        description="The square footage of the home.",
    )
    number_of_floors: int = Field(
        default=0,
        description="The number of floors in the home.",
    )
    number_of_living_rooms: int = Field(
        default=0,
        description="The number of living rooms in the home.",
    )
    number_of_bedrooms: int = Field(
        default=0,
        description="The number of bedrooms in the home.",
    )
    number_of_bathrooms: int = Field(
        default=0,
        description="The number of bathrooms in the home.",
    )
    basement: bool = Field(
        default=False,
        description="Whether the home has a basement.",
    )
    garage: bool = Field(
        default=False,
        description="Whether the home has a garage.",
    )
    wall_type: str = Field(
        default="",
        description="The type of walls in the home (e.g., brick, wood, concrete).",
    )
    pool: bool = Field(
        default=False,
        description="Whether the home has a pool.",
    )
    septic_tank: bool = Field(
        default=False,
        description="Whether the home has a septic tank.",
    )
    roof_type: str = Field(
        default="",
        description="The type of roof (e.g., flat, pitched, gabled).",
    )
    weather_conditions: str = Field(
        default="", # try to fetch this from the weather API
        description="The weather conditions in the area (e.g., humid, dry, rainy).",
    )
    appliances: List[Appliance] = Field(
        default_factory=list,
        description="A list of appliances in the home.",
    )
    sensors: List[Sensor] = Field(
        default_factory=list,
        description="A list of sensors in the home.",
    )

# # Example of a schema for the structured response
# schema = """{
#     "$defs": {
#         "Status": {
#             "enum": ["success", "failure"],
#             "title": "Status",
#             "type": "string"
#         }
#     },
#     "properties": {
#         "status": {
#             "$ref": "#/$defs/Status"
#         },
#         "response": {
#             "type": "string"
#         }
#     },
#     "required": ["status", "response"],
#     "title": "Structured Response",
#     "type": "object"
# }"""


def get_response(query, model, form):
    """
    This function sends a request to the data handler API and returns the response.
    
    :param query: The query string to be sent to the API.
    :param model: The model to be used for the request.
    :param form: The form data to be sent in the request.
    :return: The response from the API.
    """
    print("Starting get_response function")
    base_url = "http://datahandler:5000/outlines"
    # Ensure all inputs are strings before quoting
    url = f"{base_url}?query={urllib.parse.quote(str(query))}&model={urllib.parse.quote(str(model))}&form={urllib.parse.quote(form)}"
    print(url)
    try:
        request = urllib.request.Request(url)
        with urllib.request.urlopen(request) as response:
            response_data = response.read()
            response_json = json.loads(response_data.decode('utf-8'))
            return response_json.get("response", {})
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
        This is the tool for filling out a form with appliece information.
        Use it when trying to determine the appliance information from user
        provided data.
        :param message: Any string containing relevant appliance information.
        :return: Well formatted json with the fields for an appliance.
        """
        print("Starting appliance_form function")
        # if there are files, use them to fill out the home health record
        if __files__:
            for file in __files__:
                message += f"\n\n{file['name']}: {file['content']}"
    
        response = get_response(
            query=message,
            model=__model__.get('id'),
            form=json.dumps(Appliance.model_json_schema(), indent=2)
        )
    
        return response
    
    async def sensor_form(
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
        This is the tool for filling out a form with sensor information.
        Use it when trying to determine the sensor information from user
        provided data.
        :param message: Any string containing relevant sensor information.
        :return: Well formatted json with the fields for a sensor.
        """
        print("Starting sensor form")
        # if there are files, use them to fill out the home health record
        if __files__:
            for file in __files__:
                message += f"\n\n{file['name']}: {file['content']}"
    
        response = get_response(
            query=message,
            model=__model__.get('id'),
            form=json.dumps(Sensor.model_json_schema(), indent=2)
        )
    
        return response
    
    async def home_health_record(
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
        Use infomation provided about a home to fill out a home health record as completely as possible.
        When the required information is not available, leave the field blank to fill in later.
        The user can provide answers to questions, home inspection reports, or appliance manuals to help fill out the home health record.

        :param message: The message to send to the model.
        
        """
        print('Starting home health record tool')
        # if there are files, use them to fill out the home health record
        if __files__:
            for file in __files__:
                file_name = file.get('name', 'Unknown File')
                file_content = file.get('content', 'No Content Available')
                message += f"\n\n{file_name}: {file_content}"
                
        response = get_response(
            query=message,
            model=__model__.get('id'),
            form=json.dumps(HomeHealthRecord.model_json_schema(), indent=2) 
        )
        
        print(response)
    
        return response