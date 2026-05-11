class LogPanel extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.logs = [];
    }

    connectedCallback() {
        this.render();
    }

    addLog(type, data) {
        const time = new Date().toLocaleTimeString();
        this.logs.push({ time, type, data });
        this.render();
        this.scrollToBottom();
    }

    scrollToBottom() {
        const content = this.shadowRoot.querySelector('.content');
        if (content) {
            content.scrollTop = content.scrollHeight;
        }
    }

    clear() {
        this.logs = [];
        this.render();
    }

    render() {
        const styles = `
            :host { 
                display: flex; 
                flex-direction: column; 
                height: 100%; 
                background: #0b0f1a; 
                border-left: 1px solid #1f2937;
                min-width: 350px;
                max-width: 450px;
            }
            .header { 
                padding: 1.25rem; 
                border-bottom: 1px solid #1f2937; 
                font-size: 0.875rem; 
                font-weight: 600; 
                color: #e5e7eb; 
                background: #111827;
            }
            .content { 
                flex: 1; 
                overflow-y: auto; 
                padding: 1rem; 
                display: flex; 
                flex-direction: column; 
                gap: 1rem; 
                scrollbar-width: thin;
                scrollbar-color: #374151 transparent;
            }
            .log-entry { 
                font-size: 0.75rem; 
                border-radius: 8px; 
                border: 1px solid #1f2937; 
                overflow: hidden; 
                background: #0f172a;
            }
            .log-header { 
                padding: 0.6rem 0.8rem; 
                background: #1e293b; 
                display: flex; 
                justify-content: space-between; 
                align-items: center; 
            }
            .log-type { 
                font-weight: 700; 
                padding: 0.2rem 0.5rem; 
                border-radius: 4px; 
                font-size: 0.65rem; 
                text-transform: uppercase;
            }
            .type-REQUEST { color: #38bdf8; border: 1px solid #38bdf822; background: #38bdf811; }
            .type-RESPONSE { color: #10b981; border: 1px solid #10b98122; background: #10b98111; }
            .type-ERROR { color: #ef4444; border: 1px solid #ef444422; background: #ef444411; }
            .type-TOOL { color: #f59e0b; border: 1px solid #f59e0b22; background: #f59e0b11; }
            .log-time { color: #9ca3af; font-size: 0.65rem; opacity: 0.7; }
            pre { 
                padding: 1rem; 
                margin: 0; 
                white-space: pre-wrap; 
                word-break: break-all; 
                color: #cbd5e1; 
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.75rem; 
                line-height: 1.5;
            }
            .thinking-process { 
                background: #1e1b4b; 
                border-top: 1px solid #312e81; 
                padding: 1rem; 
            }
            .thinking-label { 
                color: #a5b4fc; 
                font-size: 0.7rem; 
                font-weight: 700; 
                margin-bottom: 0.75rem; 
                display: flex; 
                align-items: center; 
                gap: 0.5rem; 
            }
            .empty { color: #64748b; font-style: italic; text-align: center; margin-top: 3rem; font-size: 0.875rem; }
        `;

        this.shadowRoot.innerHTML = `
            <style>${styles}</style>
            <div class="header">Logs & Observability</div>
            <div class="content">
                ${this.logs.length === 0 ? '<div class="empty">No activity yet...</div>' : ''}
                ${this.logs.map(log => {
                    const dataStr = JSON.stringify(log.data, null, 2);
                    let thinkingHtml = '';
                    
                    if (log.type === 'RESPONSE' && log.data?.message?.thinking) {
                        thinkingHtml = `
                            <div class="thinking-process">
                                <div class="thinking-label">🧠 INTERNAL REASONING</div>
                                <pre>${log.data.message.thinking}</pre>
                            </div>
                        `;
                    }
                    
                    return `
                    <div class="log-entry">
                        <div class="log-header">
                            <span class="log-type type-${log.type}">${log.type}</span>
                            <span class="log-time">${log.time}</span>
                        </div>
                        <pre>${dataStr}</pre>
                        ${thinkingHtml}
                    </div>
                    `;
                }).join('')}
            </div>
        `;
    }
}

customElements.define('log-panel', LogPanel);
