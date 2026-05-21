"""
Main UI Entry Point for ScribeNEO.
Defines the Gradio interface, components, and event bindings for the extension.
"""
import os
import sys
import json
import gradio as gr

# Ensure extension root is in sys.path
scripts_dir = os.path.dirname(os.path.abspath(__file__))
ext_root = os.path.dirname(scripts_dir)
if ext_root not in sys.path:
    sys.path.append(ext_root)

from modules import scripts, script_callbacks, shared
from llm import llm
from tagger import tagger
from settings import load_config, save_config

base_dir = scripts.basedir()
personas_path = os.path.join(base_dir, "personas.json")

def load_personas():
    """Load and migrate custom user personas from local storage."""
    if os.path.exists(personas_path):
        try:
            with open(personas_path, 'r', encoding='utf-8') as f:
                personas = json.load(f)
            
            modified = False
            for p in personas:
                if 'name' in p:
                    if p['name'].startswith("Scribe: "):
                        p['name'] = p['name'].replace("Scribe: ", "", 1)
                        p['type'] = 'scribe'
                        modified = True
                    elif p['name'].startswith("Vision: "):
                        p['name'] = p['name'].replace("Vision: ", "", 1)
                        p['type'] = 'vision'
                        modified = True
                
                if 'type' not in p:
                    p['type'] = 'scribe'
                    modified = True
            
            if modified:
                save_personas(personas)
                
            return personas
        except Exception as e:
            print(f"[ScribeNEO] Error loading personas: {e}")
            return []
    return []

def save_personas(personas):
    """Save custom user personas to local storage."""
    try:
        with open(personas_path, 'w', encoding='utf-8') as f:
            json.dump(personas, f, indent=4)
    except Exception as e:
        print(f"[ScribeNEO] Error saving personas: {e}")

def get_enhancer_personas(personas):
    """Filter for prompt enhancer personas."""
    return ["None"] + [p['name'] for p in personas if p.get('type') == 'scribe']

def get_vision_personas(personas):
    """Filter for vision scanner personas."""
    return ["None"] + [p['name'] for p in personas if p.get('type') == 'vision']

# --- UI COMPONENT BUILDERS ---

def create_enhancer_ui(persona_names, last_enhancer, last_persona="None"):
    """Builds the Prompt Enhancer column interface."""
    with gr.Column(scale=1, elem_classes="scribeneo-module"):
        gr.Markdown("### ✨ PROMPT ENHANCER")
        
        with gr.Row(elem_classes="scribeneo-engine-row"):
            enhancer_model = gr.Dropdown(
                choices=[last_enhancer] if last_enhancer else [],
                value=last_enhancer,
                label="AI Engine",
                scale=3,
                allow_custom_value=True,
                elem_id="scribeneo_enhancer_model"
            )
            refresh_enhancer = gr.Button("🔄", elem_classes="scribeneo-refresh-btn", scale=0)
            enhancer_persona = gr.Dropdown(
                choices=persona_names,
                value=last_persona,
                label="Active Persona",
                scale=2,
                elem_id="scribeneo_enhancer_persona"
            )
        
        raw_input = gr.Textbox(
            label="Initial Prompt",
            lines=5,
            placeholder="Type keywords or a simple idea...",
            elem_id="scribeneo_main_input"
        )
        with gr.Row(elem_classes="scribeneo-action-bar"):
            enhance_btn = gr.Button("ENHANCE PROMPT", variant="primary", elem_id="scribeneo_main_enhance_btn", scale=3)
            stop_enhance_btn = gr.Button("🛑", elem_id="scribeneo_stop_enhance", scale=1, interactive=False)
            copy_enhance_btn = gr.Button("📋", elem_id="scribeneo_copy_enhance", scale=1)
            clear_enhance_btn = gr.Button("🗑️", elem_id="scribeneo_clear_enhance", scale=1)
        
        enhanced_output = gr.Textbox(
            label="Enhanced Result",
            lines=8,
            show_copy_button=False,
            elem_id="scribeneo_main_result"
        )
        
        with gr.Row(elem_classes="scribeneo-action-row"):
            send_txt2img = gr.Button("📤 Send to txt2img", elem_id="scribeneo_send_txt2img")
            send_img2img = gr.Button("🖼️ Send to img2img", elem_id="scribeneo_send_img2img")
        
        with gr.Group(elem_classes="scribeneo-tip-card"):
            gr.Markdown("""
### 📖 DASHBOARD LEGEND
*   **Stop (🛑)**: Instantly cancels long-running AI requests.
*   **Refresh (🔄)**: Synchronizes with the backend for models.
*   **Enhance / Scan**: Processes input through AI and persona.
*   **Send To (📤)**: Transfers result to txt2img or img2img.
*   **Append (➕)**: Merges scanned metadata into current intent.
""")
    return (
        enhancer_model, refresh_enhancer, enhancer_persona, raw_input, enhance_btn,
        stop_enhance_btn, copy_enhance_btn, clear_enhance_btn, enhanced_output,
        send_txt2img, send_img2img
    )

def create_vision_ui(persona_names, last_vision, last_persona="None"):
    """Builds the Vision Toolset column interface."""
    with gr.Column(scale=1, elem_classes="scribeneo-module"):
        gr.Markdown("### 👁️ VISION TOOLSET")
        
        with gr.Row(elem_classes="scribeneo-engine-row"):
            caption_model = gr.Dropdown(
                choices=[last_vision] if last_vision else [],
                value=last_vision,
                label="Vision Engine",
                scale=3,
                allow_custom_value=True,
                elem_id="scribeneo_vision_model"
            )
            refresh_vision = gr.Button("🔄", elem_classes="scribeneo-refresh-btn", scale=0)
            caption_persona = gr.Dropdown(
                choices=persona_names,
                value=last_persona,
                label="Vision Persona",
                scale=2,
                elem_id="scribeneo_vision_persona"
            )

        with gr.Row():
            override_vision_filter = gr.Checkbox(
                label="Show all models (bypass vision filter)",
                value=False,
                elem_id="scribeneo_override_vision_filter"
            )
        
        img_input = gr.Image(label="Source Image", type="pil", elem_classes="scribeneo-image-container")
        with gr.Row(elem_classes="scribeneo-action-bar"):
            tag_btn = gr.Button("SCAN IMAGE", variant="primary", elem_id="scribeneo_decode_btn", scale=3)
            stop_vision_btn = gr.Button("🛑", elem_id="scribeneo_stop_vision", scale=1, interactive=False)
            copy_vision_btn = gr.Button("📋", elem_id="scribeneo_copy_vision", scale=1)
            clear_vision_btn = gr.Button("🗑️", elem_id="scribeneo_clear_vision", scale=1)
        
        tag_output = gr.Textbox(
            label="Image Analysis Result",
            lines=8,
            show_copy_button=False,
            elem_id="scribeneo_vision_result"
        )
        
        with gr.Row(elem_classes="scribeneo-action-row"):
            vis_to_txt2img = gr.Button("📤 Send to txt2img", elem_id="scribeneo_vision_send_txt2img")
            vis_to_img2img = gr.Button("🖼️ Send to img2img", elem_id="scribeneo_vision_img2img")
        
        with gr.Row(elem_classes="scribeneo-action-row"):
            append_btn = gr.Button("➕ Append to Prompt")
            replace_btn = gr.Button("🔄 Replace Prompt")
            
    return (
        caption_model, refresh_vision, caption_persona, img_input, tag_btn,
        stop_vision_btn, copy_vision_btn, clear_vision_btn, tag_output,
        vis_to_txt2img, vis_to_img2img, append_btn, replace_btn, override_vision_filter
    )

def create_config_ui(provider, init_key, init_end, init_keep_alive, init_timeout=30, init_max_tokens=512):
    """Builds the Settings & Configuration interface."""
    with gr.Accordion("⚙️ Settings & Configuration", open=False):
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("#### ⚙️ Service Settings")
                provider_input = gr.Dropdown(
                    choices=["OpenRouter", "Hugging Face", "Ollama", "LM Studio"],
                    value=provider,
                    label="Active Service Provider",
                    elem_id="scribeneo_provider_input"
                )
                
                with gr.Row(elem_classes="scribeneo-config-row") as key_row:
                    api_key_input = gr.Textbox(
                        label="API Key / Token",
                        value=init_key,
                        type="password",
                        scale=4,
                        visible=(provider != "Ollama")
                    )
                    reveal_api_btn = gr.Button("👁️", elem_id="scribeneo_reveal_api", scale=1, visible=(provider != "Ollama"))
                
                with gr.Row(elem_classes="scribeneo-config-row"):
                    endpoint_input = gr.Textbox(label="Endpoint URL", value=init_end, scale=4, interactive=False)
                    edit_endpoint_btn = gr.Button("✏️", elem_id="scribeneo_edit_endpoint", scale=1)

                with gr.Row(elem_classes="scribeneo-config-row", visible=(provider == "Ollama")) as ollama_settings_row:
                    keep_alive_input = gr.Number(
                        label="Keep-Alive",
                        value=init_keep_alive,
                        minimum=-1,
                        precision=0,
                        scale=1,
                        visible=(provider == "Ollama"),
                        elem_id="scribeneo_keep_alive_num"
                    )
                    ollama_model_dropdown = gr.Dropdown(
                        choices=[],
                        label="Model to Unload",
                        interactive=True,
                        allow_custom_value=True,
                        scale=5,
                        visible=(provider == "Ollama"),
                        elem_id="scribeneo_unload_model_dropdown"
                    )
                    unload_model_btn = gr.Button(
                        "🛑 Unload",
                        variant="stop",
                        scale=1,
                        visible=(provider == "Ollama"),
                        elem_id="scribeneo_unload_btn"
                    )
                
                with gr.Row(elem_classes="scribeneo-settings-row"):
                    timeout_input = gr.Number(
                        label="Request Timeout (seconds)",
                        value=init_timeout,
                        minimum=5,
                        maximum=300,
                        precision=0,
                        scale=1,
                        elem_id="scribeneo_request_timeout"
                    )
                    max_tokens_input = gr.Slider(
                        label="Max Output Tokens",
                        value=init_max_tokens,
                        minimum=16,
                        maximum=4096,
                        step=16,
                        scale=1,
                        elem_id="scribeneo_max_tokens"
                    )

                with gr.Row():
                    test_conn_btn = gr.Button("🔌 Test Connection", variant="secondary")
                    save_global_btn = gr.Button("💾 Save Configuration", variant="primary")

            with gr.Column(scale=1, elem_id="scribeneo_settings_reference"):
                gr.Markdown("""
### ⚙️ Settings Reference
*   **Service Provider**: Backend platform used for text and vision model inference.
*   **API Key / Token**: Security credentials required to authenticate with the chosen service.
*   **Endpoint URL**: Base network address of the inference server.
*   **Ollama Keep-Alive**: Period of time that models remain loaded in GPU VRAM in seconds (0 to unload immediately, -1 to keep forever).
*   **Model to Unload**: Select and unload specific models from active memory.
*   **Request Timeout**: Maximum time threshold permitted for network request completion.
*   **Max Output Tokens**: Maximum limit on the number of generated response tokens.
*   **Test Connection**: Verify network and authentication state with the provider.
*   **Save Configuration**: Save the active settings to the local configuration file.
""", elem_classes="scribeneo-handbook")
    return (
        provider_input, api_key_input, reveal_api_btn, endpoint_input, edit_endpoint_btn,
        test_conn_btn, save_global_btn, keep_alive_input, key_row, ollama_settings_row,
        ollama_model_dropdown, unload_model_btn, timeout_input, max_tokens_input
    )

def create_persona_ui(persona_names):
    """Builds the Persona Management interface."""
    with gr.Accordion("🎭 Persona Management", open=False):
        gr.Markdown("Configure neural personas to guide the enhancement process.")
        with gr.Row(elem_classes="scribeneo-engine-row"):
            p_select = gr.Dropdown(choices=persona_names[1:], label="Select to Edit", scale=1)
            p_refresh = gr.Button("🔄", elem_classes="scribeneo-refresh-btn", scale=0)
        
        with gr.Group():
            with gr.Row():
                p_name = gr.Textbox(label="Name", placeholder="e.g. Cinematic Photographer", scale=3)
                p_type = gr.Radio(choices=["Prompt Enhancer", "Vision"], value="Prompt Enhancer", label="Category", scale=2)
            p_desc = gr.Textbox(label="Description", placeholder="A short blurb about this identity")
            p_prompt = gr.Textbox(label="System Prompt", lines=6, placeholder="Define the AI's behavior and style...")
        
        with gr.Row():
            p_save = gr.Button("💾 Save Persona", variant="primary")
            p_delete = gr.Button("🗑️ Delete", variant="stop")
            p_new = gr.Button("✨ New Persona")
            
    return p_select, p_refresh, p_name, p_desc, p_prompt, p_type, p_save, p_delete, p_new

def on_ui_tabs():
    """Gradio tab setup for ScribeNEO."""
    personas = load_personas()
    persona_names = ["None"] + [p['name'] for p in personas]
    
    enhancer_choices = get_enhancer_personas(personas)
    vision_choices = get_vision_personas(personas)
    
    conf = load_config()
    provider = "OpenRouter"
    
    init_key = ""
    init_end = ""
    init_keep_alive = conf["ollama"].get("keep_alive", 60)
    init_timeout = conf.get("timeout", 30)
    init_max_tokens = conf.get("max_tokens", 512)
    
    if provider == "OpenRouter":
        init_key = conf["openrouter"]["key"]
        init_end = conf["openrouter"]["endpoint"]
    elif provider == "Hugging Face":
        init_key = conf["huggingface"]["key"]
        init_end = conf["huggingface"]["endpoint"]
    elif provider == "Ollama":
        init_end = conf["ollama"]["endpoint"]

    with gr.Blocks(analytics_enabled=False, elem_id="scribe_neo_container") as scribeneo_tab:
        
        with gr.Row():
            (enhancer_model, refresh_enhancer, enhancer_persona, raw_input, enhance_btn, 
             stop_enhance_btn, copy_enhance_btn, clear_enhance_btn, enhanced_output, 
             send_txt2img, send_img2img) = create_enhancer_ui(enhancer_choices, "", "None")

            (caption_model, refresh_vision, caption_persona, img_input, tag_btn, 
             stop_vision_btn, copy_vision_btn, clear_vision_btn, tag_output, 
             vis_to_txt2img, vis_to_img2img, append_btn, replace_btn, override_vision_filter) = create_vision_ui(vision_choices, "", "None")

        (provider_input, api_key_input, reveal_api_btn, endpoint_input, 
         edit_endpoint_btn, test_conn_btn, save_global_btn, keep_alive_input, 
         key_row, ollama_settings_row, ollama_model_dropdown, unload_model_btn,
         timeout_input, max_tokens_input) = create_config_ui(provider, init_key, init_end, init_keep_alive, init_timeout, init_max_tokens)

        (p_select, p_refresh, p_name, p_desc, p_prompt, p_type,
         p_save, p_delete, p_new) = create_persona_ui(persona_names)

        # --- EVENT HANDLERS ---
        
        reveal_state = gr.State("password")
        
        def toggle_api_key_visibility(current):
            new_type = "text" if current == "password" else "password"
            icon = "🙈" if new_type == "text" else "👁️"
            return new_type, gr.update(type=new_type), gr.update(value=icon)
        
        reveal_api_btn.click(
            fn=toggle_api_key_visibility,
            inputs=[reveal_state],
            outputs=[reveal_state, api_key_input, reveal_api_btn],
            show_progress="hidden"
        )

        provider_switched = [False]

        async def update_config_fields(provider):
            conf = load_config()
            key_val = ""
            end_val = ""
            keep_alive_val = conf["ollama"].get("keep_alive", 60)
            timeout_val = conf.get("timeout", 30)
            max_tokens_val = conf.get("max_tokens", 512)
            
            if isinstance(keep_alive_val, str):
                if keep_alive_val.strip().isdigit():
                    keep_alive_val = int(keep_alive_val.strip())
                else:
                    keep_alive_val = 600

            show_key = (provider in ["OpenRouter", "Hugging Face"])
            show_keep_alive = (provider == "Ollama")
            show_unload = (provider in ["Ollama", "LM Studio"])
            show_unload_row = (provider in ["Ollama", "LM Studio"])
            
            if provider == "OpenRouter":
                key_val = conf["openrouter"]["key"]
                end_val = conf["openrouter"]["endpoint"]
            elif provider == "Hugging Face":
                key_val = conf["huggingface"]["key"]
                end_val = conf["huggingface"]["endpoint"]
            elif provider == "Ollama":
                key_val = ""
                end_val = conf["ollama"]["endpoint"]
            elif provider == "LM Studio":
                key_val = conf["lmstudio"].get("key", "")
                end_val = conf["lmstudio"]["endpoint"]
            
            if provider_switched[0]:
                gr.Info(f"Switched to {provider}. Hit 🔄 to refresh your model lists.")
            provider_switched[0] = True

            loaded_models = []
            if provider == "Ollama":
                try:
                    loaded_models = await llm.fetch_loaded_ollama_models(endpoint_url=end_val)
                except Exception:
                    pass
            elif provider == "LM Studio":
                try:
                    loaded_models = await llm.fetch_loaded_lmstudio_models(endpoint_url=end_val)
                except Exception:
                    pass

            return (
                gr.update(value=key_val, visible=show_key),
                gr.update(visible=show_key),
                gr.update(value=end_val, interactive=False),
                gr.update(value=keep_alive_val, visible=show_keep_alive),
                gr.update(choices=loaded_models, value=loaded_models[0] if loaded_models else None, visible=show_unload),
                gr.update(visible=show_unload),
                gr.update(visible=show_key),
                gr.update(visible=show_unload_row),
                gr.update(choices=[], value=None),
                gr.update(choices=[], value=None),
                gr.update(value=timeout_val),
                gr.update(value=max_tokens_val)
            )

        provider_input.change(
            fn=update_config_fields, 
            inputs=[provider_input], 
            outputs=[
                api_key_input, 
                reveal_api_btn, 
                endpoint_input, 
                keep_alive_input, 
                ollama_model_dropdown, 
                unload_model_btn,
                key_row,
                ollama_settings_row,
                enhancer_model,
                caption_model,
                timeout_input,
                max_tokens_input
            ],
            show_progress="hidden"
        )

        def toggle_endpoint_editing(current_interactive):
            new_state = not current_interactive
            icon = "✅" if new_state else "✏️"
            return gr.update(interactive=new_state), gr.update(value=icon), new_state
        
        endpoint_interactive_state = gr.State(False)
        edit_endpoint_btn.click(
            fn=toggle_endpoint_editing, 
            inputs=[endpoint_interactive_state], 
            outputs=[endpoint_input, edit_endpoint_btn, endpoint_interactive_state],
            show_progress="hidden"
        )

        async def test_connection_handler(provider, api_key, endpoint):
            success, msg = await llm.test_connection(provider, api_key, endpoint)
            if success:
                gr.Info(msg)
            else:
                gr.Warning(msg)
            return msg

        test_conn_btn.click(fn=test_connection_handler, inputs=[provider_input, api_key_input, endpoint_input], show_progress="hidden")

        async def sync_models_handler(provider, api_key, endpoint, is_vision=False, override_filter=False):
            fetch_vision = is_vision and not override_filter
            models = await llm.fetch_models(provider, api_key, endpoint, is_vision=fetch_vision)
            if not models:
                gr.Warning(f"Failed to fetch {('Vision' if fetch_vision else 'Text/All')} models for {provider}.")
                return gr.update()
            
            gr.Info(f"Synced {len(models)} {('Vision' if fetch_vision else 'Text/All')} models.")
            return gr.update(choices=models, value=models[0] if models else None)

        refresh_enhancer.click(
            fn=lambda: gr.update(choices=[], value=None),
            outputs=[enhancer_model],
            show_progress="hidden"
        ).then(
            fn=sync_models_handler,
            inputs=[provider_input, api_key_input, endpoint_input, gr.State(False), gr.State(False)],
            outputs=[enhancer_model],
            show_progress="hidden"
        )

        refresh_vision.click(
            fn=lambda: gr.update(choices=[], value=None),
            outputs=[caption_model],
            show_progress="hidden"
        ).then(
            fn=sync_models_handler,
            inputs=[provider_input, api_key_input, endpoint_input, gr.State(True), override_vision_filter],
            outputs=[caption_model],
            show_progress="hidden"
        )

        override_vision_filter.change(
            fn=lambda: gr.update(choices=[], value=None),
            outputs=[caption_model],
            show_progress="hidden"
        ).then(
            fn=sync_models_handler,
            inputs=[provider_input, api_key_input, endpoint_input, gr.State(True), override_vision_filter],
            outputs=[caption_model],
            show_progress="hidden"
        )

        def save_config_handler(provider, key, endpoint, keep_alive, timeout, max_tokens):
            conf = load_config()
            if provider == "OpenRouter":
                conf["openrouter"]["key"] = key
                conf["openrouter"]["endpoint"] = endpoint
            elif provider == "Hugging Face":
                conf["huggingface"]["key"] = key
                conf["huggingface"]["endpoint"] = endpoint
            elif provider == "Ollama":
                conf["ollama"]["endpoint"] = endpoint
                conf["ollama"]["keep_alive"] = keep_alive
            elif provider == "LM Studio":
                conf["lmstudio"]["key"] = key
                conf["lmstudio"]["endpoint"] = endpoint
            
            conf["timeout"] = int(timeout)
            conf["max_tokens"] = int(max_tokens)
            
            save_config(conf)
            gr.Info(f"Local config for {provider} saved.")
            return gr.update(interactive=False), gr.update(value="✏️"), False

        save_global_btn.click(
            fn=save_config_handler, 
            inputs=[provider_input, api_key_input, endpoint_input, keep_alive_input, timeout_input, max_tokens_input], 
            outputs=[endpoint_input, edit_endpoint_btn, endpoint_interactive_state], 
            show_progress="hidden"
        )

        async def unload_model_handler(provider, model, endpoint):
            if not model:
                gr.Warning("Please select or type a model/instance name to unload.")
                return gr.update()
            if provider == "Ollama":
                success, msg = await llm.unload_ollama(model)
            elif provider == "LM Studio":
                success, msg = await llm.unload_lmstudio(model)
            else:
                success, msg = False, "Unsupported provider for unloading."
                
            if success:
                gr.Info(msg)
            else:
                gr.Warning(msg)

            loaded_models = []
            if provider == "Ollama":
                try:
                    loaded_models = await llm.fetch_loaded_ollama_models(endpoint_url=endpoint)
                except Exception:
                    pass
            elif provider == "LM Studio":
                try:
                    loaded_models = await llm.fetch_loaded_lmstudio_models(endpoint_url=endpoint)
                except Exception:
                    pass
            
            return gr.update(choices=loaded_models, value=loaded_models[0] if loaded_models else None)

        unload_model_btn.click(
            fn=unload_model_handler, 
            inputs=[provider_input, ollama_model_dropdown, endpoint_input], 
            outputs=[ollama_model_dropdown],
            show_progress="hidden"
        )

        async def refresh_unload_choices(provider, endpoint):
            loaded_models = []
            if provider == "Ollama":
                try:
                    loaded_models = await llm.fetch_loaded_ollama_models(endpoint_url=endpoint)
                except Exception:
                    pass
            elif provider == "LM Studio":
                try:
                    loaded_models = await llm.fetch_loaded_lmstudio_models(endpoint_url=endpoint)
                except Exception:
                    pass
            return gr.update(choices=loaded_models, value=loaded_models[0] if loaded_models else None)

        ollama_model_dropdown.focus(
            fn=refresh_unload_choices,
            inputs=[provider_input, endpoint_input],
            outputs=[ollama_model_dropdown],
            show_progress="hidden"
        )

        def load_persona_fields(name):
            ps = load_personas()
            p = next((x for x in ps if x['name'] == name), None)
            if p: 
                type_val = "Vision" if p.get('type') == 'vision' else "Prompt Enhancer"
                return p['name'], p['description'], p['system_prompt'], type_val
            return "", "", "", "Prompt Enhancer"

        p_select.change(fn=load_persona_fields, inputs=[p_select], outputs=[p_name, p_desc, p_prompt, p_type], show_progress="hidden")

        def save_persona_handler(name, desc, prompt, p_type_val, original):
            ps = load_personas()
            type_val = "vision" if p_type_val == "Vision" else "scribe"
            new_p = {"name": name, "type": type_val, "description": desc, "system_prompt": prompt}
            found = False
            for i, p in enumerate(ps):
                if p['name'] == original:
                    ps[i] = new_p
                    found = True
                    break
            if not found:
                ps.append(new_p)
            save_personas(ps)
            names_with_none = ["None"] + [x['name'] for x in ps]
            gr.Info(f"Persona '{name}' saved.")
            return gr.update(choices=names_with_none[1:]), gr.update(choices=get_enhancer_personas(ps)), gr.update(choices=get_vision_personas(ps))

        def delete_persona_handler(name):
            if not name:
                return gr.update(), gr.update(), gr.update()
            ps = load_personas()
            ps = [p for p in ps if p['name'] != name]
            save_personas(ps)
            choices_list = [x['name'] for x in ps]
            all_names = ["None"] + choices_list
            gr.Info(f"Persona '{name}' deleted.")
            return gr.update(choices=choices_list, value=None), gr.update(choices=get_enhancer_personas(ps)), gr.update(choices=get_vision_personas(ps))

        p_save.click(
            fn=save_persona_handler, 
            inputs=[p_name, p_desc, p_prompt, p_type, p_select], 
            outputs=[p_select, enhancer_persona, caption_persona], 
            show_progress="hidden"
        )
        p_delete.click(
            fn=delete_persona_handler, 
            inputs=[p_select], 
            outputs=[p_select, enhancer_persona, caption_persona], 
            show_progress="hidden"
        )
        p_new.click(
            fn=lambda: ("", "", "", "Prompt Enhancer", None), 
            outputs=[p_name, p_desc, p_prompt, p_type, p_select], 
            show_progress="hidden"
        )

        async def enhance_prompt_handler(prompt, person_name, model, provider, timeout, max_tokens):
            if not prompt: 
                yield "Error: Provide an intent first."
                return
            
            yield "[ScribeNEO is formulating your enhanced prompt...]"
            
            ps = load_personas()
            p = next((x for x in ps if x['name'] == person_name), None)
            sys_prompt = p['system_prompt'] if p else ""
            
            result = await llm.enhance_prompt(
                prompt, sys_prompt, 
                provider=provider.lower().replace(" ",""), 
                model=model,
                timeout=float(timeout),
                max_tokens=int(max_tokens)
            )
            yield result

        enhance_event = enhance_btn.click(
            fn=enhance_prompt_handler,
            inputs=[raw_input, enhancer_persona, enhancer_model, provider_input, timeout_input, max_tokens_input],
            outputs=[enhanced_output]
        )
        enhance_event.then(
            fn=refresh_unload_choices,
            inputs=[provider_input, endpoint_input],
            outputs=[ollama_model_dropdown],
            show_progress="hidden"
        )
        stop_enhance_btn.click(
            fn=lambda: "[Request cancelled]",
            outputs=[enhanced_output],
            cancels=[enhance_event]
        )
        clear_enhance_btn.click(fn=lambda: "", outputs=[enhanced_output])

        async def scan_image_handler(img, person_name, model, provider, timeout, max_tokens):
            if not img:
                yield "Error: Upload an image."
                return
            
            yield "[ScribeNEO is scanning your image...]"
            
            ps = load_personas()
            p = next((x for x in ps if x['name'] == person_name), None)
            sys_prompt = p['system_prompt'] if p else None
            
            result = await tagger.scan_image(
                img, 
                provider=provider.lower().replace(" ",""), 
                model=model, 
                system_prompt=sys_prompt,
                timeout=float(timeout),
                max_tokens=int(max_tokens)
            )
            yield result

        vision_event = tag_btn.click(
            fn=scan_image_handler,
            inputs=[img_input, caption_persona, caption_model, provider_input, timeout_input, max_tokens_input],
            outputs=[tag_output]
        )
        vision_event.then(
            fn=refresh_unload_choices,
            inputs=[provider_input, endpoint_input],
            outputs=[ollama_model_dropdown],
            show_progress="hidden"
        )
        stop_vision_btn.click(
            fn=lambda: "[Request cancelled]",
            outputs=[tag_output],
            cancels=[vision_event]
        )
        clear_vision_btn.click(fn=lambda: "", outputs=[tag_output])

        # Interactive listeners for JS functions
        for btn in [send_txt2img, send_img2img, copy_enhance_btn, vis_to_txt2img, vis_to_img2img, copy_vision_btn]:
            btn.click(fn=None, _js="() => {}")

        append_btn.click(fn=lambda x, y: f"{x}\n{y}" if x else y, inputs=[raw_input, tag_output], outputs=[raw_input])
        replace_btn.click(fn=lambda x: x, inputs=[tag_output], outputs=[raw_input])

        # Initial UI load
        scribeneo_tab.load(
            fn=update_config_fields, 
            inputs=[provider_input], 
            outputs=[
                api_key_input, 
                reveal_api_btn, 
                endpoint_input, 
                keep_alive_input, 
                ollama_model_dropdown, 
                unload_model_btn,
                key_row,
                ollama_settings_row,
                enhancer_model,
                caption_model,
                timeout_input,
                max_tokens_input
            ],
            show_progress="hidden"
        )

    return [(scribeneo_tab, "ScribeNEO", "scribe_neo_tab")]

script_callbacks.on_ui_tabs(on_ui_tabs)
