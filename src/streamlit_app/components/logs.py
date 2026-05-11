import streamlit as st

def render_log_panel():
    st.markdown("### 📝 Live Logs")
    st.markdown("---")
    
    # Custom CSS for Log Badges
    st.markdown("""
        <style>
        .log-badge {
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.65rem;
            font-weight: bold;
            text-transform: uppercase;
            margin-right: 8px;
        }
        .badge-REQUEST { background-color: #38bdf822; color: #38bdf8; border: 1px solid #38bdf844; }
        .badge-RESPONSE { background-color: #10b98122; color: #10b981; border: 1px solid #10b98144; }
        .badge-TOOL { background-color: #f59e0b22; color: #f59e0b; border: 1px solid #f59e0b44; }
        .badge-ERROR { background-color: #ef444422; color: #ef4444; border: 1px solid #ef444444; }
        
        .thinking-log {
            background-color: #1e1b4b;
            padding: 10px;
            border-radius: 4px;
            border-left: 3px solid #6366f1;
            margin-top: 10px;
            font-size: 0.75rem;
            color: #c7d2fe;
            font-family: 'JetBrains Mono', monospace;
        }
        </style>
    """, unsafe_allow_html=True)

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
