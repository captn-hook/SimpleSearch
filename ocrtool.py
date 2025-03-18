import os
import requests
from datetime import datetime
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from open_webui.models.tools import (
    ToolForm,
    ToolModel,
    ToolResponse,
    Tools,
)
from open_webui.models.users import Users
from pathlib import Path
from typing import Optional
from open_webui.models.tools import (
    ToolForm,
    ToolModel,
    ToolResponse,
    Tools,
)
from open_webui.config import CACHE_DIR, DATA_DIR
from typing import Optional

from open_webui.models.models import (
    ModelForm,
    ModelModel,
    ModelResponse,
    Models,
)
from open_webui.constants import ERROR_MESSAGES
from fastapi import APIRouter, Depends, HTTPException, Request, status


class Tools:
    def __init__(self):
        # Specify the Tesseract-OCR executable path
        pytesseract.pytesseract.tesseract_cmd = r"C://Users//muhammad.tayyab//AppData//Local//Programs//Tesseract-OCR//tesseract.exe"

    def get_user_name_and_email_and_id(self, __user__: dict = {}) -> str:
        """
        Get the user name, Email and ID from the user object.
        """
        print(__user__)
        result = ""

        if "name" in __user__:
            result += f"User: {__user__['name']}"
        if "id" in __user__:
            result += f" (ID: {__user__['id']})"
        if "email" in __user__:
            result += f" (Email: {__user__['email']})"

        if result == "":
            result = "User: Unknown"

        return result

    def get_current_time(self) -> str:
        """
        Get the current time in a more human-readable format.
        :return: The current time.
        """
        now = datetime.now()
        current_time = now.strftime("%I:%M:%S %p")
        current_date = now.strftime("%A, %B %d, %Y")
        return f"Current Date and Time = {current_date}, {current_time}"

    def calculator(self, equation: str) -> str:
        """
        Calculate the result of an equation.
        :param equation: The equation to calculate.
        """
        try:
            result = eval(equation)
            return f"{equation} = {result}"
        except Exception as e:
            print(e)
            return "Invalid equation"

    def get_current_weather(self, city: str) -> str:
        """
        Get the current weather for a given city.
        :param city: The name of the city to get the weather for.
        :return: The current weather information or an error message.
        """
        api_key = os.getenv("OPENWEATHER_API_KEY")
        if not api_key:
            return (
                "API key is not set in the environment variable 'OPENWEATHER_API_KEY'."
            )

        base_url = "http://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": api_key,
            "units": "metric",
        }

        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("cod") != 200:
                return f"Error fetching weather data: {data.get('message')}"

            weather_description = data["weather"][0]["description"]
            temperature = data["main"]["temp"]
            humidity = data["main"]["humidity"]
            wind_speed = data["wind"]["speed"]

            return f"Weather in {city}: {temperature}°C"
        except requests.RequestException as e:
            return f"Error fetching weather data: {str(e)}"

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract text from a scanned PDF file using OCR.
        :param pdf_path: Path to the PDF file.
        :return: Extracted text from the PDF.
        """
        extracted_text = ""

        try:
            # Open the PDF file
            pdf_document = fitz.open(pdf_path)

            for page_num in range(len(pdf_document)):
                # Get the page
                page = pdf_document[page_num]
                # Render the page to an image
                pix = page.get_pixmap()
                # Convert the image to a PIL Image
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                # Use pytesseract to do OCR on the image
                text = pytesseract.image_to_string(img)
                extracted_text += f"Page {page_num + 1}:\n{text}\n\n"

            pdf_document.close()
        except Exception as e:
            return f"Error extracting text from PDF: {str(e)}"

        return extracted_text.strip()  # Return extracted text without trailing spaces


# Example of usage
if __name__ == "__main__":
    tools = Tools()
    upload_directory = "/app/backend/data/uploads/"

    # List all PDF files in the upload directory
    for filename in os.listdir(upload_directory):
        if filename.endswith(".pdf"):
            pdf_path = os.path.join(upload_directory, filename)
            extracted_text = tools.extract_text_from_pdf(pdf_path)
            print(f"Extracted text from {filename}:\n{extracted_text}\n{'-' * 40}\n")
