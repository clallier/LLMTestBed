"""
Observability and log parsing handler for Streamlit trace visualizations.

High level role: Manages session index selections, parses activity traces,
and formats safety status summaries and JSON export structures.
"""

import json
from typing import Any, Dict, List, Tuple

import streamlit as st


class ObservabilityProcessor:
    """
    Orchestrates trace navigation states, telemetry metrics, and export data structures.

    High level role: Provides raw telemetry formatters and handles session selection logic.
    """

    # Internal Constants
    _JSON_INDENT: int = 2

    # ==========================================
    # Public API
    # ==========================================

    def initialize_selection_state(self, logs_length: int):
        """
        Initializes or resets the active trace selection index in session state.

        High level role: Keeps selection boundaries aligned with trace changes.

        Arguments:
            logs_length (int): Total count of logged items.

        Returns:
            None
        """
        if "selected_log_index" not in st.session_state:
            st.session_state.selected_log_index = logs_length - 1
        elif st.session_state.selected_log_index >= logs_length:
            st.session_state.selected_log_index = logs_length - 1

    def select_log(self, index: int):
        """
        Updates the active selected log index and triggers a page rerun.

        High level role: Synchronizes Master-Detail view selections.

        Arguments:
            index (int): Target log index to select.

        Returns:
            None
        """
        st.session_state.selected_log_index = index
        st.rerun()

    def format_export_payload(self, raw_messages: List[Dict[str, Any]]) -> str:
        """
        Compiles and serializes the complete conversation history into a printable JSON export string.

        High level role: Prepares clean diagnostic export deliverables containing all turns.

        Arguments:
            raw_messages (List[Dict[str, Any]]): The raw message turns containing tool calls and content.

        Returns:
            str: Prettified JSON payload string.
        """
        payload = {"conversation_history": raw_messages}
        return json.dumps(payload, indent=self._JSON_INDENT)

    def get_security_status(self, security_data: Dict[str, Any]) -> Tuple[float, str, str]:
        """
        Evaluates risk telemetry scores and generates matching UI status variables.

        High level role: Translates raw risk floats into semantic CSS colors and badges.
        Description: Takes security log data, extracts the risk score and target/summary,
        and computes the percentage, status label, and corresponding Streamlit CSS color badge.
        How it works:
        - If 'summary' is present in the payload (backward compatibility), it uses it.
        - Otherwise, it dynamically determines the status label based on target and risk score.
        - Translates the final label into green, red, or orange badges based on safety checks.

        Args:
            security_data (Dict[str, Any]): Bayesian guardrail metrics dictionary containing
                'risk_score' (float), optionally 'target' (str), and optionally 'summary' (str)
                or 'value' (str).

        Returns:
            Tuple[float, str, str]: A tuple containing:
                1. risk_score_percent (float): Risk score scaled to 0-100.
                2. summary_label (str): Textual safety summary of the assessed target.
                3. badge_color (str): Streamlit semantic color name ('green', 'red', or 'orange').

        Raises:
            KeyError: This method does not raise any key errors and safely falls back to defaults.

        Examples:
            >>> processor = ObservabilityProcessor()
            >>> processor.get_security_status({"risk_score": 0.15})
            (15.0, 'Safe', 'green')
        """
        score = security_data.get("risk_score", 0.0)
        target = security_data.get("target", "unknown")

        # Try getting summary directly for backward compatibility
        summary = security_data.get("summary")
        if summary is None:
            # Generate a semantic status label based on the risk score and target
            if score > 0.8:
                summary = "High risk prompt" if target == "user_prompt" else "High risk tool output"
            elif score > 0.5:
                summary = "Medium Risk"
            else:
                summary = "Safe"

        summary_clean = summary.lower()
        if "safe" in summary_clean:
            badge_color = "green"
        elif "risk" in summary_clean or score > 0.5:
            badge_color = "red"
        else:
            badge_color = "orange"

        return score * 100.0, summary, badge_color

    def format_tool_arguments(self, arguments: Any) -> str:
        """
        Safely converts raw tool invocation arguments into a prettified JSON string block.

        High level role: Normalizes dynamic types for consistent display rendering.

        Arguments:
            arguments (Any): Arguments payload, typically dict or string.

        Returns:
            str: Prettified JSON block or raw string.
        """
        if isinstance(arguments, dict):
            return json.dumps(arguments, indent=self._JSON_INDENT)
        return str(arguments)
