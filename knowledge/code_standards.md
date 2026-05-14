# SKILL: Advanced Code Modification Standards (LLMTestbed)

## 🏗️ Architecture & Modularity
- **Design Patterns**: Prefer **Modularity**, **Dependency Injection**, **IoC (Inversion of Control)**, and **Factory patterns**. This ensures the code is simple to test, understand, maintain, and evolve.
- **Classes over Functions**: Prefer classes over just a bunch of functions when possible to encapsulate state and behavior.
- **Functions and methods**: They should be less than 20 lines long and do only one thing. Try to use pure functions and avoid side effects as much as possible. Make sure they are deterministic and predictable. If a function is more than 20 lines long, it should be refactored into smaller functions.
- **UI Components**: All UI logic must reside in `src/streamlit_app/components/`.
- **API Communication**: All backend calls must use a dedicated client (e.g., `src/streamlit_app/api/client.py`).
- **Presets**: Prompts and attack templates must be stored in `src/streamlit_app/presets/`.
- **Styling**: CSS must be in `src/streamlit_app/styles/main.css` and loaded via `loader.py`. Keep styles simple and theme-aware (no hardcoded colors).

## 📁 File & Class Organization
- **No Utils/Helpers**: Never use `helper` or `utils` in a file name. Use purpose-driven names (e.g., `time.py` for time management, `regex.py` for regex logic).
- **Constants**: 
    - **External**: Create a `constants.py` file at the root of the component (e.g., `src/backend/constants.py` or `src/streamlit_app/constants.py`).
    - **Internal**: Declare at the very top of the class/file.
- **Class Structure**:
    1. Internal Constants
    2. Public API (Methods intended for external use)
    3. Private Internal Helpers (Methods prefixed with `_`)

## 🎨 Theme & Aesthetics
- **Theme Awareness**: NEVER hardcode colors in CSS or Python. Use Streamlit CSS variables (e.g., `var(--background-color)`).
- **Premium Feel**: Maintain high-contrast chat bubbles, pulsing avatars during processing, and JetBrains Mono for reasoning/logs.

## 🕵️‍♂️ Observability & Quality
- **Automated Testing**: Create tests for EACH new modification.
- **Streaming Integrity**: Ensure that streaming functionality is ALWAYS working and verified after UI changes.
- **Documentation**: Every function and class must have a clear, up-to-date **Docstring** using **Google Style**: 1. high level role, description, how it works and specificities. 2. Arguments, types, order, default values. 3. Return types, what is returned and specificities. 4. Potential errors. 5. Examples on how to use it.

## 🛡️ Security by Design
- **Secure Coding**: Prioritize "Security by Design" to avoid introducing vulnerabilities.
- **Granular Logging**: Every major action (REQUEST, RESPONSE, TOOL) must be logged via `add_log()`.
- **Reasoning Isolation**: Internal reasoning must NEVER clutter the chat bubbles; it belongs in the Log Panel.
