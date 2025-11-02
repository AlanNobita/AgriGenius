console.log("chat.js loaded");

// Character Counter
function updateCharCounter(input) {
    const counter = document.getElementById('charCounter');
    const currentCount = input.value.length;
    const maxCount = 2000;

    // Update counter if present (graceful for production template variations)
    if (counter) {
        const currentEl = counter.querySelector('.current');
        if (currentEl) currentEl.textContent = currentCount;
        counter.classList.toggle('near-limit', currentCount >= maxCount * 0.8);
        counter.classList.toggle('at-limit', currentCount >= maxCount);
    }

    // Auto-resize textarea
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 120) + 'px';

    // Enable/disable send button (guarded)
    const sendBtn = document.getElementById('sendBtn');
    if (sendBtn) sendBtn.disabled = !input.value.trim();
}

// Chat Interface Class
class AgriChatGPT {
    constructor() {
        // Initialize DOM elements
        this.chatMessages = document.getElementById('chat-window');
        this.chatInput = document.getElementById('chat-input');
        this.chatForm = document.getElementById('chat-form');
        this.sendBtn = document.getElementById('send-btn');
        this.welcomeScreen = document.getElementById('welcomeScreen');
        this.conversationsList = document.getElementById('conversation-list');
        this.newChatBtn = document.getElementById('new-chat-btn');
        this.clearAllBtn = document.getElementById('clearAllBtn');
        this.settingsBtn = document.getElementById('settingsBtn');
        this.userName = document.getElementById('userName');
        this.userInfo = document.getElementById('userInfo');
        this.aiModesList = document.getElementById('ai-modes-list');

        this.currentConversationId = null;
        this.conversations = [];
        this.currentAIMode = null;
        this.isTyping = false;

        this.initializeEventListeners();
        this.loadConversations();
        this.loadAIModes();
        this.checkForExistingConversation();
        this.updateUserInfo();
    }

    initializeEventListeners() {
        // Send button click
        this.sendBtn.addEventListener('click', (e) => {
            e.preventDefault();
            this.sendMessage();
        });

        // Text input listeners
        this.chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Auto-resize textarea and enable/disable send button
        this.chatInput.addEventListener('input', () => updateCharCounter(this.chatInput));

        // Suggestion cards
        document.querySelectorAll('.suggestion-card').forEach(card => {
            card.addEventListener('click', () => {
                const suggestion = card.dataset.suggestion;
                this.chatInput.value = suggestion;
                this.sendMessage();
            });
        });

        // New chat button
        this.newChatBtn.addEventListener('click', () => this.startNewChat());

        // Clear all conversations button
        if (this.clearAllBtn) {
            this.clearAllBtn.addEventListener('click', () => this.clearAllConversations());
        }

        // Settings button
        if (this.settingsBtn) {
            this.settingsBtn.addEventListener('click', () => this.toggleSettings());
        }

        // File uploads (guarded) — these UI elements are optional in production templates
        const attachBtn = document.getElementById('attachBtn');
        const fileInput = document.getElementById('fileInput');
        if (attachBtn && fileInput) {
            attachBtn.addEventListener('click', () => fileInput.click());
        }

        const uploadDocBtn = document.getElementById('uploadDocBtn');
        const docInput = document.getElementById('docInput');
        if (uploadDocBtn && docInput) {
            uploadDocBtn.addEventListener('click', () => docInput.click());

            // Handle document upload
            docInput.addEventListener('change', async (e) => {
                const file = e.target.files[0];
                if (!file) return;

                const formData = new FormData();
                formData.append('pdf', file);

                try {
                    const response = await fetch('/rag/api/upload_pdf', {
                        method: 'POST',
                        body: formData,
                        credentials: 'same-origin'
                    });

                    // Safely parse JSON or surface raw text for debugging
                    const contentType = response.headers.get('content-type') || '';
                    let data;
                    if (contentType.includes('application/json')) {
                        data = await response.json();
                    } else {
                        const text = await response.text();
                        throw new Error(`Non-JSON response (${response.status}): ${text.slice(0, 300)}`);
                    }

                    if (!response.ok || data.error) {
                        throw new Error(data && data.error ? data.error : `Upload failed (${response.status})`);
                    }

                    this.addMessage(
                        `✅ Successfully uploaded and processed: ${file.name}\nIngested ${data.chunks} chunks. This knowledge is now available.`,
                        'assistant'
                    );
                } catch (error) {
                    console.error('Upload error:', error);
                    this.addMessage(
                        `❌ Upload failed: ${error.message}. Check file type/size or try another PDF.`,
                        'assistant'
                    );
                }

                e.target.value = '';
            });
        }
    }

    async loadConversations() {
        try {
            const response = await fetch('/api/conversations');
            const data = await response.json();

            if (data.conversations) {
                this.conversations = data.conversations;
                this.renderConversations();
            }
        } catch (error) {
            console.error('Error loading conversations:', error);
        }
    }

    renderConversations() {
        this.conversationsList.innerHTML = '';

        this.conversations.forEach(conv => {
            const convElement = document.createElement('div');
            convElement.className = `conversation-item ${conv.id === this.currentConversationId ? 'active' : ''}`;
            convElement.innerHTML = `
                <div class="conversation-title">${conv.title}</div>
                <div class="conversation-actions">
                    <button class="action-btn-small" onclick="agriChat.deleteConversation(${conv.id})" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;

            convElement.addEventListener('click', (e) => {
                if (!e.target.closest('.conversation-actions')) {
                    this.loadConversation(conv.id);
                }
            });

            this.conversationsList.appendChild(convElement);
        });
    }

    async loadConversation(conversationId) {
        try {
            const response = await fetch(`/api/conversations/${conversationId}/messages`);
            const data = await response.json();

            if (data.conversation) {
                this.currentConversationId = conversationId;
                this.clearMessages();

                // Update URL without page reload
                window.history.pushState({}, '', `/chat/${conversationId}`);

                // Render messages
                data.conversation.messages.forEach(msg => {
                    this.addMessage(msg.content, msg.role, new Date(msg.timestamp));
                });

                // Update active conversation in sidebar
                this.renderConversations();
            }
        } catch (error) {
            console.error('Error loading conversation:', error);
        }
    }

    checkForExistingConversation() {
        const pathParts = window.location.pathname.split('/');
        if (pathParts[1] === 'chat' && pathParts[2]) {
            this.currentConversationId = parseInt(pathParts[2]);
            this.loadConversation(this.currentConversationId);
        }
    }

    startNewChat() {
        this.currentConversationId = null;
        this.clearMessages();
        this.showWelcomeScreen();

        // Update URL
        window.history.pushState({}, '', '/chat');

        // Update sidebar
        this.renderConversations();

        // Focus input
        this.chatInput.focus();
    }

    clearMessages() {
        this.chatMessages.innerHTML = '';
    }

    showWelcomeScreen() {
        this.chatMessages.innerHTML = `
            <div class="welcome-screen">
                <i class="welcome-icon fas fa-robot"></i>
                <h2 class="welcome-title">Welcome to AgriGenius AI</h2>
                <p class="welcome-subtitle">Your intelligent farming companion powered by advanced AI</p>

                <div class="suggestions-grid">
                    <div class="suggestion-card" data-suggestion="What are the current sensor readings?">
                        <i class="suggestion-icon fas fa-chart-line"></i>
                        <div class="suggestion-title">Sensor Data</div>
                        <div class="suggestion-desc">Check current farm conditions</div>
                    </div>

                    <div class="suggestion-card" data-suggestion="How can I improve my crop yield?">
                        <i class="suggestion-icon fas fa-seedling"></i>
                        <div class="suggestion-title">Crop Optimization</div>
                        <div class="suggestion-desc">Get yield improvement tips</div>
                    </div>

                    <div class="suggestion-card" data-suggestion="What fertilizer should I use?">
                        <i class="suggestion-icon fas fa-flask"></i>
                        <div class="suggestion-title">Fertilizer Advice</div>
                        <div class="suggestion-desc">Nutrient recommendations</div>
                    </div>

                    <div class="suggestion-card" data-suggestion="When should I water my plants?">
                        <i class="suggestion-icon fas fa-tint"></i>
                        <div class="suggestion-title">Watering Schedule</div>
                        <div class="suggestion-desc">Optimize irrigation timing</div>
                    </div>
                </div>
            </div>
        `;

        // Re-attach suggestion card listeners
        document.querySelectorAll('.suggestion-card').forEach(card => {
            card.addEventListener('click', () => {
                const suggestion = card.dataset.suggestion;
                this.chatInput.value = suggestion;
                this.sendMessage();
            });
        });
    }

    async sendMessage() {
        console.log("sendMessage called");
        const message = this.chatInput.value.trim();
        if (!message || this.isTyping) return;

        // Hide welcome screen if visible
        const welcomeScreen = document.querySelector('.welcome-screen');
        if (welcomeScreen) {
            welcomeScreen.remove();
        }

        // Add user message
        this.addMessage(message, 'user');
        this.chatInput.value = '';
        this.chatInput.style.height = 'auto';
        this.sendBtn.disabled = false;

        // Show typing indicator
        this.showTypingIndicator();

        try {
            // Send to RAG endpoint
            console.log("Sending fetch request to /rag/api/chat_rag");
            const response = await fetch('/rag/api/chat_rag', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: message
                })
            });
            console.log("Fetch request complete, processing response");

            const data = await response.json();
            console.log("Response JSON parsed:", data);

            // Remove typing indicator
            this.hideTypingIndicator();

            if (data.error) {
                console.error("API Error:", data.error);
                this.addMessage(`Sorry, I encountered an error: ${data.error}. Please try again.`, 'assistant');
            } else if (!data.success) {
                console.error("API Request Failed:", data);
                this.addMessage('Sorry, I\'m having trouble processing your request right now. Please try again.', 'assistant');
            } else {
                // Show answer using consistent 'response' field
                this.addMessage(data.response || 'No answer returned.', 'assistant');
                // Show sources if present
                if (data.contexts && Array.isArray(data.contexts) && data.contexts.length) {
                    const sources = data.contexts.map(c => `[${c.id || 'source'}]`).slice(0, 5).join(' ');
                    this.addMessage(`Sources: ${sources}`, 'assistant');
                }
            }
        } catch (error) {
            console.error("Error in sendMessage:", error);
            this.hideTypingIndicator();
            this.addMessage('Sorry, I\'m having trouble connecting. Please check your internet connection and try again.', 'assistant');
        }
    }

    addMessage(content, sender, timestamp = null) {
        const messageGroup = document.createElement('div');
        messageGroup.className = 'message-group';

        const message = document.createElement('div');
        message.className = `message ${sender}`;

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';

        if (sender === 'user') {
            avatar.textContent = window.currentUser ? window.currentUser.charAt(0).toUpperCase() : 'U';
        } else {
            avatar.innerHTML = '<i class="fas fa-robot"></i>';
        }

        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';

        const messageBubble = document.createElement('div');
        messageBubble.className = 'message-bubble';
        messageBubble.innerHTML = this.formatMessage(content);

        const messageTime = document.createElement('div');
        messageTime.className = 'message-time';
        const time = timestamp ? new Date(timestamp) : new Date();
        messageTime.textContent = time.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});

        messageContent.appendChild(messageBubble);
        messageContent.appendChild(messageTime);

        message.appendChild(avatar);
        message.appendChild(messageContent);
        messageGroup.appendChild(message);

        this.chatMessages.appendChild(messageGroup);
        this.scrollToBottom();
    }

    formatMessage(content) {
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>')
            .replace(/• /g, '<br>• ');
    }

    showTypingIndicator() {
        this.isTyping = true;
        this.sendBtn.disabled = true;

        const typingGroup = document.createElement('div');
        typingGroup.className = 'message-group typing-group';

        const typingMessage = document.createElement('div');
        typingMessage.className = 'message assistant';

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.innerHTML = '<i class="fas fa-robot"></i>';

        const typingContent = document.createElement('div');
        typingContent.className = 'message-content';

        const typingIndicator = document.createElement('div');
        typingIndicator.className = 'typing-indicator';
        typingIndicator.innerHTML = `
            <span>AgriGenius is thinking</span>
            <div class="typing-dots">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        `;

        typingContent.appendChild(typingIndicator);
        typingMessage.appendChild(avatar);
        typingMessage.appendChild(typingContent);
        typingGroup.appendChild(typingMessage);

        this.chatMessages.appendChild(typingGroup);
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        this.isTyping = false;
        const typingGroup = this.chatMessages.querySelector('.typing-group');
        if (typingGroup) {
            typingGroup.remove();
        }

        // Re-enable send button if there's text
        const hasText = this.chatInput.value.trim().length > 0;
        this.sendBtn.disabled = !hasText;
    }

    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    async deleteConversation(conversationId) {
        if (!confirm('Are you sure you want to delete this conversation?')) {
            return;
        }

        try {
            const response = await fetch(`/api/conversations/${conversationId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                // If we're currently viewing this conversation, start a new chat
                if (this.currentConversationId === conversationId) {
                    this.startNewChat();
                }

                // Reload conversations list
                this.loadConversations();
            }
        } catch (error) {
            console.error('Error deleting conversation:', error);
            alert('Failed to delete conversation. Please try again.');
        }
    }

    // New methods for enhanced sidebar functionality
    updateUserInfo() {
        const userData = document.getElementById('user-data');
        if (userData && this.userName) {
            const isAuthenticated = userData.dataset.authenticated === 'true';
            const username = userData.dataset.username || 'Guest';
            
            this.userName.textContent = username;
            
            if (this.userInfo) {
                this.userInfo.style.display = isAuthenticated ? 'flex' : 'none';
            }
        }
    }

    async clearAllConversations() {
        if (!confirm('Are you sure you want to delete all conversations? This action cannot be undone.')) {
            return;
        }

        try {
            const response = await fetch('/api/conversations', {
                method: 'DELETE'
            });

            if (response.ok) {
                this.startNewChat();
                this.loadConversations();
            }
        } catch (error) {
            console.error('Error clearing conversations:', error);
            alert('Failed to clear conversations. Please try again.');
        }
    }

    toggleSettings() {
        // For now, just show a placeholder for settings
        const settingsMenu = document.createElement('div');
        settingsMenu.className = 'settings-menu';
        settingsMenu.innerHTML = `
            <div class="settings-header">
                <h4>Settings</h4>
                <button class="close-settings">&times;</button>
            </div>
            <div class="settings-content">
                <div class="setting-item">
                    <label>Theme</label>
                    <select id="themeSelect">
                        <option value="light">Light</option>
                        <option value="dark">Dark</option>
                    </select>
                </div>
                <div class="setting-item">
                    <label>Font Size</label>
                    <select id="fontSizeSelect">
                        <option value="small">Small</option>
                        <option value="medium" selected>Medium</option>
                        <option value="large">Large</option>
                    </select>
                </div>
            </div>
        `;

        // Add styles for settings menu
        const style = document.createElement('style');
        style.textContent = `
            .settings-menu {
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: var(--bg-card);
                border: 1px solid var(--border-color);
                border-radius: var(--radius-xl);
                padding: var(--spacing-lg);
                box-shadow: var(--shadow-xl);
                z-index: 10000;
                min-width: 300px;
            }
            .settings-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: var(--spacing-lg);
                padding-bottom: var(--spacing-md);
                border-bottom: 1px solid var(--border-color);
            }
            .settings-header h4 {
                margin: 0;
                color: var(--text-primary);
            }
            .close-settings {
                background: none;
                border: none;
                font-size: var(--font-size-xl);
                color: var(--text-muted);
                cursor: pointer;
                padding: 0;
                width: 24px;
                height: 24px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: var(--radius-sm);
            }
            .close-settings:hover {
                background: var(--bg-tertiary);
                color: var(--text-primary);
            }
            .settings-content {
                display: flex;
                flex-direction: column;
                gap: var(--spacing-md);
            }
            .setting-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .setting-item label {
                color: var(--text-primary);
                font-weight: 500;
            }
            .setting-item select {
                padding: var(--spacing-xs) var(--spacing-sm);
                border: 1px solid var(--border-color);
                border-radius: var(--radius-sm);
                background: var(--bg-primary);
                color: var(--text-primary);
                font-size: var(--font-size-sm);
            }
        `;
        document.head.appendChild(style);

        document.body.appendChild(settingsMenu);

        // Add event listeners
        settingsMenu.querySelector('.close-settings').addEventListener('click', () => {
            settingsMenu.remove();
            style.remove();
        });

        // Theme selector
        const themeSelect = settingsMenu.querySelector('#themeSelect');
        themeSelect.addEventListener('change', (e) => {
            document.body.setAttribute('data-theme', e.target.value);
            localStorage.setItem('theme', e.target.value);
        });

        // Font size selector
        const fontSizeSelect = settingsMenu.querySelector('#fontSizeSelect');
        fontSizeSelect.addEventListener('change', (e) => {
            const root = document.documentElement;
            switch(e.target.value) {
                case 'small':
                    root.style.fontSize = '14px';
                    break;
                case 'medium':
                    root.style.fontSize = '16px';
                    break;
                case 'large':
                    root.style.fontSize = '18px';
                    break;
            }
            localStorage.setItem('fontSize', e.target.value);
        });

        // Load saved settings
        const savedTheme = localStorage.getItem('theme') || 'light';
        themeSelect.value = savedTheme;
        document.body.setAttribute('data-theme', savedTheme);

        const savedFontSize = localStorage.getItem('fontSize') || 'medium';
        fontSizeSelect.value = savedFontSize;
        switch(savedFontSize) {
            case 'small':
                document.documentElement.style.fontSize = '14px';
                break;
            case 'medium':
                document.documentElement.style.fontSize = '16px';
                break;
            case 'large':
                document.documentElement.style.fontSize = '18px';
                break;
        }

        // Close on outside click
        setTimeout(() => {
            const closeOnOutsideClick = (e) => {
                if (!settingsMenu.contains(e.target) && e.target !== this.settingsBtn) {
                    settingsMenu.remove();
                    style.remove();
                    document.removeEventListener('click', closeOnOutsideClick);
                }
            };
            document.addEventListener('click', closeOnOutsideClick);
        }, 100);
    }

    // AI Modes functionality
    async loadAIModes() {
        try {
            const response = await fetch('/api/ai-modes');
            const data = await response.json();

            if (data.modes) {
                this.renderAIModes(data.modes);
                this.loadCurrentMode();
            }
        } catch (error) {
            console.error('Error loading AI modes:', error);
        }
    }

    renderAIModes(modes) {
        this.aiModesList.innerHTML = '';

        modes.forEach(mode => {
            const modeElement = document.createElement('div');
            modeElement.className = `ai-mode-item ${this.currentAIMode && this.currentAIMode.id === mode.id ? 'active' : ''}`;
            modeElement.dataset.modeId = mode.id;
            modeElement.innerHTML = `
                <div class="ai-mode-icon">
                    <i class="fas ${mode.icon}"></i>
                </div>
                <div class="ai-mode-info">
                    <div class="ai-mode-name">${mode.name}</div>
                    <div class="ai-mode-description">${mode.description}</div>
                </div>
            `;

            modeElement.addEventListener('click', () => {
                this.selectMode(mode);
            });

            this.aiModesList.appendChild(modeElement);
        });
    }

    async selectMode(mode) {
        try {
            const response = await fetch(`/api/ai-modes/${mode.name}/set`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ mode_id: mode.id })
            });

            if (response.ok) {
                this.currentAIMode = mode;
                this.renderAIModes(this.availableAIModes);
                this.addMessage(`Switched to ${mode.name} mode: ${mode.description}`, 'assistant');
            }
        } catch (error) {
            console.error('Error setting AI mode:', error);
        }
    }

    async loadCurrentMode() {
        try {
            const response = await fetch('/api/current-ai-mode');
            const data = await response.json();

            if (data.mode) {
                this.currentAIMode = data.mode;
                this.renderAIModes(this.availableAIModes);
            }
        } catch (error) {
            console.error('Error loading current AI mode:', error);
        }
    }
}

// Initialize chat when page loads
document.addEventListener('DOMContentLoaded', () => {
    // Check if we are on a page that uses AgriChatGPT
    if (document.getElementById('chat-window')) {
        window.agriChat = new AgriChatGPT();
    }
});