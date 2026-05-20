"""
Tagging Service for ScribeNEO.
Provides vision-based image interrogation and tagging capabilities
using Ollama and OpenRouter backends.
"""
import requests
import base64
import io
from PIL import Image
from modules import shared

from llm_service import llm_service

class TaggingService:
    """
    Service for analyzing image content and generating descriptive tags.
    """
    def __init__(self):
        self.timeout = 60.0 # Vision tasks can take longer

    def encode_image(self, image):
        """
        Converts a PIL Image object to a base64-encoded PNG string.
        
        Args:
            image (PIL.Image): The image to encode.
            
        Returns:
            str: Base64 string or None.
        """
        if image is None:
            return None
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')

    def interrogate_ollama(self, image, model="llava", system_prompt=None):
        """
        Performs image interrogation using a local Ollama instance.
        
        Args:
            image (PIL.Image): Source image.
            model (str): The vision model to use (e.g., 'llava').
            system_prompt (str, optional): Custom persona/instructions.
            
        Returns:
            str: Image description or error message.
        """
        config = llm_service.get_config()
        endpoint = config['ollama_endpoint']
        url = f"{endpoint.rstrip('/')}/api/chat"
        
        b64_image = self.encode_image(image)
        if not b64_image:
            return "No image provided."

        keep_alive = config.get("ollama_keep_alive", 60)
        try:
            if isinstance(keep_alive, str) and keep_alive.strip().isdigit():
                keep_alive = int(keep_alive.strip())
            elif isinstance(keep_alive, str):
                keep_alive = keep_alive.strip()
        except Exception:
            pass

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        user_prompt = "Describe this image." if system_prompt else "Describe this image in detail for a Stable Diffusion prompt. focus on subjects, lighting, and style."
        messages.append({
            "role": "user",
            "content": user_prompt,
            "images": [b64_image]
        })

        data = {
            "model": model,
            "messages": messages,
            "stream": False,
            "keep_alive": keep_alive
        }

        try:
            response = requests.post(url, json=data, timeout=self.timeout)
            if response.status_code == 400:
                try:
                    err_json = response.json()
                    err_msg = err_json.get('error', '')
                    if 'multimodal' in err_msg.lower() or 'vision' in err_msg.lower() or 'image' in err_msg.lower():
                        return f"Ollama Error: The model '{model}' does not support vision (multimodal input). Please select a vision-capable model (e.g. llava, moondream, qwen2.5-vl)."
                except Exception:
                    pass
            response.raise_for_status()
            result = response.json()
            return result.get('message', {}).get('content', 'No description generated.')
        except requests.exceptions.HTTPError as e:
            return f"Ollama HTTP Error ({e.response.status_code}): {e.response.text}"
        except requests.exceptions.Timeout:
            return "Ollama Error: Request timed out."
        except Exception as e:
            return f"Ollama Tagging Error: {str(e)}"

    def interrogate_openrouter(self, image, model=None, system_prompt=None):
        """
        Interrogates an image using an OpenRouter-hosted vision model.
        
        Args:
            image (PIL.Image): Source image.
            model (str, optional): Target vision model.
            system_prompt (str, optional): Custom persona/instructions.
            
        Returns:
            str: AI output or error message.
        """
        config = llm_service.get_config()
        # Default vision model if none provided
        target_model = model or "google/gemini-2.0-pro-exp-02-05:free"
        
        if not config["openrouter_key"]:
            return "Error: OpenRouter API Key not set."

        b64_image = self.encode_image(image)
        if not b64_image:
            return "No image provided."

        headers = {
            "Authorization": f"Bearer {config['openrouter_key']}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
            
        user_prompt = "Describe this image." if system_prompt else "Describe this image for a Stable Diffusion prompt. Output only the prompt tags and description."
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": user_prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{b64_image}"
                    }
                }
            ]
        })

        data = {
            "model": target_model,
            "messages": messages
        }

        endpoint = f"{config['openrouter_endpoint'].rstrip('/')}/chat/completions"

        try:
            response = requests.post(endpoint, headers=headers, json=data, timeout=self.timeout)
            if response.status_code == 400:
                try:
                    err_json = response.json()
                    err_msg = err_json.get('error', {}).get('message', '')
                    if 'vision' in err_msg.lower() or 'image' in err_msg.lower() or 'multimodal' in err_msg.lower():
                        return f"OpenRouter Error: The model '{model}' does not support image input. Please select a vision-capable model."
                except Exception:
                    pass
            if response.status_code != 200:
                print(f"[ScribeNEO] Vision API Error: {response.text}")
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except requests.exceptions.HTTPError as e:
            return f"Vision API HTTP Error ({e.response.status_code}): {e.response.text}"
        except requests.exceptions.Timeout:
            return "Vision API Error: Request timed out."
        except Exception as e:
            print(f"[ScribeNEO] Critical Vision Error: {str(e)}")
            return f"OpenRouter Tagging Error: {str(e)}"

    def interrogate_huggingface(self, image, model=None, system_prompt=None):
        """
        Interrogates an image using the Hugging Face Inference API (Router).
        Compatible with OpenAI VLM message format.
        """
        config = llm_service.get_config()
        # Default vision-capable model for HF if none provided
        target_model = model or "meta-llama/Llama-3.2-11B-Vision-Instruct"
        
        if not config["hf_token"]:
            return "Error: Hugging Face Token not set."

        b64_image = self.encode_image(image)
        if not b64_image:
            return "No image provided."

        headers = {
            "Authorization": f"Bearer {config['hf_token']}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
            
        user_prompt = "Describe this image." if system_prompt else "Describe this image for a Stable Diffusion prompt. Output only the prompt tags and description."
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": user_prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{b64_image}"
                    }
                }
            ]
        })

        data = {
            "model": target_model,
            "messages": messages,
            "stream": False
        }

        # Uses the router endpoint defined in config
        endpoint = f"{config['hf_endpoint'].rstrip('/')}/chat/completions"

        try:
            response = requests.post(endpoint, headers=headers, json=data, timeout=self.timeout)
            if response.status_code == 400:
                try:
                    err_json = response.json()
                    err_msg = err_json.get('error', '')
                    if 'vision' in err_msg.lower() or 'image' in err_msg.lower() or 'multimodal' in err_msg.lower():
                        return f"Hugging Face Error: The model '{model}' does not support image input. Please select a vision-capable model."
                except Exception:
                    pass
            if response.status_code != 200:
                print(f"[ScribeNEO] HF Vision API Error: {response.text}")
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except requests.exceptions.HTTPError as e:
            return f"HF Vision HTTP Error ({e.response.status_code}): {e.response.text}"
        except requests.exceptions.Timeout:
            return "HF Vision Error: Request timed out."
        except Exception as e:
            print(f"[ScribeNEO] HF Critical Vision Error: {str(e)}")
            return f"Hugging Face Tagging Error: {str(e)}"

    def interrogate(self, image, provider="openrouter", model=None, system_prompt=None):
        """
        Routes the interrogation request to the specified provider.
        """
        if provider == "openrouter":
            return self.interrogate_openrouter(image, model, system_prompt)
        elif provider == "ollama":
            return self.interrogate_ollama(image, model, system_prompt)
        elif provider == "huggingface":
            return self.interrogate_huggingface(image, model, system_prompt)
        
        return f"Error: Unknown vision provider '{provider}'"

tagging_service = TaggingService()
