"""
Simple LLM API integration for local LLM server.

Example usage:
    client = LLMClient()
    response = client.call("What is this place?")
    print(response)
"""

import os
import requests
from dotenv import load_dotenv
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()


class LLMClient:
    """Simple client for calling local LLM server."""

    def __init__(self, env_model_ref: str, env_url_ref : str, env_api_ref: str):
        self.api_url = os.getenv(env_url_ref)
        self.api_token = os.getenv(env_api_ref)
        self.model = os.getenv(env_model_ref)
        self.timeout = 30


    def call(self, prompt: str, system_prompt: str = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
        }

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=self.timeout,
                verify=False
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as e:
            try:
                print(f"Response: {response.status_code}")
                print(f"Body: {response.text}")
            except:
                pass
            raise RuntimeError(f"API call failed: {e}")

    def call_batch(self, prompts: list[str]) -> list[str]:
        """Call the LLM multiple times."""
        return [self.call(prompt) for prompt in prompts]



if __name__ == "__main__":
    client = LLMClient("LLAMA_LLM_model", "LLAMA_LLM_API_URL", "LLAMA_LLM_API_TOKEN")
    print(client.call("Hello!"))



