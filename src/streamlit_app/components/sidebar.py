"""
Streamlit Sidebar Configuration Component.

High level role: Renders model selectors, system prompt presets, and mock tools checklists.
"""

from typing import Any, Dict, List, Tuple

import streamlit as st

from streamlit_app.api.client import fetch_models, fetch_tools
from streamlit_app.presets.attacks import ATTACK_TEMPLATES, FLAT_ATTACK_TEMPLATES
from streamlit_app.presets.system import SYSTEM_PRESETS


def render_sidebar() -> Tuple[str, str, List[str], List[Dict[str, Any]], str]:
    """Renders the sidebar and returns the selected configuration."""
    with st.sidebar:
        # Official branding logo
        st.logo(
            "src/streamlit_app/assets/logo_text.png",
            icon_image="src/streamlit_app/assets/logo.png",
            size="large",
        )

        # Configuration controls (Model, Tools, etc.)
        selected_model = _render_model_selection()
        system_prompt = _render_system_presets()
        selected_tool_names, available_tools = _render_tool_selection()
        selected_attack = _render_attack_presets()

        st.markdown("---")
        if st.button("Clear History", type="secondary", use_container_width=True):
            st.session_state.messages = []
            st.session_state.raw_messages = []
            st.session_state.logs = []
            st.rerun()

        return selected_model, system_prompt, selected_tool_names, available_tools, selected_attack


def _render_model_selection() -> str:
    """Fetches and renders the model selection dropdown."""
    models = fetch_models()
    model_names = []
    if isinstance(models, list):
        model_names = [m.get("name", m) if isinstance(m, dict) else m for m in models]

    if not model_names:
        model_names = ["No model available. Please run 'ollama serve' first."]

    return st.selectbox("Select Model", model_names)


def _render_system_presets() -> str:
    """Renders system prompt presets dropdown and an editable text area.

    High level role: Renders system prompt presets dropdown and an editable text area.
    Description: Integrates with system prompt presets to preselect tool states and
    populate default system prompts inside the text area workspace.
    How it works:
    - Renders selectbox of preset keys.
    - Compares current selection against stored session state to detect changes.
    - If a preset changes, programmatically resets and populates the checkbox session states.
    - Renders and returns the updated text_area prompt content.

    Args:
        None

    Returns:
        str: Currently input or edited system prompt content.

    Raises:
        None

    Examples:
        >>> prompt = _render_system_presets()
    """
    if "current_preset" not in st.session_state:
        st.session_state.current_preset = None

    selected_preset = st.selectbox("System Preset", list(SYSTEM_PRESETS.keys()))
    preset_data = SYSTEM_PRESETS[selected_preset]

    if st.session_state.current_preset != selected_preset:
        st.session_state.current_preset = selected_preset
        _update_preset_tools(preset_data.get("selected_tools", []))

    return st.text_area(
        "System Prompt",
        preset_data["system_prompt"],
        height=120,
        label_visibility="collapsed",
    )


def _update_preset_tools(selected_tools: str | List[str]) -> None:
    """Updates session state tool selections to match the active system preset.

    High level role: Updates system state tool checks.
    Description: Iterates through all available system tools, setting selected
    tools to True and others to False in both widget key and cache states.
    How it works:
    - Converts input string to a list of strings if a single tool is passed.
    - Fetches the available tools to ensure full coverage.
    - Configures session state tool_selections dictionary and widget keys.

    Args:
        selected_tools (str | List[str]): A tool name or list of tool names preselected by the preset.

    Returns:
        None

    Raises:
        None

    Examples:
        >>> _update_preset_tools("list_users")
    """
    if "tool_selections" not in st.session_state:
        st.session_state.tool_selections = {}

    tools_list = [selected_tools] if isinstance(selected_tools, str) else selected_tools
    available_tools = fetch_tools()

    if available_tools:
        for tool in available_tools:
            name = tool["function"]["name"]
            is_active = (name in tools_list)
            st.session_state.tool_selections[name] = is_active
            st.session_state[f"tool_check_{name}"] = is_active


def _build_attack_options() -> List[str]:
    """Builds hierarchical dropdown options from the attack template presets.

    High level role: Hierarchical options builder.
    Description: Converts the nested ATTACK_TEMPLATES dictionary structure into
    a visually structured flat list of dropdown option label strings.
    How it works:
    - Prepends a default placeholder 'None' option.
    - Loops over all template categories to append divider header categories.
    - Indents and appends individual template keys beneath their categories.

    Args:
        None

    Returns:
        List[str]: A list of options formatted for selection inputs.

    Raises:
        None

    Examples:
        >>> options = _build_attack_options()
    """
    options = ["None"]
    for category, templates in ATTACK_TEMPLATES.items():
        options.append(f"── {category} ──")
        for template in templates:
            options.append(f"   {template}")
    return options


def _inject_payload(attack_name: str) -> None:
    """Injects the selected attack template payload into user chat message history.

    High level role: Chat history payload injector.
    Description: Resolves flat template payload names, appends active and raw
    chat records to the session state, and sets state to processing.
    How it works:
    - Retreives flat attack template by name.
    - Appends payload to messages and raw_messages.
    - Sets is_processing to True and triggers st.rerun().

    Args:
        attack_name (str): The specific name of the attack template to inject.

    Returns:
        None

    Raises:
        KeyError: If the provided attack template name does not exist.

    Examples:
        >>> _inject_payload("Schema based request")
    """
    payload_content = FLAT_ATTACK_TEMPLATES[attack_name]
    st.session_state.setdefault("messages", []).append(
        {"role": "user", "content": payload_content}
    )
    st.session_state.setdefault("raw_messages", []).append(
        {"role": "user", "content": payload_content}
    )
    st.session_state.is_processing = True
    st.rerun()


def _render_attack_presets() -> str:
    """Renders a single hierarchical dropdown for selecting attack templates.

    High level role: Renders a single selectbox where attack templates are grouped
    under section headers using indentations and visual divider marks. If a header
    is selected, it acts as a null selection. Renders the 'Inject Payload' button
    directly under the selectbox if an attack is selected.

    Args:
        None

    Returns:
        str: The key of the selected attack template (with leading whitespace stripped),
            or "None" if a header or "None" is selected.

    Raises:
        None

    Examples:
        >>> selected_attack = _render_attack_presets()
    """
    st.markdown("### 🏹 Attack Templates")
    options = _build_attack_options()
    selected_option = st.selectbox("Load Attack", options)
    selected_attack = "None"
    if selected_option.startswith("   "):
        selected_attack = selected_option.strip()

    if selected_attack != "None":
        if st.button("Inject Payload", type="primary", use_container_width=True):
            _inject_payload(selected_attack)

    return selected_attack


def _render_tool_selection() -> Tuple[List[str], List[Dict[str, Any]]]:
    """Fetches and renders the tool selection checkboxes with persistent state.

    High level role: Renders checkbox widgets to select which mock tools are enabled.
    Description: Fetches available tools from the backend, initializes and retrieves
    persistent checkbox states from st.session_state, and returns the active tool selections.
    How it works:
    - Queries the backend tools registry.
    - Initializes the custom 'tool_selections' persistent dictionary in session state.
    - Iterates over available tools, rendering checkboxes initialized with saved states.
    - Updates persistent states and returns selected names alongside full tool schemas.

    Args:
        None

    Returns:
        Tuple[List[str], List[Dict[str, Any]]]: List of selected tool names and all available tools.

    Raises:
        None

    Examples:
        >>> selected_names, tools = _render_tool_selection()
    """
    st.markdown("### 🛠️ Mock Tools")
    available_tools = fetch_tools()
    selected_tool_names = []

    if "tool_selections" not in st.session_state:
        st.session_state.tool_selections = {}

    if available_tools:
        for tool in available_tools:
            name = tool["function"]["name"]
            current_val = st.session_state.tool_selections.setdefault(name, True)
            checked = st.checkbox(name, value=current_val, key=f"tool_check_{name}")
            st.session_state.tool_selections[name] = checked
            if checked:
                selected_tool_names.append(name)

    return selected_tool_names, available_tools
