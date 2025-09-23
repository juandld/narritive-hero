import os
import json
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from base64 import b64encode

# Load environment variables from .env file
load_dotenv()

# Configure the API key
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY not found. Please set it in the .env file.")

# Initialize the LangChain model
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", api_key=api_key)

# Load scenario data
scenarios_path = os.path.join(os.path.dirname(__file__), 'scenarios.json')
with open(scenarios_path, 'r') as f:
    scenarios_data = json.load(f)

def get_scenario_by_id(scenario_id):
    """Finds a scenario in the loaded data by its ID."""
    for scenario in scenarios_data:
        if scenario["id"] == scenario_id:
            return scenario
    return None

def process_interaction(audio_file, current_scenario_id_str):
    """
    Processes the user's audio interaction to determine the next scenario.
    """
    try:
        current_scenario_id = int(current_scenario_id_str)
        
        # 1. Transcribe Audio to Text using LangChain
        audio_bytes = audio_file.read()
        
        # Create a multimodal message with a text prompt and the audio data
        # Correctly specifying the mime_type for the audio data.
        message = HumanMessage(
            content=[
                {"type": "text", "text": "Transcribe this audio recording."},
                {
                    "type": "image_url", 
                    "image_url": {
                        "url": f"data:audio/webm;base64,{b64encode(audio_bytes).decode()}"
                    }
                }
            ]
        )
        
        # Invoke the model
        response = llm.invoke([message])
        transcribed_text = response.content.lower()

        # 2. Recognize Intent (Simplified MVP Logic)
        current_scenario = get_scenario_by_id(current_scenario_id)
        if not current_scenario:
            return {"error": "Scenario not found"}

        next_scenario_id = None
        # Simple keyword matching for the MVP
        if "yes" in transcribed_text or "yeah" in transcribed_text or "i am" in transcribed_text:
            for option in current_scenario["options"]:
                if "yes" in option["text"].lower():
                    next_scenario_id = option["next_scenario"]
                    break
        elif "no" in transcribed_text or "not" in transcribed_text:
            for option in current_scenario["options"]:
                if "no" in option["text"].lower():
                    next_scenario_id = option["next_scenario"]
                    break
        
        if not next_scenario_id:
            return {"error": f"Could not determine intent from speech. (Heard: '{transcribed_text}')"}

        # 3. Determine Next Scenario
        next_scenario = get_scenario_by_id(next_scenario_id)
        if not next_scenario:
            return {"error": "Next scenario not found"}
            
        return {"nextScenario": next_scenario}

    except Exception as e:
        return {"error": str(e)}
