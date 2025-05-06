"""
title: Home Health Record Framework
author: Tristan Hook
author_url: https://captn-hook.github.io/
git_url: https://github.com/captn-hook/SimpleSearch
description: This tool uses ollama to structure Home Health Record.
required_open_webui_version: 0.4.0
requirements: ollama
version: 0.4.0
licence: MIT
"""

from pydantic import BaseModel, Field
from typing import List

from ollama import chat

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


class Tools:

    def __init__(self):
        pass
    
    async def structure_home_health_record(
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

        # if there are files, use them to fill out the home health record
        if __files__:
            for file in __files__:
                message += f"\n\n{file['name']}: {file['content']}"

        response = chat(
        messages=[
            {
                "role": "user",
                "content": message,
            },
        ],
        model=__model__,
        format=HomeHealthRecord.model_json_schema(),
        )

        res = HomeHealthRecord.model_validate_json(response.message.content)
        
        return res