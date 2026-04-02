# NexusFlow AI - Modern Web UI

A beautiful, interactive chat interface for the NexusFlow Customer Success Digital FTE.

## 🎨 Features

### Live Chat Interface
- **Real-time AI responses** with typing indicators
- **Quick reply suggestions** for common questions
- **Message metadata** showing category and escalation status
- **Clean, modern design** with gradient styling

### Analytics Dashboard
- **Real-time metrics**: Total tickets, AI resolution rate, escalations
- **Sentiment distribution chart**: Visual breakdown of customer emotions
- **Category distribution chart**: Ticket types breakdown
- **Recent tickets list**: Click to view details

### Ticket Management
- **View all tickets** with filtering options
- **Ticket details modal** with full information
- **Status badges** for quick visual reference

## 🚀 How to Use

### Start the API Server

```bash
python demo_api.py
```

### Access the UI

Open your browser to:
- **Main UI**: http://localhost:8000/static/index.html
- **API Docs**: http://localhost:8000/docs
- **Old Form**: http://localhost:8000/test_form.html

## 📱 Views

### 1. Live Chat (Default)
Start chatting with the AI assistant immediately. Type your question or click a quick reply suggestion.

### 2. Dashboard
View analytics and metrics about all support tickets. Click refresh to update data.

### 3. Tickets
Browse all tickets created during your session. Click any ticket to view details.

## 🎯 Quick Test Scenarios

Try these sample questions in the chat:

1. **How-to Question**: "How do I set up recurring tasks?"
2. **Pricing**: "What are your pricing plans?"
3. **Technical Issue**: "Gantt chart export is hanging"
4. **Billing**: "I was charged twice!"
5. **Integration**: "How do I connect Slack?"

## 🎨 UI Components

- **Sidebar Navigation**: Switch between Chat, Dashboard, and Tickets
- **Status Badge**: Shows AI online/offline status
- **Typing Indicator**: Animated dots while AI is responding
- **Quick Replies**: Pre-defined questions for quick testing
- **Theme Toggle**: Switch between light and dark themes (coming soon)
- **Clear Chat**: Reset the conversation

## 📊 Dashboard Metrics

| Metric | Description |
|--------|-------------|
| Total Tickets | Number of support requests |
| AI Resolution Rate | Percentage resolved by AI |
| Escalated to Human | Number requiring human agent |
| Avg Sentiment | Overall customer satisfaction |

## 🔧 Customization

Edit `static/style.css` to customize:
- Colors (CSS variables at top)
- Spacing and layout
- Animations and transitions
- Responsive breakpoints

Edit `static/app.js` to customize:
- Chat behavior
- Dashboard rendering
- API integration

---

**Built with ❤️ for the Digital FTE Hackathon**
