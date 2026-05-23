"""
Isolated Streamlit AppTest helper wrappers for Presets component testing.

High level role: Contains isolated functions called by AppTest context to test rendering
of attack presets, tool selections, and presets synchronization in sidebar.
"""


def run_attack_presets_selectbox():
    """Wrapper function to render the attack presets component.

    High level role: Provides an isolated Streamlit context to render and test
    the sidebar's category-based attack presets component.

    Args:
        None

    Returns:
        None: Renders directly to the Streamlit app testing context.

    Raises:
        None

    Examples:
        >>> run_attack_presets_selectbox()
    """
    import streamlit as st

    from streamlit_app.components.sidebar import _render_attack_presets
    with st.sidebar:
        selected = _render_attack_presets()
    st.write(f"Selected: {selected}")


def run_tool_selection():
    """Wrapper function to render the tool selection component in tests.

    High level role: Provides an isolated Streamlit context to render the tool selection list.
    Description: Integrates sidebar and renders the tool checkboxes, printing the result list.
    How it works:
    - Renders the _render_tool_selection component in sidebar.
    - Prints the selected tools as markdown text.

    Args:
        None

    Returns:
        None

    Raises:
        None

    Examples:
        >>> run_tool_selection()
    """
    import streamlit as st

    from streamlit_app.components.sidebar import _render_tool_selection
    with st.sidebar:
        selected, _ = _render_tool_selection()
    st.write(f"Selected: {', '.join(selected)}")


def run_presets_and_tools():
    """Wrapper function to render both system presets and tool selections in tests.

    High level role: Renders both system presets and tool selections.

    Arguments:
        None

    Returns:
        None

    Examples:
        >>> run_presets_and_tools()
    """
    import streamlit as st

    from streamlit_app.components.sidebar import _render_system_presets, _render_tool_selection

    with st.sidebar:
        prompt = _render_system_presets()
        selected, _ = _render_tool_selection()

    st.write(f"Prompt: {prompt}")
    st.write(f"Selected: {', '.join(selected)}")
