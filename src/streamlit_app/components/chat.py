import streamlit as st
import httpx
import json
import time

BACKEND_URL = "http://localhost:8000"

def add_log(type, data):
    st.session_state.logs.append({
        "time": time.strftime("%H:%M:%S"),
        "type": type,
        "data": data
    })

def render_chat_interface(selected_model, system_prompt, selected_tool_names, available_tools):
    st.header("🕵️ Agent Attack Sandbox")
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Handle processing
    if st.session_state.is_processing and st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        process_assistant_response(selected_model, system_prompt, selected_tool_names, available_tools)

    # Custom Non-Floating Input (Embedded at bottom of discussion)
    st.markdown("---")
    
    def on_input_submit():
        if st.session_state.input_field:
            st.session_state.messages.append({"role": "user", "content": st.session_state.input_field})
            st.session_state.is_processing = True
            st.session_state.input_field = "" # Clear after submit

    st.text_input(
        "Enter payload...", 
        key="input_field", 
        on_change=on_input_submit,
        placeholder="Type here and press Enter to attack...",
        disabled=st.session_state.is_processing,
        label_visibility="collapsed"
    )

def process_assistant_response(selected_model, system_prompt, selected_tool_names, available_tools):
    with st.chat_message("assistant"):
        # Hidden marker that triggers the CSS pulse animation on the avatar
        st.markdown('<div class="is-thinking"></div>', unsafe_allow_html=True)
        message_placeholder = st.empty()
        
        full_response = ""
        thinking_content = ""
        
        # Prepare Payload
        tools = [t for t in available_tools if t["function"]["name"] in selected_tool_names] if available_tools else []
        payload = {
            "model": selected_model,
            "messages": st.session_state.messages,
            "system": system_prompt,
            "stream": True,
            "tools": tools if tools else None
        }
        add_log("REQUEST", payload)

        try:
            with httpx.stream("POST", f"{BACKEND_URL}/chat", json=payload, timeout=120.0) as r:
                content_type = r.headers.get("content-type", "")
                
                if "application/json" in content_type:
                    data = r.json()
                    full_response = data["message"]["content"]
                    thinking_content = data["message"].get("thinking", "")
                    add_log("RESPONSE", data)
                else:
                    for line in r.iter_lines():
                        if line:
                            data = json.loads(line)
                            if "message" in data:
                                if "content" in data["message"]:
                                    full_response += data["message"]["content"]
                                    # Regular streaming (no HTML here!)
                                    message_placeholder.markdown(full_response + "▌")
                                if "thinking" in data["message"]:
                                    thinking_content += data["message"]["thinking"]
                            if "message" in data and "tool_calls" in data["message"]:
                                add_log("TOOL", data["message"]["tool_calls"])
                    add_log("RESPONSE", {"content": full_response, "thinking": thinking_content})

                # Final render (Clears the marker and the cursor)
                message_placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
        except Exception as e:
            st.error(f"Error: {e}")
            add_log("ERROR", {"message": str(e)})
        
        st.session_state.is_processing = False
        st.rerun()
