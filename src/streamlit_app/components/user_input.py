"""
User input component wrapping Streamlit's native multimodal chat input.

High level role: Renders st.chat_input with native file upload capabilities, processes
image attachments (encoding to base64), and handles session state updates on user submission.
"""

from typing import Any

import streamlit as st

from streamlit_app.components.processors.chat import ChatProcessor


class UserInputComponent:
    """
    Component for rendering and processing the multimodal user prompt input.

    High level role: Encapsulates state and rendering behavior for the user chat input,
    handling image extraction, base64 encoding, and message history updates.
    """

    def render(self) -> None:
        """
        Renders the native multimodal st.chat_input and updates chat history on submit.

        High level role: Renders st.chat_input with file uploading active, extracts the text
        and images, appends a new user message to session state, and triggers a rerun.

        Arguments:
            None

        Returns:
            None

        Potential Errors:
            None

        Examples:
            >>> ui = UserInputComponent()
            >>> ui.render()
        """
        prompt = st.chat_input(
            "Type here and press Enter to attack...",
            accept_file=True,
            file_type=["png", "jpg", "jpeg"],
            key="chat_multimodal_input",
        )
        if prompt is not None:
            text = prompt.text if prompt.text else ""
            user_message: dict[str, Any] = {"role": "user", "content": text}

            if prompt.files:
                uploaded_image = prompt.files[0]
                base64_img = ChatProcessor.encode_image_to_base64(uploaded_image)
                user_message["images"] = [base64_img]

            st.session_state.messages.append(user_message)
            st.session_state.raw_messages.append(user_message)
            st.session_state.is_processing = True
            st.rerun()
