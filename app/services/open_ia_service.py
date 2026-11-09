import os

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def call_ai(
    model: str, max_tokens: int, reasoning: dict, messages: list,
    timeout: int, temperature: float = 0.1, response_format: str = "text"
    ) -> str:
    """ Funcion que ejecuta el cliente"""
    response = client.chat.completions.create(
        model=model,
        max_completion_tokens=max_tokens,
        reasoning_effort=reasoning,
        messages=messages,
        temperature=temperature,
        response_format={"type": response_format},
        timeout=timeout
    )

    return response.choices[0].message.content