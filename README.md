**First Step**
Create a .env file

In the .env file add the 
OPENAI_API_KEY (OpenAI API Key provided in the Slack)

and PERPLEXITY_API_KEY [Add your own]

Format is OPENAI_API_KEY = "add_key_here"

**RUN:**
pip install -r requirements.txt

**RUN (to launch the interface)**
streamlit run app.py


**How To Add Your Function to the Framework**

In cmugpt_assistant.py there are three tasks.

1. Import your function
2. Add your function description to the def get_tools(self): function.
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
            },
        ]
        return tools

  3. Make your function executable by our system
   # Function to execute the functions
      def execute_function(self, function_name, arguments):
          if function_name == 'general_purpose_knowledge_search':
              return self.general_purpose_knowledge_search(arguments.get('search_query'))
          #Add elif statements here
          else:
              return {"error": "Function not found."}
  
      # Define the functions (simulate the functionality)
      def general_purpose_knowledge_search(self, search_query):
          # Use Perplexity API for general knowledge searches
          return self.perplexity_search.search(search_query)
  
      def get_functions_called(self):
          return self.functions_called

        1. **Add elif statements to check if function_name == 'add_your_function_name'**

        2. Def a new helper function that calls your function if following with previous format/approach
