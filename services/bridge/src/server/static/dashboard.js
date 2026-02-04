// Dashboard State
let requestLogs = [];
let chatMessages = [];
let isStreaming = false;
let authRequired = false;

// API helpers - compute base path to support sub-path deployments
const basePath = window.location.pathname.replace(/\/dashboard\/?$/, '');
const apiBase = window.location.origin + basePath;

async function apiFetch(endpoint, options = {}) {
    const apiKey = document.getElementById('api-key').value;
    if (apiKey) {
        options.headers = { ...options.headers, 'Authorization': `Bearer ${apiKey}` };
    }
    const response = await fetch(`${apiBase}${endpoint}`, options);

    // Check for auth failure
    if (response.status === 401) {
        authRequired = true;
        updateAuthState();
        throw new Error('Authentication required');
    }

    authRequired = false;
    updateAuthState();
    return response.json();
}

function updateAuthState() {
    const lockedEls = document.querySelectorAll('.auth-locked');
    const apiKeyInput = document.getElementById('api-key');

    if (authRequired && !apiKeyInput.value) {
        lockedEls.forEach(el => el.classList.remove('hidden'));
        document.getElementById('health-status').innerHTML = '<div class="text-dark-muted text-sm">🔒 Enter API key to view</div>';
        document.getElementById('provider-metrics').innerHTML = '<div class="text-dark-muted text-sm">🔒 Enter API key to view</div>';
        document.getElementById('stat-total').textContent = '🔒';
        document.getElementById('stat-success').textContent = '🔒';
        document.getElementById('stat-tokens').textContent = '🔒';
        document.getElementById('stat-uptime').textContent = '🔒';
    } else {
        lockedEls.forEach(el => el.classList.add('hidden'));
    }
}

// Format helpers
function formatDuration(seconds) {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    return `${Math.round(seconds / 3600)}h`;
}

function formatTime(date) {
    return date.toLocaleTimeString('en-US', { hour12: false });
}

function formatNumber(num) {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
}

// Update status indicator
function updateStatus(connected) {
    const el = document.getElementById('status-indicator');
    if (connected) {
        el.innerHTML = `<span class="w-2 h-2 rounded-full bg-green-500"></span><span class="text-sm text-dark-muted">Connected</span>`;
    } else {
        el.innerHTML = `<span class="w-2 h-2 rounded-full bg-red-500"></span><span class="text-sm text-dark-muted">Disconnected</span>`;
    }
}

// Fetch and display health
async function fetchHealth() {
    try {
        const data = await apiFetch('/health');
        const container = document.getElementById('health-status');

        let html = '';
        for (const [name, info] of Object.entries(data.providers || {})) {
            const statusClass = info.available ? 'bg-green-500' : 'bg-red-500';
            const statusText = info.available ? info.version || 'Available' : info.error || 'Unavailable';
            html += `
                <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2">
                        <span class="w-2 h-2 rounded-full ${statusClass}"></span>
                        <span class="font-medium">${name}</span>
                    </div>
                    <span class="text-sm text-dark-muted">${statusText}</span>
                </div>
            `;
        }
        container.innerHTML = html || '<div class="text-dark-muted text-sm">No providers configured</div>';
        updateStatus(true);
    } catch (e) {
        updateStatus(false);
    }
}

// Fetch and display metrics
async function fetchMetrics() {
    try {
        const data = await apiFetch('/metrics');

        // Update stats
        const req = data.requests || {};
        const totalTokens = req.total_tokens || {};
        document.getElementById('stat-total').textContent = req.total_requests || 0;
        document.getElementById('stat-success').textContent = `${(req.overall_success_rate || 0).toFixed(1)}%`;
        document.getElementById('stat-tokens').textContent = formatNumber(totalTokens.total || 0);
        document.getElementById('stat-uptime').textContent = formatDuration(req.uptime_seconds || 0);

        // Update provider metrics
        const container = document.getElementById('provider-metrics');
        let html = '';

        for (const [name, stats] of Object.entries(req.providers || {})) {
            const tokens = stats.tokens || {};
            html += `
                <div class="mb-4 last:mb-0">
                    <div class="flex justify-between items-center mb-2">
                        <span class="font-medium text-white">${name}</span>
                        <span class="text-sm text-dark-muted">${stats.total_requests} requests</span>
                    </div>
                    <div class="grid grid-cols-4 gap-2 text-sm">
                        <div>
                            <div class="text-dark-muted">Success</div>
                            <div class="text-green-400">${stats.success_rate.toFixed(1)}%</div>
                        </div>
                        <div>
                            <div class="text-dark-muted">Avg Time</div>
                            <div>${stats.avg_duration_seconds.toFixed(2)}s</div>
                        </div>
                        <div>
                            <div class="text-dark-muted">Failed</div>
                            <div class="text-red-400">${stats.failed_requests}</div>
                        </div>
                        <div>
                            <div class="text-dark-muted">Tokens</div>
                            <div class="text-purple-400">${formatNumber(tokens.total || 0)}</div>
                        </div>
                    </div>
                    ${Object.keys(stats.models || {}).length > 0 ? `
                        <div class="mt-3 border-t border-dark-border pt-2">
                            <div class="text-xs text-dark-muted mb-2">Per-model breakdown:</div>
                            ${Object.entries(stats.models).map(([model, mstats]) => `
                                <div class="flex justify-between text-xs py-1">
                                    <span class="text-dark-text">${model}</span>
                                    <span class="text-dark-muted">
                                        ${mstats.total_requests} req ·
                                        <span class="text-blue-400">${formatNumber(mstats.tokens?.prompt || 0)}p</span> /
                                        <span class="text-green-400">${formatNumber(mstats.tokens?.completion || 0)}c</span>
                                    </span>
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}
                </div>
            `;
        }

        container.innerHTML = html || '<div class="text-dark-muted text-sm">No metrics yet</div>';
    } catch (e) {
        console.error('Failed to fetch metrics:', e);
    }
}

// Request log functions
function addRequestLog(entry) {
    requestLogs.unshift(entry);
    if (requestLogs.length > 50) requestLogs.pop();
    renderRequestLogs();
}

function renderRequestLogs() {
    const container = document.getElementById('request-log');
    if (requestLogs.length === 0) {
        container.innerHTML = '<div class="text-dark-muted text-sm text-center py-8">No requests yet</div>';
        return;
    }

    container.innerHTML = requestLogs.map(log => `
        <div class="log-entry flex items-center justify-between text-sm py-2 border-b border-dark-border last:border-0">
            <div class="flex items-center gap-2">
                <span class="w-2 h-2 rounded-full ${log.success ? 'bg-green-500' : 'bg-red-500'}"></span>
                <span class="font-mono text-dark-muted">${log.time}</span>
                <span class="text-white">${log.model}</span>
            </div>
            <div class="text-dark-muted">${log.duration}</div>
        </div>
    `).join('');
}

function clearLogs() {
    requestLogs = [];
    renderRequestLogs();
}

function clearChat() {
    chatMessages = [];
    document.getElementById('chat-messages').innerHTML = `
        <div class="text-center text-dark-muted text-sm py-8">
            Send a message to start testing
        </div>
    `;
    document.getElementById('msg-count').classList.add('hidden');
}

async function resetMetrics() {
    await apiFetch('/metrics/reset', { method: 'POST' });
    fetchMetrics();
}

// Chat functions
function addChatMessage(role, content) {
    chatMessages.push({ role, content });
    renderChat();
}

function updateLastMessage(content) {
    if (chatMessages.length > 0) {
        chatMessages[chatMessages.length - 1].content = content;
        renderChat(false);
    }
}

function renderChat(scroll = true) {
    const container = document.getElementById('chat-messages');
    const countEl = document.getElementById('msg-count');

    // Update message count indicator
    if (chatMessages.length > 0) {
        countEl.textContent = `${chatMessages.length} msg${chatMessages.length > 1 ? 's' : ''} in context`;
        countEl.classList.remove('hidden');
    } else {
        countEl.classList.add('hidden');
    }

    container.innerHTML = chatMessages.map(msg => {
        const isUser = msg.role === 'user';
        return `
            <div class="flex ${isUser ? 'justify-end' : 'justify-start'}">
                <div class="${isUser ? 'bg-blue-600' : 'bg-dark-border'} rounded-lg px-4 py-2 max-w-[85%]">
                    <pre class="text-sm whitespace-pre-wrap">${escapeHtml(msg.content)}${msg.role === 'assistant' && isStreaming ? '<span class="typing">|</span>' : ''}</pre>
                </div>
            </div>
        `;
    }).join('');

    if (scroll) {
        container.scrollTop = container.scrollHeight;
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function sendMessage() {
    const input = document.getElementById('user-input');
    const message = input.value.trim();
    if (!message || isStreaming) return;

    const model = document.getElementById('model-select').value;
    const stream = document.getElementById('stream-toggle').checked;
    const systemPrompt = document.getElementById('system-prompt').value.trim();
    const apiKey = document.getElementById('api-key').value;

    // Add user message to history
    addChatMessage('user', message);
    input.value = '';

    // Build messages array with FULL conversation history
    const messages = [];
    if (systemPrompt) {
        messages.push({ role: 'system', content: systemPrompt });
    }
    // Include all previous messages for context
    for (const msg of chatMessages) {
        messages.push({ role: msg.role, content: msg.content });
    }

    const startTime = Date.now();

    // Disable send button
    document.getElementById('send-btn').disabled = true;
    isStreaming = true;

    try {
        if (stream) {
            // Streaming request
            addChatMessage('assistant', '');

            const headers = { 'Content-Type': 'application/json' };
            if (apiKey) headers['Authorization'] = `Bearer ${apiKey}`;

            const response = await fetch(`${apiBase}/v1/chat/completions`, {
                method: 'POST',
                headers,
                body: JSON.stringify({ model, messages, stream: true })
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let fullContent = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ') && line !== 'data: [DONE]') {
                        try {
                            const data = JSON.parse(line.slice(6));
                            const content = data.choices?.[0]?.delta?.content;
                            if (content) {
                                fullContent += content;
                                updateLastMessage(fullContent);
                            }
                        } catch (e) {}
                    }
                }
            }
        } else {
            // Non-streaming request
            addChatMessage('assistant', 'Thinking...');

            const data = await apiFetch('/v1/chat/completions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model, messages, stream: false })
            });

            const content = data.choices?.[0]?.message?.content || 'No response';
            updateLastMessage(content);
        }

        // Log the request
        addRequestLog({
            time: formatTime(new Date()),
            model,
            success: true,
            duration: `${((Date.now() - startTime) / 1000).toFixed(2)}s`
        });

    } catch (e) {
        updateLastMessage(`Error: ${e.message}`);
        addRequestLog({
            time: formatTime(new Date()),
            model,
            success: false,
            duration: `${((Date.now() - startTime) / 1000).toFixed(2)}s`
        });
    } finally {
        document.getElementById('send-btn').disabled = false;
        isStreaming = false;
        renderChat();
    }

    // Refresh metrics
    fetchMetrics();
}

// Refresh all data
function refreshAll() {
    fetchHealth();
    fetchMetrics();
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', function() {
    // Keyboard shortcut for sending messages
    document.getElementById('user-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Refresh data when API key is entered
    document.getElementById('api-key').addEventListener('change', () => {
        refreshAll();
    });

    // Initial data fetch
    refreshAll();

    // Refresh metrics every 10s
    setInterval(fetchMetrics, 10000);
});
