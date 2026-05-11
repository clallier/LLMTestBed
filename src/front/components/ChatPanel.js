class ChatPanel extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.messages = [];
        this.systemPrompt = "You are a helpful AI assistant.";
    }

    connectedCallback() {
        this.render();
    }

    addMessage(role, content) {
        this.messages.push({ role, content });
        this.render();
        this.scrollToBottom();
    }

    appendToLastMessage(content) {
        if (this.messages.length > 0) {
            this.messages[this.messages.length - 1].content += content;
            this.render();
            this.scrollToBottom();
        }
    }

    scrollToBottom() {
        const container = this.shadowRoot.getElementById('chat-container');
        if (container) container.scrollTop = container.scrollHeight;
    }

    clear() {
        this.messages = [];
        this.render();
    }

    setSystemPrompt(text) {
        this.systemPrompt = text;
        this.render();
    }

    setUserInput(text) {
        const el = this.shadowRoot.getElementById('user-input');
        if (el) {
            el.value = text;
            el.style.height = 'auto';
            el.style.height = el.scrollHeight + 'px';
        }
    }

    render() {
        const styles = `
            :host { display: flex; flex-direction: column; flex: 1; background: #0b0f1a; min-width: 0; }
            header { padding: 1.5rem; border-bottom: 1px solid #1f2937; }
            .section-label { display: flex; justify-content: space-between; align-items: center; font-size: 0.75rem; font-weight: 600; color: #9ca3af; margin-bottom: 0.75rem; }
            textarea { background: #1f2937; color: #e5e7eb; border: 1px solid #1f2937; border-radius: 8px; padding: 0.75rem; font-family: inherit; font-size: 0.875rem; resize: none; width: 100%; box-sizing: border-box; }
            #system-prompt { height: 100px; }
            #chat-container { flex: 1; overflow-y: auto; padding: 1.5rem; display: flex; flex-direction: column; gap: 1.5rem; }
            .message { padding: 1rem; border-radius: 12px; font-size: 0.9375rem; line-height: 1.6; max-width: 85%; }
            .user { background: #38bdf8; color: #000; align-self: flex-end; }
            .assistant { background: #1f2937; color: #e5e7eb; align-self: flex-start; border: 1px solid #1f2937; }
            .input-area { padding: 1.5rem; border-top: 1px solid #1f2937; background: #0f172a; }
            .input-wrapper { max-width: 900px; margin: 0 auto; display: flex; flex-direction: column; gap: 0.75rem; background: #1f2937; padding: 1rem; border-radius: 12px; border: 1px solid #374151; }
            #user-input { background: transparent; border: none; flex: 1; min-height: 120px; max-height: 400px; padding: 0.5rem; color: #e5e7eb; font-family: 'JetBrains Mono', monospace; font-size: 0.875rem; line-height: 1.5; outline: none; }
            .input-footer { display: flex; justify-content: flex-end; align-items: center; gap: 1rem; margin-top: 0.5rem; }
            button { background: #38bdf8; color: #000; border: none; border-radius: 6px; padding: 0.6rem 1.5rem; font-weight: 600; cursor: pointer; transition: all 0.2s; }
            button:hover { background: #7dd3fc; transform: translateY(-1px); }
            .danger { background: transparent; color: #ef4444; border: 1px solid #ef4444; padding: 0.25rem 0.75rem; font-size: 0.75rem; }
        `;

        this.shadowRoot.innerHTML = `
            <style>${styles}</style>
            <header>
                <div class="section-label">
                    <span>System Prompt</span>
                    <button id="reset-btn" class="danger">Reset Memory</button>
                </div>
                <textarea id="system-prompt">${this.systemPrompt}</textarea>
            </header>
            <div id="chat-container">
                ${this.messages.map(m => `<div class="message ${m.role}">${m.content}</div>`).join('')}
            </div>
            <div class="input-area">
                <div class="input-wrapper">
                    <textarea id="user-input" placeholder="Type your prompt here..." rows="1"></textarea>
                    <div class="input-footer">
                        <span style="font-size: 0.7rem; color: #6b7280;">Shift+Enter for new line</span>
                        <button id="send-btn">Send</button>
                    </div>
                </div>
            </div>
        `;

        this.shadowRoot.getElementById('send-btn').addEventListener('click', () => this.handleSend());
        this.shadowRoot.getElementById('reset-btn').addEventListener('click', () => this.dispatchEvent(new CustomEvent('reset')));
        this.shadowRoot.getElementById('system-prompt').addEventListener('input', (e) => {
            this.systemPrompt = e.target.value;
        });
        const userInput = this.shadowRoot.getElementById('user-input');
        
        userInput.addEventListener('input', (e) => {
            e.target.style.height = 'auto';
            e.target.style.height = (e.target.scrollHeight) + 'px';
        });

        userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleSend();
            }
        });
    }

    handleSend() {
        const input = this.shadowRoot.getElementById('user-input');
        const text = input.value.trim();
        if (!text) return;
        
        this.dispatchEvent(new CustomEvent('send', {
            detail: {
                userPrompt: text,
                systemPrompt: this.shadowRoot.getElementById('system-prompt').value
            }
        }));
        input.value = '';
        input.style.height = 'auto';
    }
}

customElements.define('chat-panel', ChatPanel);
