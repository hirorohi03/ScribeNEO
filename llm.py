"""
LLM Manager for ScribeNEO.
Manages communication with AI providers (OpenRouter, Hugging Face, Ollama, LM Studio)
for prompt enhancement and model synchronization using async I/O.
"""
import httpx
import json
import os
import settings
from settings import load_config

DEFAULT_TEXT_MODEL = "google/gemini-2.0-flash-lite-preview-02-05:free"

class LLMManager:
    """
    Manager class for coordinating LLM requests and operations.
    """
    def __init__(self):
        pass

    def get_config_data(self):
        """Load and return configuration parameters."""
        conf = load_config()
        return {
            "timeout": conf.get("timeout", 30),
            "max_tokens": conf.get("max_tokens", 512),
            "openrouter_key": conf["openrouter"]["key"],
            "openrouter_endpoint": conf["openrouter"]["endpoint"],
            "hf_token": conf["huggingface"]["key"],
            "hf_endpoint": conf["huggingface"]["endpoint"],
            "ollama_endpoint": conf["ollama"]["endpoint"],
            "ollama_keep_alive": conf["ollama"].get("keep_alive", 60),
            "lmstudio_endpoint": conf["lmstudio"]["endpoint"],
            "lmstudio_key": conf["lmstudio"].get("key", "")
        }

    async def query_openrouter(self, messages, model=None, timeout=None, max_tokens=None):
        """
        Send a chat completion request to OpenRouter asynchronously.
        """
        cfg = self.get_config_data()
        target_model = model or DEFAULT_TEXT_MODEL
        
        if not cfg["openrouter_key"]:
            return "Error: OpenRouter API Key not set."

        headers = {
            "Authorization": f"Bearer {cfg['openrouter_key']}",
            "HTTP-Referer": "https://github.com/SiliconeShojo/ScribeNEO",
            "X-Title": "ScribeNEO",
            "Content-Type": "application/json"
        }
        
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
                if response.status_code != 200:
                    print(f"[ScribeNEO] OpenRouter API Error: {response.text}")
                response.raise_for_status()
                result = response.json()
                return result['choices'][0]['message']['content']
        except httpx.HTTPStatusError as e:
            return f"OpenRouter HTTP Error ({e.response.status_code}): {e.response.text}"
        except httpx.TimeoutException:
            return "OpenRouter Error: Request timed out."
        except Exception as e:
            print(f"[ScribeNEO] OpenRouter Error: {str(e)}")
            return f"OpenRouter Error: {str(e)}"

    async def fetch_models(self, provider=None, api_key=None, endpoint_url=None, is_vision=False):
        """
        Fetch available models from the specified provider asynchronously.
        """
        cfg = self.get_config_data()
        provider = provider or cfg.get("provider", "OpenRouter")
        req_timeout = float(cfg["timeout"])
        
        if provider == "OpenRouter":
            key = api_key or cfg["openrouter_key"]
            if not key:
                return []
            try:
                endpoint = endpoint_url or cfg["openrouter_endpoint"]
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{endpoint.rstrip('/')}/models", timeout=min(req_timeout, 10.0))
                    response.raise_for_status()
                    data = response.json()
                models = data.get('data', [])
                
                if is_vision:
                    vision_keywords = ['vision', 'gemini', 'gpt-4o', 'claude-3', 'vlk', 'pixtral', 'vl', 'lava', 'multimodal', 'llava']
                    models = [m for m in models if any(k in m['id'].lower() for k in vision_keywords)]
                
                return sorted([m['id'] for m in models])
            except Exception as e:
                print(f"[ScribeNEO] OpenRouter Sync Error: {e}")
                return []
                
        elif provider == "Hugging Face":
            token = api_key or cfg["hf_token"]
            try:
                endpoint = endpoint_url or cfg["hf_endpoint"]
                headers = {"Authorization": f"Bearer {token}"} if token else {}
                url = f"{endpoint.rstrip('/')}/models"
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, headers=headers, timeout=min(req_timeout, 10.0))
                    response.raise_for_status()
                    data = response.json()
                models = data.get('data', [])
                
                if is_vision:
                    vision_keywords = ['vision', 'llava', 'vlk', 'pixtral', 'paligemma', 'idefics', 'molmo', 'qwen-vl', 'vl', 'lava', 'multimodal']
                    return sorted([m['id'] for m in models if any(k in m['id'].lower() for k in vision_keywords)])
                
                return sorted([m['id'] for m in models])
            except Exception as e:
                print(f"[ScribeNEO] HF Router Sync Error: {e}")
                return []
                
        elif provider == "Ollama":
            url = endpoint_url or cfg["ollama_endpoint"]
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{url.rstrip('/')}/api/tags", timeout=min(req_timeout, 5.0))
                    response.raise_for_status()
                    data = response.json()
                models = [m['name'] for m in data.get('models', [])]
                
                if is_vision:
                    vision_models = ['llava', 'moondream', 'bakllava', 'qwen', 'gemma', 'vl', 'vision', 'minicpm', 'paligemma']
                    return sorted([m for m in models if any(v in m.lower() for v in vision_models)])
                
                return sorted(models)
            except Exception as e:
                print(f"[ScribeNEO] Ollama Sync Error: {e}")
                return []

        elif provider == "LM Studio":
            key = api_key or cfg.get("lmstudio_key", "")
            url = endpoint_url or cfg["lmstudio_endpoint"]
            headers = {"Authorization": f"Bearer {key}"} if key else {}
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{url.rstrip('/')}/models", headers=headers, timeout=min(req_timeout, 5.0))
                    response.raise_for_status()
                    data = response.json()
                models = data.get('data', [])
                
                if is_vision:
                    vision_keywords = ['vision', 'gemini', 'gpt-4o', 'claude-3', 'vlk', 'pixtral', 'vl', 'lava', 'multimodal', 'llava', 'moondream', 'qwen', 'minicpm', 'paligemma']
                    models = [m for m in models if any(k in m['id'].lower() for k in vision_keywords)]
                
                return sorted([m['id'] for m in models])
            except Exception as e:
                print(f"[ScribeNEO] LM Studio Sync Error: {e}")
                return []
        
        return []

    async def test_connection(self, provider, api_key, endpoint_url=None):
        """
        Validate credentials and endpoint for the specified provider asynchronously.
        """
        cfg = self.get_config_data()
        req_timeout = float(cfg["timeout"])
        try:
            if provider == "OpenRouter":
                headers = {"Authorization": f"Bearer {api_key}"}
                endpoint = endpoint_url or "https://openrouter.ai/api/v1"
                async with httpx.AsyncClient() as client:
                    r = await client.get(f"{endpoint.rstrip('/')}/key", headers=headers, timeout=min(req_timeout, 10.0))
                if r.status_code == 200:
                     data = r.json().get('data', {})
                     label = data.get('label', 'Authenticated')
                     return True, f"Connected to OpenRouter as '{label}'"
                return False, f"OpenRouter Auth Error: {r.status_code}"
            
            elif provider == "Hugging Face":
                headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
                async with httpx.AsyncClient() as client:
                    r = await client.get("https://huggingface.co/api/whoami-v2", headers=headers, timeout=min(req_timeout, 10.0))
                if r.status_code == 200:
                    data = r.json()
                    return True, f"Connected to Hugging Face as {data.get('name', 'Anonymous')}"
                return False, f"HF Error: {r.text}"
            
            elif provider == "Ollama":
                url = endpoint_url or "http://localhost:11434"
                async with httpx.AsyncClient() as client:
                    r = await client.get(f"{url.rstrip('/')}/api/tags", timeout=min(req_timeout, 5.0))
                if r.status_code == 200:
                    return True, "Successfully connected to Ollama server."
                return False, f"Ollama unreachable: Status {r.status_code}"

            elif provider == "LM Studio":
                url = endpoint_url or "http://localhost:1234/v1"
                key = api_key or ""
                headers = {"Authorization": f"Bearer {key}"} if key else {}
                async with httpx.AsyncClient() as client:
                    r = await client.get(f"{url.rstrip('/')}/models", headers=headers, timeout=min(req_timeout, 5.0))
                if r.status_code == 200:
                    return True, "Successfully connected to LM Studio server."
                return False, f"LM Studio unreachable: Status {r.status_code}"
                    
        except httpx.TimeoutException:
            return False, "Connection Timeout: Server took too long to respond."
        except (httpx.ConnectError, httpx.RequestError):
            return False, "Connection Error: Could not reach the server."
        except Exception as e:
            return False, f"Connection Failed: {str(e)}"
        
        return False, "Unknown provider."

    async def query_ollama(self, messages, model="llama3", timeout=None, max_tokens=None):
        """Send chat request to Ollama backend asynchronously."""
        cfg = self.get_config_data()
        url = f"{cfg['ollama_endpoint'].rstrip('/')}/api/chat"
        
        keep_alive = cfg.get("ollama_keep_alive", 60)
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
        
        req_max_tokens = max_tokens if max_tokens is not None else cfg["max_tokens"]
        if req_max_tokens:
            data["options"] = {"num_predict": int(req_max_tokens)}

        req_timeout = timeout if timeout is not None else float(cfg["timeout"])

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=data, timeout=req_timeout)
                response.raise_for_status()
                result = response.json()
                return result['message']['content']
        except httpx.HTTPStatusError as e:
            return f"Ollama HTTP Error ({e.response.status_code}): {e.response.text}"
        except httpx.TimeoutException:
            return "Ollama Error: Request timed out."
        except Exception as e:
            return f"Ollama Error: {str(e)}"

    async def unload_ollama(self, model):
        """Unload specified model from Ollama server memory asynchronously."""
        cfg = self.get_config_data()
        url = f"{cfg['ollama_endpoint'].rstrip('/')}/api/generate"
        data = {
            "model": model,
            "keep_alive": 0,
            "stream": False
        }
        req_timeout = float(cfg["timeout"])
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=data, timeout=min(req_timeout, 10.0))
                response.raise_for_status()
                return True, f"Successfully unloaded Ollama model '{model}'."
        except Exception as e:
            return False, f"Failed to unload Ollama model: {str(e)}"

    async def fetch_loaded_ollama_models(self, endpoint_url=None):
        """Fetch running models from Ollama asynchronously."""
        cfg = self.get_config_data()
        url = endpoint_url or cfg["ollama_endpoint"]
        api_url = f"{url.rstrip('/')}/api/ps"
        req_timeout = float(cfg["timeout"])
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(api_url, timeout=min(req_timeout, 5.0))
                response.raise_for_status()
                data = response.json()
            models = [m['name'] for m in data.get('models', [])]
            return sorted(models)
        except Exception as e:
            print(f"[ScribeNEO] Ollama loaded models fetch error: {e}")
            return []

    async def query_huggingface(self, messages, model="mistralai/Mistral-7B-Instruct-v0.2", timeout=None, max_tokens=None):
        """Send chat request to Hugging Face Inference API asynchronously."""
        cfg = self.get_config_data()
        if not cfg["hf_token"]:
            return "Error: Hugging Face Token not set."

        headers = {
            "Authorization": f"Bearer {cfg['hf_token']}",
            "Content-Type": "application/json"
        }
        
        endpoint = f"{cfg['hf_endpoint'].rstrip('/')}/chat/completions"
        data = {
            "model": model,
            "messages": messages,
            "stream": False
        }
        
        req_max_tokens = max_tokens if max_tokens is not None else cfg["max_tokens"]
        if req_max_tokens:
            data["max_tokens"] = int(req_max_tokens)

        req_timeout = timeout if timeout is not None else float(cfg["timeout"])

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(endpoint, headers=headers, json=data, timeout=req_timeout)
                response.raise_for_status()
                result = response.json()
                return result['choices'][0]['message']['content']
        except httpx.HTTPStatusError as e:
            return f"Hugging Face HTTP Error ({e.response.status_code}): {e.response.text}"
        except httpx.TimeoutException:
            return "Hugging Face Error: Request timed out."
        except Exception as e:
            return f"Hugging Face Router Error: {str(e)}"

    async def query_lmstudio(self, messages, model=None, timeout=None, max_tokens=None):
        """Send chat completion request to LM Studio server asynchronously."""
        cfg = self.get_config_data()
        if not model:
            return "Error: LM Studio requires a model selected."

        headers = {"Content-Type": "application/json"}
        if cfg["lmstudio_key"]:
            headers["Authorization"] = f"Bearer {cfg['lmstudio_key']}"

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
                            err_msg = err_json.get('error', '')
                            if isinstance(err_msg, dict):
                                err_msg = err_msg.get('message', '')
                        except Exception:
                            pass
                        
                        if "role" in err_msg.lower() or "jinja" in err_msg.lower():
                            system_content = ""
                            user_content = ""
                            other_messages = []
                            for msg in messages:
                                role = msg.get("role")
                                content = msg.get("content")
                                if role == "system":
                                    system_content = content
                                elif role == "user":
                                    user_content = content
                                else:
                                    other_messages.append(msg)
                            
                            if system_content:
                                fallback_content = f"System Instructions:\n{system_content}\n\nUser Input:\n{user_content}"
                                fallback_messages = [{"role": "user", "content": fallback_content}] + other_messages
                                fallback_data = {
                                    "model": model,
                                    "messages": fallback_messages,
                                    "stream": False
                                }
                                if req_max_tokens:
                                    fallback_data["max_tokens"] = int(req_max_tokens)
                                response = await client.post(endpoint, headers=headers, json=fallback_data, timeout=req_timeout)
                    except Exception as fallback_err:
                        print(f"[ScribeNEO] LM Studio role fallback failed: {fallback_err}")

                if response.status_code != 200:
                    print(f"[ScribeNEO] LM Studio API Error: {response.text}")
                response.raise_for_status()
                result = response.json()
                return result['choices'][0]['message']['content']
        except httpx.HTTPStatusError as e:
            return f"LM Studio HTTP Error ({e.response.status_code}): {e.response.text}"
        except httpx.TimeoutException:
            return "LM Studio Error: Request timed out."
        except Exception as e:
            print(f"[ScribeNEO] LM Studio Critical Error: {str(e)}")
            return f"LM Studio Error: {str(e)}"

    async def fetch_loaded_lmstudio_models(self, endpoint_url=None):
        """Fetch running model instances from LM Studio asynchronously."""
        cfg = self.get_config_data()
        url = endpoint_url or cfg["lmstudio_endpoint"]
        base_url = url.rstrip('/')
        if base_url.endswith('/v1'):
            api_url = base_url[:-3] + '/api/v1/models'
        else:
            api_url = base_url + '/api/v1/models'
        req_timeout = float(cfg["timeout"])
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(api_url, timeout=min(req_timeout, 5.0))
                response.raise_for_status()
                data = response.json()
            
            if isinstance(data, dict):
                 models_list = data.get('models') or data.get('data') or []
            else:
                 models_list = data

            loaded_models = []
            for m in models_list:
                loaded_insts = m.get('loaded_instances', [])
                if loaded_insts:
                    for inst in loaded_insts:
                        inst_id = inst.get('id')
                        if inst_id:
                            loaded_models.append(inst_id)
            return sorted(loaded_models)
        except Exception as e:
            print(f"[ScribeNEO] LM Studio loaded models fetch error: {e}")
            return []

    async def unload_lmstudio(self, instance_id):
        """Unload specified model instance from LM Studio asynchronously."""
        cfg = self.get_config_data()
        url = cfg['lmstudio_endpoint']
        base_url = url.rstrip('/')
        if base_url.endswith('/v1'):
            api_url = base_url[:-3] + '/api/v1/models/unload'
        else:
            api_url = base_url + '/api/v1/models/unload'

        data = {"instance_id": instance_id}
        headers = {}
        if cfg["lmstudio_key"]:
            headers["Authorization"] = f"Bearer {cfg['lmstudio_key']}"
        req_timeout = float(cfg["timeout"])

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(api_url, headers=headers, json=data, timeout=min(req_timeout, 5.0))
                response.raise_for_status()
                return True, f"Successfully unloaded LM Studio model instance '{instance_id}'."
        except Exception as e:
            return False, f"Failed to unload LM Studio model: {str(e)}"

    async def enhance_prompt(self, user_prompt, persona_system_prompt, provider="openrouter", model=None, timeout=None, max_tokens=None):
        """
        Orchestrates final prompt enhancement payload and routes to the provider asynchronously.
        """
        messages = []
        user_msg = f"Enhance this prompt for Stable Diffusion: {user_prompt}"
        
        if persona_system_prompt:
            if "{input}" in persona_system_prompt:
                persona_system_prompt = persona_system_prompt.replace("{input}", user_prompt)
                user_msg = "Process the request as instructed in the system prompt."
                
            messages.append({"role": "system", "content": persona_system_prompt})
            
        messages.append({"role": "user", "content": user_msg})

        provider_key = provider.lower().replace(" ","")
        if provider_key == "openrouter":
            return await self.query_openrouter(messages, model, timeout=timeout, max_tokens=max_tokens)
        elif provider_key == "ollama":
            return await self.query_ollama(messages, model or "llama3", timeout=timeout, max_tokens=max_tokens)
        elif provider_key == "huggingface":
            return await self.query_huggingface(messages, model or "mistralai/Mistral-7B-Instruct-v0.2", timeout=timeout, max_tokens=max_tokens)
        elif provider_key == "lmstudio":
            return await self.query_lmstudio(messages, model, timeout=timeout, max_tokens=max_tokens)
        
        return "Error: Unknown provider."

llm = LLMManager()
