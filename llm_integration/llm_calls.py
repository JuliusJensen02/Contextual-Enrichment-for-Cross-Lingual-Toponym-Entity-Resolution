import os
import requests
from dotenv import load_dotenv
from openai import OpenAI
from anthropic import Anthropic

load_dotenv()


class LLMClient:
    def __init__(self, prompt: str, instructions: str):
        self.timeout = 30
        self.prompt = prompt
        self.instructions = instructions

    def call_llama(self, model: str = os.getenv("LLAMA_MODEL"), url: str = os.getenv("LLAMA_API_URL"), token: str = os.getenv("LLAMA_API_TOKEN")):
        payload = {
            "model": model
        }
        messages = []
        messages.append({"role": "system", "content": self.instructions})
        messages.append({"role": "user", "content": self.prompt})
        payload["messages"] = messages
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                url,
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

    def call_openai(self, model: str = os.getenv("OPENAI_MODEL"), token: str = os.getenv("OPENAI_API_TOKEN")):
        client = OpenAI(api_key=token, timeout=self.timeout)

        response = client.responses.create(model=model, input=self.prompt, instructions=self.instructions)

        return response

    def call_anthropic(self, model: str = os.getenv("CLAUDE_MODEL"), token: str = os.getenv("CLAUDE_API_TOKEN"),
                    workspace_id: str = os.getenv("CLAUDE_WORKSPACE_ID")):
        client = Anthropic(
            api_key=token,
            timeout=self.timeout,
            default_headers={"anthropic-workspace-id": workspace_id} if workspace_id else None,
        )

        # Anthropic does not accept a "system" role in messages; it is a separate parameter.
        message = client.messages.create(
            max_tokens=1024,
            system=self.instructions,
            messages=[
                {
                    "content": self.prompt,
                    "role": "user",
                },
            ],
            model=model,
        )
        return message




if __name__ == "__main__":
    client = LLMClient("Hello!", "Return ONLY strictly JSON (No markdown, no extra text)")
    print("Anthropic")
    print(client.call_anthropic())
    # print("\nOpenAI")
    # print(client.call_openai())
    # print("\nLlama")
    # print(client.call_llama())