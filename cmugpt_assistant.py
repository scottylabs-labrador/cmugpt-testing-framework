from openai import OpenAI, APITimeoutError, APIError
import json
from dotenv import load_dotenv
import os
import time
from perplexity_integration import CMUPerplexitySearch  # Changed from relative import
import requests
from googleapiclient.discovery import build
from google.oauth2 import service_account
import datetime
import os.path
from datetime import datetime
from tzlocal import get_localzone  # Auto-detect user's timezone
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# This scope allows for some modification to the calendar, as opposed to /calendar/readonly
SCOPES = ["https://www.googleapis.com/auth/calendar"]

def authenticate_google_calendar():
    """Authenticate and return the Google Calendar API service."""
    credentials_location = "credentials.json"
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_location, SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)
    return service

load_dotenv()

class CMUGPTAssistant:
    def __init__(self):
        # Set up OpenAI client with timeout configuration
        self.client = OpenAI(
            api_key=os.getenv('OPENAI_API_KEY'),
            timeout=60.0,  # 60 second timeout
            max_retries=3  # Allow 3 retries
        )
        
        # Define the function definitions (tools) for the model
        self.tools = self.get_tools()
        
        # Initialize conversation messages
        self.messages = [
            {
                "role": "system",
                "content": "You are CMUGPT, an assistant knowledgeable about Carnegie Mellon University in Pittsburgh, Pennsylvania. Use the supplied tools to assist the user."
            },
            #{
            #    "role": "system",
            #    "content": "Write concise, relevant responses, with the skilled style of a Pultizer Prize-winning author.  Do not use course search function, all others allowed."
            #}
        ]
        
        # Keep track of functions called
        self.functions_called = []
        
        # self.perplexity_search = CMUPerplexitySearch()
    
    def get_tools(self):
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "general_purpose_knowledge_search",
                    "description": "Search for general knowledge about Carnegie Mellon University.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "search_query": {
                                "type": "string",
                                "description": "The query to search for general knowledge."
                            }
                        },
                        "required": ["search_query"],
                        "additionalProperties": False
                    },
                    "strict": True  # Enabling Structured Outputs
                }
            }, {
                "type": "function",
                "function": {
                    "name": "create_calendar_event",
                    "description": "Make an event in the user's calendar when prompted",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "summary": {
                                "type": "string",
                                "description": "The name of the event to be created with default settings"
                            }
                        },
                        "required": ["name"],
                        "additionalProperties": False
                    },
                    "strict": False  # Enabling Structured Outputs
                }
            }
        ]
        return tools

    def process_user_input(self, user_input):
        self.messages.append({"role": "user", "content": user_input})
        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model='gpt-4o-mini',  # Fixed model name
                    messages=self.messages,
                    tools=self.tools,
                )

                assistant_message = response.choices[0].message
                
                if assistant_message.tool_calls:
                    # The model wants to call functions
                    tool_calls = assistant_message.tool_calls
                    function_results = []

                    for tool_call in tool_calls:
                        function_name = tool_call.function.name
                        arguments = json.loads(tool_call.function.arguments)
                        result = self.execute_function(function_name, arguments)

                        # Keep track of functions called
                        self.functions_called.append({
                            'function_name': function_name,
                            'arguments': arguments,
                            'result': result
                        })

                        # Prepare the function result message
                        function_result_message = {
                            "role": "tool",
                            "content": json.dumps(result),
                            "tool_call_id": tool_call.id
                        }

                        # Add the assistant's message (function call) and the function result to the conversation
                        self.messages.append({
                            "role": "assistant",
                            "tool_calls": [tool_call]
                        })
                        self.messages.append(function_result_message)

                    # After providing the function results, call the model again to get the final response
                    response = self.client.chat.completions.create(
                        model='gpt-4o-mini',
                        messages=self.messages,
                        #tools=self.tools,
                    )

                    

                    assistant_message = response.choices[0].message
                    self.messages.append(assistant_message)

                    return assistant_message.content
                else:
                    self.messages.append(assistant_message)
                    return assistant_message.content

            except APITimeoutError as e:
                if attempt == max_retries - 1:
                    return f"I apologize, but I'm having trouble connecting. Please try again in a moment. (Error: Connection timeout)"
                time.sleep(retry_delay)
                retry_delay *= 2
                
            except APIError as e:
                if attempt == max_retries - 1:
                    return f"I apologize, but there was an error processing your request. Please try again. (Error: {str(e)})"
                time.sleep(retry_delay)
                retry_delay *= 2
                
            except Exception as e:
                return f"I apologize, but an unexpected error occurred. Please try again. (Error: {str(e)})"

        return "I apologize, but I was unable to process your request after multiple attempts. Please try again later."
    def testers():
        return True
    # Function to execute the functions
    def execute_function(self, function_name, arguments):
        if function_name == 'general_purpose_knowledge_search':
            return self.general_purpose_knowledge_search(arguments.get('search_query'))
        #Add elif statements here
        elif function_name == 'create_calendar_event':
            return self.create_calendar_event(arguments.get('summary'))
        else:
            return {"error": "Function not found."}

    # Define the functions (simulate the functionality)
    # def general_purpose_knowledge_search(self, search_query):
    #     # Use Perplexity API for general knowledge searches
    #     return 0
        # return self.perplexity_search.search(search_query)

    # custom function for creating calendar
    def create_calendar_event(self, summary):
        location = "Tepper"
        description = "Eating icecream"

        start_date = "03/10/2025"
        end_date = "03/10/2025"
        start_time = "09:30"
        end_time = "10:35"

        start_object = datetime.strptime(f"{start_date} {start_time}", "%m/%d/%Y %H:%M")
        end_object = datetime.strptime(f"{end_date} {end_time}", "%m/%d/%Y %H:%M")
        user_timezone = get_localzone()
        # Localize datetime to user's timezone
        start_object = start_object.replace(tzinfo=user_timezone)
        end_object = end_object.replace(tzinfo=user_timezone)

        # Convert to ISO 8601 format
        start_iso = start_object.isoformat()
        end_iso = end_object.isoformat()

        event = {
        'summary': summary,
        'location': location,
        'description': description,
        'start': {
            'dateTime': start_iso,
        },
        'end': {
            'dateTime': end_iso,
        },
        }
        service = authenticate_google_calendar()

        try:
            # insert the event 
            event = service.events().insert(calendarId="primary", body=event).execute()
            print(f"Event added successfully!")

        except HttpError as error:
            print(f"An error occurred: {error}")
        return "Your event was added successfully! Let me know if you need anything else"
    
    def get_functions_called(self):
        return self.functions_called
             