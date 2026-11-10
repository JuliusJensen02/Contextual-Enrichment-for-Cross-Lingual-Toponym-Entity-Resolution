import os
import requests
from dotenv import load_dotenv

load_dotenv()


class LLMClient:
    """Simple client for calling local LLM server."""

    def __init__(self, env_model_ref: str, env_url_ref : str, env_api_ref: str, endpoint_path: str):
        self.api_url = os.getenv(env_url_ref)
        self.api_token = os.getenv(env_api_ref)
        self.model = os.getenv(env_model_ref)
        self.timeout = 30
        self.endpoint = endpoint_path


    def call(self, prompt: str, instructions: str = None) -> str:

        payload = {
            "model": self.model
        }

        if self.endpoint.__contains__("responses"):
            payload["input"] = prompt
            if instructions:
                payload["instructions"] = instructions
        else:
            messages = []
            if instructions:
                messages.append({"role": "system", "content": instructions})
            messages.append({"role": "user", "content": prompt})
            payload["messages"] = messages


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
            return response.json()
        
        except requests.exceptions.RequestException as e:
            if e.response is not None:
                print(f"Response: {e.response.status_code}")
                print(f"Body: {e.response.text}")

            raise RuntimeError(f"API call failed: {e}") from e

    def call_batch(self, prompts: list[str]) -> list[str]:
        """Call the LLM multiple times."""
        return [self.call(prompt) for prompt in prompts]



if __name__ == "__main__":
    llama_client = LLMClient("LLAMA_MODEL", "LLAMA_API_URL", "LLAMA_API_TOKEN", "chat/completions")
    openai_client = LLMClient("OPENAI_MODEL", "OPENAI_API_URL", "OPENAI_API_TOKEN", "responses")
    print("LLAMA")
    print(llama_client.call("Hello!"))
    print("\n")
    print("OPEN AI")
    print(openai_client.call("Hello!"))