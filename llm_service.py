"""
LLM Service for ScribeNEO.
Orchestrates communication with various AI backends (OpenRouter, Hugging Face, Ollama)
to perform prompt enhancement and model synchronization.
"""
import requests
import json
import os
import config_service
from config_service import load_config

DEFAULT_TEXT_MODEL = "google/gemini-2.0-flash-lite-preview-02-05:free"

class LLMService:
    """
    Core service class for managing LLM interactions and configurations.
    """
    def __init__(self):
        self.timeout = 30.0

    def get_config(self):
        """Bridge to centralized local config."""
        conf = load_config()
        
        return {
            "openrouter_key": conf["openrouter"]["key"],
            "openrouter_endpoint": conf["openrouter"]["endpoint"],
            "hf_token": conf["huggingface"]["key"],
            "hf_endpoint": conf["huggingface"]["endpoint"],
            "ollama_endpoint": conf["ollama"]["endpoint"],
            "ollama_keep_alive": conf["ollama"].get("keep_alive", 60)
        }

    def call_openrouter(self, messages, model=None):
        """
        Sends a chat completion request to OpenRouter.
        
        Args:
            messages (list): Chat history/messages in OpenAI format.
            model (str, optional): Overrides the default model.
            
        Returns:
            str: The AI's response content or an error message.
        """
        config = self.get_config()
        target_model = model or DEFAULT_TEXT_MODEL
        
        if not config["openrouter_key"]:
            return "Error: OpenRouter API Key not set."

        headers = {
            "Authorization": f"Bearer {config['openrouter_key']}",
            "HTTP-Referer": "https://github.com/SiliconeShojo/ScribeNEO",
            "X-Title": "ScribeNEO",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": target_model,
            "messages": messages
        }

        endpoint = f"{config['openrouter_endpoint'].rstrip('/')}/chat/completions"

        try:
            response = requests.post(endpoint, headers=headers, json=data, timeout=self.timeout)
            if response.status_code != 200:
                print(f"[ScribeNEO] API Error: {response.text}")
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except requests.exceptions.HTTPError as e:
            return f"OpenRouter HTTP Error ({e.response.status_code}): {e.response.text}"
        except requests.exceptions.Timeout:
            return "OpenRouter Error: Request timed out."
        except Exception as e:
            print(f"[ScribeNEO] Critical Error: {str(e)}")
            return f"OpenRouter Error: {str(e)}"

    def fetch_available_models(self, provider=None, api_key=None, endpoint_url=None, is_vision=False):
        """
        Universally fetches available models from the specified or configured provider.
        Filters for vision-support if requested.
        
        Args:
            provider (str, optional): Provider name to sync from.
            api_key (str, optional): Temporary key to use for testing.
            endpoint_url (str, optional): Temporary endpoint to use for testing.
            is_vision (bool): Whether to filter for vision-capable models.
            
        Returns:
            list: Sorted list of model identifiers.
        """
        config = self.get_config()
        provider = provider or config["provider"]
        
        if provider == "OpenRouter":
            key = api_key or config["openrouter_key"]
            if not key: return []
            try:
                endpoint = endpoint_url or config["openrouter_endpoint"]
                response = requests.get(f"{endpoint.rstrip('/')}/models", timeout=10.0)
                response.raise_for_status()
                data = response.json()
                models = data.get('data', [])
                
                if is_vision:
                    # Filter for models that likely support vision
                    vision_keywords = ['vision', 'gemini', 'gpt-4o', 'claude-3', 'vlk', 'pixtral', 'vl', 'lava', 'multimodal', 'llava']
                    models = [m for m in models if any(k in m['id'].lower() for k in vision_keywords)]
                
                return sorted([m['id'] for m in models])
            except Exception as e:
                print(f"[ScribeNEO] OpenRouter Sync Error: {e}")
                return []
                
        elif provider == "Hugging Face":
            token = api_key or config["hf_token"]
            try:
                endpoint = endpoint_url or config["hf_endpoint"]
                headers = {"Authorization": f"Bearer {token}"} if token else {}
                url = f"{endpoint.rstrip('/')}/models"
                response = requests.get(url, headers=headers, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                models = data.get('data', [])
                
                if is_vision:
                    # Extract IDs and filter
                    vision_keywords = ['vision', 'llava', 'vlk', 'pixtral', 'paligemma', 'idefics', 'molmo', 'qwen-vl', 'vl', 'lava', 'multimodal']
                    return sorted([m['id'] for m in models if any(k in m['id'].lower() for k in vision_keywords)])
                
                return sorted([m['id'] for m in models])
            except Exception as e:
                print(f"[ScribeNEO] HF Router Sync Error: {e}")
                return []
                
        elif provider == "Ollama":
            url = endpoint_url or config["ollama_endpoint"]
            try:
                response = requests.get(f"{url.rstrip('/')}/api/tags", timeout=5.0)
                response.raise_for_status()
                data = response.json()
                models = [m['name'] for m in data.get('models', [])]
                
                if is_vision:
                    vision_models = ['llava', 'moondream', 'bakllava', 'qwen', 'gemma', 'vl', 'vision', 'minicpm', 'paligemma']
                    return sorted([m for m in models if any(v in m.lower() for v in vision_models)])
                
                return sorted(models)
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                return []
            except Exception as e:
                print(f"[ScribeNEO] Ollama Sync Error: {e}")
                return []
        
        return []

    def test_connection(self, provider, api_key, endpoint_url=None):
        """
        Validates the provided credentials and endpoint for a specific AI service.
        
        Returns:
            tuple: (success_bool, message_str)
        """
        try:
            if provider == "OpenRouter":
                headers = {"Authorization": f"Bearer {api_key}"}
                endpoint = endpoint_url or "https://openrouter.ai/api/v1"
                r = requests.get(f"{endpoint.rstrip('/')}/key", headers=headers, timeout=10.0)
                if r.status_code == 200:
                    data = r.json().get('data', {})
                    label = data.get('label', 'Authenticated')
                    return True, f"Connected to OpenRouter as '{label}'"
                return False, f"OpenRouter Auth Error: {r.status_code}"
            
            elif provider == "Hugging Face":
                headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
                r = requests.get("https://huggingface.co/api/whoami-v2", headers=headers, timeout=10.0)
                if r.status_code == 200:
                    data = r.json()
                    return True, f"Connected to Hugging Face as {data.get('name', 'Anonymous')}"
                return False, f"HF Error: {r.text}"
            
            elif provider == "Ollama":
                url = endpoint_url or "http://localhost:11434"
                r = requests.get(f"{url.rstrip('/')}/api/tags", timeout=5.0)
                if r.status_code == 200:
                    return True, "Successfully connected to Ollama server."
                return False, f"Ollama unreachable: Status {r.status_code}"
                    
        except requests.exceptions.Timeout:
            return False, "Connection Timeout: Server took too long to respond."
        except requests.exceptions.ConnectionError:
            return False, "Connection Error: Could not reach the server."
        except Exception as e:
            return False, f"Connection Failed: {str(e)}"
        
        return False, "Unknown provider."

    def call_ollama(self, messages, model="llama3"):
        """
        Communicates with a local or remote Ollama server using the native API.
        """
        config = self.get_config()
        url = f"{config['ollama_endpoint'].rstrip('/')}/api/chat"
        
        keep_alive = config.get("ollama_keep_alive", 60)
        try:
            if isinstance(keep_alive, str) and keep_alive.strip().isdigit():
                keep_alive = int(keep_alive.strip())
            elif isinstance(keep_alive, str):
                keep_alive = keep_alive.strip()
        except Exception:
            pass

        data = {
            "model": model,
            "messages": messages,
            "stream": False,
            "keep_alive": keep_alive
        }

        try:
            response = requests.post(url, json=data, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            return result['message']['content']
        except requests.exceptions.HTTPError as e:
            return f"Ollama HTTP Error ({e.response.status_code}): {e.response.text}"
        except requests.exceptions.Timeout:
            return "Ollama Error: Request timed out."
        except Exception as e:
            return f"Ollama Error: {str(e)}"

    def unload_ollama_model(self, model):
        """
        Unloads the specified Ollama model from memory by sending a request with keep_alive: 0.
        """
        config = self.get_config()
        url = f"{config['ollama_endpoint'].rstrip('/')}/api/generate"
        data = {
            "model": model,
            "keep_alive": 0,
            "stream": False
        }
        try:
            response = requests.post(url, json=data, timeout=5.0)
            response.raise_for_status()
            return True, f"Successfully unloaded Ollama model '{model}'."
        except Exception as e:
            return False, f"Failed to unload Ollama model: {str(e)}"

    def call_hf(self, messages, model="mistralai/Mistral-7B-Instruct-v0.2"):
        """
        Sends requests to the Hugging Face Inference API / Router.
        """
        config = self.get_config()
        if not config["hf_token"]:
            return "Error: Hugging Face Token not set in Settings."

        headers = {
            "Authorization": f"Bearer {config['hf_token']}",
            "Content-Type": "application/json"
        }
        
        # Use OpenAI-compatible endpoint
        endpoint = f"{config['hf_endpoint'].rstrip('/')}/chat/completions"

        data = {
            "model": model,
            "messages": messages,
            "stream": False
        }

        try:
            response = requests.post(endpoint, headers=headers, json=data, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except requests.exceptions.HTTPError as e:
            return f"Hugging Face HTTP Error ({e.response.status_code}): {e.response.text}"
        except requests.exceptions.Timeout:
            return "Hugging Face Error: Request timed out."
        except Exception as e:
            return f"Hugging Face Router Error: {str(e)}"

    def enhance_prompt(self, user_prompt, persona_system_prompt, provider="openrouter", model=None):
        """
        Main entry point for ScribeNEO logic. Prepares the final message payload
        and routes it to the correct provider based on configuration.
        """
        messages = []
        user_msg = f"Enhance this prompt for Stable Diffusion: {user_prompt}"
        
        if persona_system_prompt:
            # Handle template placeholders if present
            if "{input}" in persona_system_prompt:
                persona_system_prompt = persona_system_prompt.replace("{input}", user_prompt)
                user_msg = "Process the request as instructed in the system prompt."
                
            messages.append({"role": "system", "content": persona_system_prompt})
            
        messages.append({"role": "user", "content": user_msg})

        if provider == "openrouter":
            return self.call_openrouter(messages, model)
        elif provider == "ollama":
            return self.call_ollama(messages, model or "llama3")
        elif provider == "huggingface":
            return self.call_hf(messages, model or "mistralai/Mistral-7B-Instruct-v0.2")
        
        return "Error: Unknown provider."

llm_service = LLMService()
