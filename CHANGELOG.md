# Changelog

## [1.1.0] - 2026-05-20

### Added
- **Native Ollama API Integration**: Migrated all Ollama calls from the OpenAI API compatibility shim to native `/api/chat` and `/api/generate` endpoints. Special thanks to [@hirorohi03](https://github.com/hirorohi03) for suggesting this improvement!
- **Ollama VRAM Model Unloading**: Added an "Unload" button and model selection manager to instantly release active models from GPU VRAM. Special thanks to [@hirorohi03](https://github.com/hirorohi03) for the recommendation!
- **Configurable Keep-Alive**: Added a customizable "Keep-Alive" numeric setting (in seconds) next to the model unloader to control how long models remain loaded in memory. Special thanks to [@hirorohi03](https://github.com/hirorohi03) for the recommendation!
- **Bypass Vision Filters**: Added a "Show all models (bypass vision filter)" checkbox in the Vision Toolset to query Ollama models manually even if they aren't on the predefined vision model list.
- **Expanded Vision Models**: Included broader default support for Ollama vision models (`qwen`, `gemma`, `vl`, `vision`, `minicpm`, `paligemma`).
- **Schema-Based Persona Management**: Removed legacy name prefixes (`Scribe: ` and `Vision: `) from the `personas.json` file, replacing them with a structured `"type"` attribute (`scribe` vs. `vision`) for cleaner database separation.
- **Automatic Persona Database Migration**: Added startup logic that automatically migrates legacy name prefix schemas to the new type-based database format.
- **Persona Lab Category Toggle**: Integrated a compact **Category** selector control inside the Persona Lab UI to separate Prompt Enhancer and Vision personas during editing.
- **Ollama Vision Persona Support**: Rewrote local Ollama image interrogation to use the native `/api/chat` endpoint, adding full support for custom Vision system prompts and personas.

### Fixed
- **Vision Query Error Handling**: Added graceful HTTP 400 interception. If a text-only model is interrogated with an image, the system now returns a helpful capability suggestion instead of throwing an unhandled exception.