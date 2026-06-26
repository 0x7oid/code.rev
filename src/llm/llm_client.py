from google import genai
import os

client = genai.Client(api_key=os.environ.get("API_KEY"))


def ask_llm(prompt , model="gemini-3.5-flash"):
    response = client.models.generate_content(
        model=model , contents = prompt
    )
    return response.text

