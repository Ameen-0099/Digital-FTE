/**
 * NexusFlow AI - Chat & Dashboard Application
 */

const API_URL = '';
let tickets = [];
let currentView = 'chat';

// DOM Elements
const chatMessages = document.getElementById('chatMessages');
const chatForm = document.getElementById('chatForm');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const quickReplies = document.getElementById('quickReplies');
const clearChatBtn = document.getElementById('clearChat');
const toggleThemeBtn = document.getElementById('toggleTheme');
const navItems = document.querySelectorAll('.nav-item');
const views = {
    chat: document.getElementById('chat-view'),
    dashboard: document.getElementById('dashboard-view'),
    tickets: document.getElementById('tickets-view')
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    loadDashboard();
    checkApiHealth();
});

function setupEventListeners() {
    // Chat form submit
    chatForm.addEventListener('submit', handleSubmit);

    // Quick replies
    quickReplies.addEventListener('click', (e) => {
        const quickReply = e.target.closest('.quick-reply');
        if (quickReply) {
            sendMessage(quickReply.dataset.message);
        }
    });

    // Clear chat
    clearChatBtn.addEventListener('click', clearChat);

    // Navigation
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const view = item.dataset.view;
            switchView(view);
        });
    });

    // Theme toggle
    toggleThemeBtn.addEventListener('click', toggleTheme);

    // Refresh dashboard
    document.getElementById('refreshDashboard')?.addEventListener('click', loadDashboard);

    // Modal close
    document.getElementById('closeModal')?.addEventListener('click', closeModal);
}

function switchView(viewName) {
    // Update nav
    navItems.forEach(item => {
        item.classList.toggle('active', item.dataset.view === viewName);
    });

    // Update view
    Object.entries(views).forEach(([name, el]) => {
        el.classList.toggle('active', name === viewName);
    });

    currentView = viewName;

    if (viewName === 'dashboard') {
        loadDashboard();
    } else if (viewName === 'tickets') {
        loadTickets();
    }
}

async function handleSubmit(e) {
    e.preventDefault();
    const message = messageInput.value.trim();
    if (!message) return;

    sendMessage(message);
    messageInput.value = '';
}

function sendMessage(message) {
    // Add user message
    addMessage(message, 'user');

    // Show typing indicator
    showTypingIndicator();

    // Send to API
    fetch(`${API_URL}/support/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            name: 'Chat User',
            email: 'user@chat.com',
            subject: message,
            description: message,
            priority: 'medium',
            channel: 'web_form'
        })
    })
    .then(res => res.json())
    .then(data => {
        removeTypingIndicator();
        addMessage(data.response, 'ai', data);
    })
    .catch(err => {
        removeTypingIndicator();
        addMessage('Sorry, I encountered an error. Please try again.', 'ai', { error: true });
        console.error('Error:', err);
    });
}

function addMessage(text, type, metadata = {}) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}-message`;

    const avatar = type === 'ai' ? '<i class="fas fa-robot"></i>' : '<i class="fas fa-user"></i>';
    const sender = type === 'ai' ? 'NexusFlow AI' : 'You';
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    let metaHtml = '';
    if (type === 'ai' && metadata.category) {
        const badgeClass = metadata.escalation_needed ? 'badge-warning' : 'badge-success';
        const badgeText = metadata.escalation_needed ? '⚠️ Escalated' : '✓ Resolved by AI';
        metaHtml = `
            <div class="message-meta">
                <span class="badge ${badgeClass}">${badgeText}</span>
                <span class="badge badge-info">${formatCategory(metadata.category)}</span>
            </div>
        `;
    }

    messageDiv.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-sender">${sender}</span>
                <span class="message-time">${time}</span>
            </div>
            <div class="message-text">${formatMessage(text)}</div>
            ${metaHtml}
        </div>
    `;

    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Store ticket if AI response
    if (type === 'ai' && metadata.ticket_id) {
        tickets.unshift({
            id: metadata.ticket_id,
            subject: text.substring(0, 50),
            category: metadata.category,
            sentiment: metadata.sentiment,
            escalation: metadata.escalation_needed,
            time: time
        });
    }
}

function formatMessage(text) {
    // Convert newlines to breaks
    text = text.replace(/\n/g, '<br>');

    // Bold text
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    return text;
}

function formatCategory(category) {
    return category.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function showTypingIndicator() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message ai-message typing-message';
    typingDiv.id = 'typingIndicator';
    typingDiv.innerHTML = `
        <div class="message-avatar"><i class="fas fa-robot"></i></div>
        <div class="message-content">
            <div class="message-text">
                <div class="typing-indicator">
                    <span></span><span></span><span></span>
                </div>
            </div>
        </div>
    `;
    chatMessages.appendChild(typingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeTypingIndicator() {
    const typing = document.getElementById('typingIndicator');
    if (typing) typing.remove();
}

function clearChat() {
    chatMessages.innerHTML = `
        <div class="message ai-message">
            <div class="message-avatar"><i class="fas fa-robot"></i></div>
            <div class="message-content">
                <div class="message-header">
                    <span class="message-sender">NexusFlow AI</span>
                    <span class="message-time">Now</span>
                </div>
                <div class="message-text">
                    👋 Chat cleared! How can I help you?
                </div>
            </div>
        </div>
    `;
    tickets = [];
}

async function loadDashboard() {
    try {
        const response = await fetch(`${API_URL}/reports/dashboard`);
        const data = await response.json();

        // Update metrics
        document.getElementById('totalTickets').textContent = data.overview?.total_tickets || 0;
        document.getElementById('aiResolutionRate').textContent = data.overview?.ai_resolution_rate || '0%';
        document.getElementById('escalatedTickets').textContent = data.overview?.escalated_to_human || 0;

        // Calculate average sentiment
        const sentiments = data.sentiment_distribution || {};
        const totalSentiment = Object.values(sentiments).reduce((a, b) => a + b, 0);
        if (totalSentiment > 0) {
            const positive = (sentiments.positive || 0) + (sentiments.very_positive || 0);
            const neutral = sentiments.neutral || 0;
            const negative = (sentiments.frustrated || 0) + (sentiments.panicked || 0) + (sentiments.angry || 0);
            
            if (positive > negative) {
                document.getElementById('avgSentiment').textContent = '😊 Good';
                document.getElementById('avgSentiment').style.color = 'var(--success)';
            } else if (negative > positive) {
                document.getElementById('avgSentiment').textContent = '😟 Needs Attention';
                document.getElementById('avgSentiment').style.color = 'var(--warning)';
            } else {
                document.getElementById('avgSentiment').textContent = '😐 Neutral';
                document.getElementById('avgSentiment').style.color = 'var(--gray-600)';
            }
        }

        // Render sentiment chart
        renderSentimentChart(sentiments);

        // Render category chart
        renderCategoryChart(data.category_distribution || {});

        // Render recent tickets
        renderRecentTickets(data.recent_tickets || []);

    } catch (err) {
        console.error('Error loading dashboard:', err);
    }
}

function renderSentimentChart(sentiments) {
    const container = document.getElementById('sentimentChart');
    const total = Object.values(sentiments).reduce((a, b) => a + b, 0) || 1;

    const colors = {
        panicked: '#f56565',
        angry: '#ed8936',
        frustrated: '#ed8936',
        very_frustrated: '#ed8936',
        concerned: '#ecc94b',
        neutral: '#4299e1',
        positive: '#48bb78',
        very_positive: '#48bb78'
    };

    container.innerHTML = Object.entries(sentiments)
        .sort((a, b) => b[1] - a[1])
        .map(([sentiment, count]) => {
            const percent = Math.round((count / total) * 100);
            return `
                <div class="chart-bar">
                    <span class="chart-bar-label">${sentiment.replace('_', ' ')}</span>
                    <div class="chart-bar-track">
                        <div class="chart-bar-fill" style="width: ${percent}%; background: ${colors[sentiment] || '#718096'}">
                            ${percent}%
                        </div>
                    </div>
                </div>
            `;
        }).join('');
}

function renderCategoryChart(categories) {
    const container = document.getElementById('categoryChart');
    const total = Object.values(categories).reduce((a, b) => a + b, 0) || 1;

    const colors = [
        '#667eea', '#764ba2', '#48bb78', '#ed8936', '#f56565',
        '#4299e1', '#ecc94b', '#38b2ac', '#9f7aea', '#f687b3'
    ];

    container.innerHTML = Object.entries(categories)
        .sort((a, b) => b[1] - a[1])
        .map(([category, count], index) => {
            const percent = Math.round((count / total) * 100);
            return `
                <div class="chart-bar">
                    <span class="chart-bar-label">${formatCategory(category)}</span>
                    <div class="chart-bar-track">
                        <div class="chart-bar-fill" style="width: ${percent}%; background: ${colors[index % colors.length]}">
                            ${percent}%
                        </div>
                    </div>
                </div>
            `;
        }).join('');
}

function renderRecentTickets(recentIds) {
    const container = document.getElementById('recentTickets');

    if (tickets.length === 0 && recentIds.length === 0) {
        container.innerHTML = '<p style="color: var(--gray-500); text-align: center; padding: 20px;">No tickets yet</p>';
        return;
    }

    const displayTickets = tickets.length > 0 ? tickets : recentIds.map(id => ({
        id,
        subject: 'Ticket',
        category: 'general',
        escalation: false,
        time: new Date().toLocaleTimeString()
    }));

    container.innerHTML = displayTickets.slice(0, 5).map(ticket => `
        <div class="ticket-row" onclick="showTicketDetail('${ticket.id}')">
            <span class="ticket-id">${ticket.id}</span>
            <span class="ticket-subject">${ticket.subject?.substring(0, 40) || 'Support Request'}${(ticket.subject?.length || 0) > 40 ? '...' : ''}</span>
            <span class="badge ${ticket.escalation ? 'badge-warning' : 'badge-success'}">
                ${ticket.escalation ? '⚠️ Escalated' : '✓ Resolved'}
            </span>
            <span style="color: var(--gray-500); font-size: 13px;">${ticket.time}</span>
        </div>
    `).join('');
}

async function loadTickets() {
    const container = document.getElementById('ticketsList');

    if (tickets.length === 0) {
        container.innerHTML = '<p style="color: var(--gray-500); text-align: center; padding: 40px;">No tickets yet. Start a chat to create tickets!</p>';
        return;
    }

    container.innerHTML = tickets.map(ticket => `
        <div class="ticket-row" onclick="showTicketDetail('${ticket.id}')">
            <span class="ticket-id">${ticket.id}</span>
            <span class="ticket-subject">${ticket.subject?.substring(0, 60) || 'Support Request'}</span>
            <span class="badge badge-info">${formatCategory(ticket.category || 'general')}</span>
            <span class="badge ${ticket.escalation ? 'badge-warning' : 'badge-success'}">
                ${ticket.escalation ? 'Escalated' : 'Resolved'}
            </span>
        </div>
    `).join('');
}

function showTicketDetail(ticketId) {
    const ticket = tickets.find(t => t.id === ticketId) || { id: ticketId };

    const modal = document.getElementById('ticketModal');
    const body = document.getElementById('ticketModalBody');

    body.innerHTML = `
        <div class="ticket-detail">
            <div class="detail-row">
                <span class="detail-label">Ticket ID:</span>
                <span class="detail-value">${ticket.id}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Subject:</span>
                <span class="detail-value">${ticket.subject || 'N/A'}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Category:</span>
                <span class="detail-value">${formatCategory(ticket.category || 'general')}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Sentiment:</span>
                <span class="detail-value">${ticket.sentiment ? formatCategory(ticket.sentiment) : 'N/A'}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Status:</span>
                <span class="detail-value">
                    <span class="badge ${ticket.escalation ? 'badge-warning' : 'badge-success'}">
                        ${ticket.escalation ? 'Escalated to Human' : 'Resolved by AI'}
                    </span>
                </span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Time:</span>
                <span class="detail-value">${ticket.time || 'N/A'}</span>
            </div>
        </div>
    `;

    modal.classList.add('active');
}

function closeModal() {
    document.getElementById('ticketModal').classList.remove('active');
}

function toggleTheme() {
    document.body.classList.toggle('dark-theme');
    const btn = document.getElementById('toggleTheme');
    btn.innerHTML = document.body.classList.contains('dark-theme')
        ? '<i class="fas fa-sun"></i>'
        : '<i class="fas fa-moon"></i>';
}

async function checkApiHealth() {
    try {
        const response = await fetch(`${API_URL}/health`);
        const data = await response.json();

        const statusDot = document.querySelector('.status-dot');
        const statusText = document.querySelector('.status-badge span:last-child');

        if (data.status === 'healthy') {
            statusDot.style.background = '#48bb78';
            statusText.textContent = 'AI Online';
        } else {
            statusDot.style.background = '#ed8936';
            statusText.textContent = 'Limited Service';
        }
    } catch (err) {
        const statusDot = document.querySelector('.status-dot');
        const statusText = document.querySelector('.status-badge span:last-child');
        statusDot.style.background = '#f56565';
        statusText.textContent = 'Offline';
    }
}

// Close modal on outside click
window.addEventListener('click', (e) => {
    const modal = document.getElementById('ticketModal');
    if (e.target === modal) {
        modal.classList.remove('active');
    }
});
