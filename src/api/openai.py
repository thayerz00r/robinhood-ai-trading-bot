from openai import OpenAI
import re
import json
from config import OPENAI_API_KEY, OPENAI_MODEL_NAME


# Initialize OpenAI client -- modified for AbacusRouteLLM / OpenAI compatible
client = OpenAI(
    base_url="https://routellm.abacus.ai/v1",
    api_key=OPENAI_API_KEY
    )


# Make AI request to OpenAI API
def make_ai_request(prompt):
    ai_resp = client.chat.completions.create(
        model=OPENAI_MODEL_NAME,
        messages=[{"role": "user", "content": prompt}]
    )
    return ai_resp


# Parse AI response
def parse_ai_response(ai_response):
    try:
        ai_content = re.sub(r'```json|```', '', ai_response.choices[0].message.content.strip())
        decisions = json.loads(ai_content)
    except json.JSONDecodeError:
        raise Exception("Invalid JSON response from OpenAI: " + ai_response.choices[0].message.content.strip())
    return decisions
