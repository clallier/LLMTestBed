"""
Observability and log parsing handler for Streamlit trace visualizations.

High level role: Manages session index selections, parses activity traces,
and formats safety status summaries and JSON export structures.
"""

import json
from typing import Any, Dict, Tuple

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

    def format_export_payload(self, log: Dict[str, Any]) -> str:
        """
        Compiles and serializes trace log details into a printable JSON export string.

        High level role: Prepares clean diagnostic export deliverables.

        Arguments:
            log (Dict[str, Any]): Telemetry trace log containing 'time', 'type', and 'data'.

        Returns:
            str: Prettified JSON payload string.
        """
        payload = {
            "timestamp": log.get("time", ""),
            "type": log.get("type", ""),
            "data": log.get("data", {})
        }
        return json.dumps(payload, indent=self._JSON_INDENT)

    def get_security_status(
        self,
        security_data: Dict[str, Any]
    ) -> Tuple[float, str, str]:
        """
        Evaluates risk telemetry scores and generates matching UI status variables.

        High level role: Translates raw risk floats into semantic CSS colors and badges.

        Arguments:
            security_data (Dict[str, Any]): Bayesian guardrail metrics.

        Returns:
            Tuple[float, str, str]: A tuple of (risk_score_percent, summary_label, badge_color).
        """
        score = security_data.get("risk_score", 0.0)
        summary = security_data.get("summary", "No details")

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
