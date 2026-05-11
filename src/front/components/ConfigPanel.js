class ConfigPanel extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.models = [];
        this.availableTools = [];
    }

    setModels(models) {
        this.models = Array.isArray(models) ? models : [];
        this.render();
    }

    setTools(tools) {
        this.availableTools = Array.isArray(tools) ? tools : [];
        this.render();
    }

    connectedCallback() {
        this.render();
    }

    render() {
        const styles = `
            :host {
                display: flex;
                flex-direction: column;
                height: 100%;
                background: #111827;
                border-right: 1px solid #1f2937;
                width: 300px;
            }
            .header { padding: 1.5rem; border-bottom: 1px solid #1f2937; }
            h2 { font-size: 0.875rem; text-transform: uppercase; letter-spacing: 0.05em; color: #9ca3af; margin: 0; }
            .content { padding: 1.5rem; display: flex; flex-direction: column; gap: 1.5rem; }
            .group { display: flex; flex-direction: column; gap: 0.5rem; }
            label { font-size: 0.75rem; font-weight: 600; color: #9ca3af; }
            select, button {
                background: #1f2937;
                color: #e5e7eb;
                border: 1px solid #374151;
                border-radius: 6px;
                padding: 0.5rem;
                font-family: inherit;
                outline: none;
                cursor: pointer;
            }
            button.secondary { background: #374151; width: 100%; font-weight: 600; margin-top: 0.5rem; }
            button.secondary:hover { background: #4b5563; }
        `;

        this.shadowRoot.innerHTML = `
            <style>${styles}</style>
            <div class="header"><h2>Configuration</h2></div>
            <div class="content">
                <div class="group">
                    <label>Model</label>
                    <select id="model-select">
                        ${this.models.map(m => `<option value="${m.name}">${m.name}</option>`).join('') || '<option>Loading models...</option>'}
                    </select>
                </div>
                <div class="group">
                    <label>Master Prompt Preset</label>
                    <select id="preset-select">
                        <option value="default">Helpful Assistant</option>
                        <option value="vulnerable">Vulnerable Agent</option>
                        <option value="strict">Strict Security Guard</option>
                    </select>
                </div>
                <div class="group">
                    <label>Prompt Injection Attacks</label>
                    <select id="attack-select">
                        <option value="">Select an attack...</option>
                        <option value="ignore">Ignore Instructions</option>
                        <option value="dan">DAN (Do Anything Now)</option>
                        <option value="payload-split">Payload Splitting</option>
                        <option value="indirect">Indirect Injection (Scraped)</option>
                    </select>
                </div>
                <div class="group">
                    <label>Enabled Tools</label>
                    <div id="tools-list" style="display: flex; flex-direction: column; gap: 0.5rem;">
                        ${this.availableTools.map(t => `
                            <label style="display: flex; align-items: center; gap: 0.5rem; font-size: 0.75rem; cursor: pointer;">
                                <input type="checkbox" class="tool-checkbox" value="${t.function.name}" checked>
                                ${t.function.name}
                            </label>
                        `).join('') || '<div style="font-size: 0.75rem; color: #6b7280;">No tools available</div>'}
                    </div>
                </div>
                <div class="group">
                    <label>Scenarios</label>
                    <button id="test-btn" class="secondary">Run Security Suite</button>
                </div>
            </div>
        `;

        this.shadowRoot.getElementById('model-select').addEventListener('change', (e) => {
            this.dispatchEvent(new CustomEvent('model-change', { detail: e.target.value }));
        });
        this.shadowRoot.getElementById('preset-select').addEventListener('change', (e) => {
            this.dispatchEvent(new CustomEvent('preset-change', { detail: e.target.value }));
        });
        this.shadowRoot.getElementById('attack-select').addEventListener('change', (e) => {
            this.dispatchEvent(new CustomEvent('attack-change', { detail: e.target.value }));
        });
    }

    getSelectedToolNames() {
        const checkboxes = this.shadowRoot.querySelectorAll('.tool-checkbox');
        return Array.from(checkboxes).filter(cb => cb.checked).map(cb => cb.value);
    }
}

customElements.define('config-panel', ConfigPanel);
