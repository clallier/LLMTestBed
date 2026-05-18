"""
Log parsing and trace recording processor.

High level role: Manages live logs tracing states and session appending.
"""

import time
import streamlit as st
from typing import Any

class LogsProcessor:
    """
    Manages session-state trace logs and handles new trace registrations.

    High level role: Provides static state managers for session telemetry tracking.
    """

    # Internal Constants
    _DEFAULT_TIME_FORMAT: str = "%H:%M:%S"

    # ==========================================
    # Public API
    # ==========================================

    @staticmethod
    def add_log(log_type: str, data: Any):
        """
        Appends a trace log entry to the session state logs with a timestamp.

        High level role: Records an event in session state for later Trace Explorer analysis.

        Arguments:
            log_type (str): Type of trace log (e.g., REQUEST, RESPONSE, SECURITY).
            data (Any): Payload data associated with the trace event.

        Returns:
            None
        """
        if "logs" not in st.session_state:
            st.session_state.logs = []
        st.session_state.logs.append({
            "time": time.strftime(LogsProcessor._DEFAULT_TIME_FORMAT),
            "type": log_type,
            "data": data
        })

# Module-level export for seamless functional imports
add_log = LogsProcessor.add_log
