from openai import OpenAI
import os
from typing import List, Dict, Optional

class LLMService:
    def __init__(self, api_key: Optional[str] = None, model: str = "x-ai/grok-4.1-fast"):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY") or "dummy"
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
        )
        self.model = model

    def set_api_key(self, api_key: str):
        self.api_key = api_key
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
        )

    def set_model(self, model: str):
        self.model = model

    def generate_response(self, system_prompt: str, user_input: str, context: str = "") -> str:
        if not self.api_key or self.api_key == "dummy":
            return "Error: API Key not set."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nUser: {user_input}"}
        ]

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"Error calling LLM: {str(e)}"

    def generate_response_stream(self, system_prompt: str, user_input: str, context: str = ""):
        if not self.api_key or self.api_key == "dummy":
            yield "Error: API Key not set."
            return

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nUser: {user_input}"}
        ]
        
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            yield f"Error calling LLM: {str(e)}"

    def generate_summary(self, memories: str) -> str:
        if not self.api_key:
            return "Error: API Key not set."
            
        prompt = f"Summarize the following events into a concise memory update:\n{memories}"
        
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"Error summarizing: {str(e)}"

if __name__=="__main__":
    llm_service = LLMService()
    response = llm_service.generate_response(
        system_prompt="You are a helpful assistant.",
        user_input="Hello, how are you?",
        context="Some relevant context."
    )
    print("Response:", response)