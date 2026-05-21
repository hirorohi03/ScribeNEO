"""
Image Tagger for ScribeNEO.
Provides vision-based image scanning and tagging capabilities
using Ollama, OpenRouter, Hugging Face, and LM Studio backends with async requests.
"""
import httpx
import base64
import io
from PIL import Image
from modules import shared
from llm import llm

class ImageTagger:
    """
    Tagger class for analyzing image contents and generating tag descriptions.
    """
    def __init__(self):
        pass

    def encode_image(self, image):
        """
        Converts a PIL Image object to a base64-encoded PNG string.
        """
        if image is None:
            return None
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')

    async def scan_with_ollama(self, image, model="llava", system_prompt=None, timeout=None, max_tokens=None):
        """
        Scan image using local Ollama model asynchronously.
        """
        cfg = llm.get_config_data()
        endpoint = cfg['ollama_endpoint']
        url = f"{endpoint.rstrip('/')}/api/chat"
        
        b64_image = self.encode_image(image)
        if not b64_image:
            return "No image provided."

        keep_alive = cfg.get("ollama_keep_alive", 60)
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
        
        req_max_tokens = max_tokens if max_tokens is not None else cfg["max_tokens"]
        if req_max_tokens:
            data["options"] = {"num_predict": int(req_max_tokens)}

        req_timeout = timeout if timeout is not None else float(cfg["timeout"])

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=data, timeout=req_timeout)
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
        except httpx.HTTPStatusError as e:
            return f"Ollama HTTP Error ({e.response.status_code}): {e.response.text}"
        except httpx.TimeoutException:
            return "Ollama Error: Request timed out."
        except Exception as e:
            return f"Ollama Tagging Error: {str(e)}"

    async def scan_with_openrouter(self, image, model=None, system_prompt=None, timeout=None, max_tokens=None):
        """Scan image using OpenRouter hosted vision model asynchronously."""
        cfg = llm.get_config_data()
        target_model = model or "google/gemini-2.0-pro-exp-02-05:free"
        
        if not cfg["openrouter_key"]:
            return "Error: OpenRouter API Key not set."

        b64_image = self.encode_image(image)
        if not b64_image:
            return "No image provided."

        headers = {
            "Authorization": f"Bearer {cfg['openrouter_key']}",
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
        
        req_max_tokens = max_tokens if max_tokens is not None else cfg["max_tokens"]
        if req_max_tokens:
            data["max_tokens"] = int(req_max_tokens)
            
        endpoint = f"{cfg['openrouter_endpoint'].rstrip('/')}/chat/completions"
        req_timeout = timeout if timeout is not None else float(cfg["timeout"])

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(endpoint, headers=headers, json=data, timeout=req_timeout)
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
        except httpx.HTTPStatusError as e:
            return f"Vision API HTTP Error ({e.response.status_code}): {e.response.text}"
        except httpx.TimeoutException:
            return "Vision API Error: Request timed out."
        except Exception as e:
            print(f"[ScribeNEO] OpenRouter Vision Error: {str(e)}")
            return f"OpenRouter Tagging Error: {str(e)}"

    async def scan_with_huggingface(self, image, model=None, system_prompt=None, timeout=None, max_tokens=None):
        """Scan image using Hugging Face Inference API vision model asynchronously."""
        cfg = llm.get_config_data()
        target_model = model or "meta-llama/Llama-3.2-11B-Vision-Instruct"
        
        if not cfg["hf_token"]:
            return "Error: Hugging Face Token not set."

        b64_image = self.encode_image(image)
        if not b64_image:
            return "No image provided."

        headers = {
            "Authorization": f"Bearer {cfg['hf_token']}",
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
        
        req_max_tokens = max_tokens if max_tokens is not None else cfg["max_tokens"]
        if req_max_tokens:
            data["max_tokens"] = int(req_max_tokens)
            
        endpoint = f"{cfg['hf_endpoint'].rstrip('/')}/chat/completions"
        req_timeout = timeout if timeout is not None else float(cfg["timeout"])

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(endpoint, headers=headers, json=data, timeout=req_timeout)
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
        except httpx.HTTPStatusError as e:
            return f"HF Vision HTTP Error ({e.response.status_code}): {e.response.text}"
        except httpx.TimeoutException:
            return "HF Vision Error: Request timed out."
        except Exception as e:
            print(f"[ScribeNEO] HF Vision Error: {str(e)}")
            return f"Hugging Face Tagging Error: {str(e)}"

    async def scan_with_lmstudio(self, image, model=None, system_prompt=None, timeout=None, max_tokens=None):
        """Scan image using LM Studio hosted vision model asynchronously."""
        cfg = llm.get_config_data()
        if not model:
            return "Error: LM Studio requires a vision model selected."

        b64_image = self.encode_image(image)
        if not b64_image:
            return "No image provided."

        headers = {"Content-Type": "application/json"}
        if cfg["lmstudio_key"]:
            headers["Authorization"] = f"Bearer {cfg['lmstudio_key']}"
        
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
            "model": model,
            "messages": messages,
            "stream": False
        }
        
        req_max_tokens = max_tokens if max_tokens is not None else cfg["max_tokens"]
        if req_max_tokens:
            data["max_tokens"] = int(req_max_tokens)
            
        endpoint = f"{cfg['lmstudio_endpoint'].rstrip('/')}/chat/completions"
        req_timeout = timeout if timeout is not None else float(cfg["timeout"])

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(endpoint, headers=headers, json=data, timeout=req_timeout)
                if response.status_code == 400:
                    try:
                        err_msg = ""
                        try:
                            err_json = response.json()
                            err_val = err_json.get('error', '')
                            if isinstance(err_val, dict):
                                err_msg = err_val.get('message', '')
                            else:
                                err_msg = str(err_val)
                        except Exception:
                            pass
                        
                        if 'vision' in err_msg.lower() or 'image' in err_msg.lower() or 'multimodal' in err_msg.lower():
                            return f"LM Studio Error: The model '{model}' does not support image input. Please select a vision-capable model."
                        elif "role" in err_msg.lower() or "jinja" in err_msg.lower():
                            if system_prompt:
                                fallback_content = f"System Instructions:\n{system_prompt}\n\nUser Input:\n{user_prompt}"
                                fallback_messages = [{
                                    "role": "user",
                                    "content": [
                                        {"type": "text", "text": fallback_content},
                                        {
                                            "type": "image_url",
                                            "image_url": {
                                                "url": f"data:image/png;base64,{b64_image}"
                                            }
                                        }
                                    ]
                                }]
                                fallback_data = {
                                    "model": model,
                                    "messages": fallback_messages,
                                    "stream": False
                                }
                                if req_max_tokens:
                                    fallback_data["max_tokens"] = int(req_max_tokens)
                                response = await client.post(endpoint, headers=headers, json=fallback_data, timeout=req_timeout)
                    except Exception as fallback_err:
                        print(f"[ScribeNEO] LM Studio vision role fallback failed: {fallback_err}")
                if response.status_code != 200:
                    print(f"[ScribeNEO] LM Studio Vision API Error: {response.text}")
                response.raise_for_status()
                result = response.json()
                return result['choices'][0]['message']['content']
        except httpx.HTTPStatusError as e:
            return f"LM Studio Vision HTTP Error ({e.response.status_code}): {e.response.text}"
        except httpx.TimeoutException:
            return "LM Studio Vision Error: Request timed out."
        except Exception as e:
            print(f"[ScribeNEO] LM Studio Critical Vision Error: {str(e)}")
            return f"LM Studio Tagging Error: {str(e)}"

    async def scan_image(self, image, provider="openrouter", model=None, system_prompt=None, timeout=None, max_tokens=None):
        """Route image scanning request to the designated provider asynchronously."""
        provider_key = provider.lower().replace(" ", "")
        if provider_key == "openrouter":
            return await self.scan_with_openrouter(image, model, system_prompt, timeout=timeout, max_tokens=max_tokens)
        elif provider_key == "ollama":
            return await self.scan_with_ollama(image, model, system_prompt, timeout=timeout, max_tokens=max_tokens)
        elif provider_key == "huggingface":
            return await self.scan_with_huggingface(image, model, system_prompt, timeout=timeout, max_tokens=max_tokens)
        elif provider_key == "lmstudio":
            return await self.scan_with_lmstudio(image, model, system_prompt, timeout=timeout, max_tokens=max_tokens)
        
        return f"Error: Unknown vision provider '{provider}'"

tagger = ImageTagger()
