import streamlit as st

def render_log_panel():
    """
    Renders the live logs panel in the Streamlit interface.
    
    Iterates through the session state logs in reverse order (newest first)
    and displays them in expandable sections with appropriate badges and
    reasoning blocks.
    """
    st.markdown("### 📝 Live Logs")
    st.markdown("---")
 
    # Log container
    for log in reversed(st.session_state.logs):
        badge_html = f'<span class="log-badge badge-{log["type"]}">{log["type"]}</span>'
        
        with st.expander(f"{log['time']} {log['type']}", expanded=False):
            # Header with Badge
            st.markdown(f"{badge_html} **{log['type']}** at {log['time']}", unsafe_allow_html=True)
            
            # Show Reasoning if available (Critical parity feature)
            if log['type'] == 'RESPONSE' and isinstance(log['data'], dict) and log['data'].get('thinking'):
                st.markdown(f'<div class="thinking-log">🧠 <b>REASONING:</b><br>{log["data"]["thinking"]}</div>', unsafe_allow_html=True)
            
            # Main Data
            st.json(log['data'])
