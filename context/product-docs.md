# NexusFlow - Product Documentation

## Table of Contents

1. [Getting Started](#getting-started)
2. [Core Features](#core-features)
3. [User Guide](#user-guide)
4. [Admin Guide](#admin-guide)
5. [Integrations](#integrations)
6. [API Reference](#api-reference)
7. [Troubleshooting](#troubleshooting)
8. [FAQs](#faqs)

---

## Getting Started

### Creating Your Account

1. Visit [app.nexusflow.com](https://app.nexusflow.com)
2. Click "Start Free Trial"
3. Enter your work email and create a password
4. Verify your email address
5. Complete the onboarding wizard:
   - Add team members (optional)
   - Choose a workspace template
   - Import from another tool (optional)

### System Requirements

| Platform | Requirements |
|----------|--------------|
| **Web App** | Chrome 90+, Firefox 88+, Safari 14+, Edge 90+ |
| **Desktop App** | Windows 10+, macOS 11+, Linux (Ubuntu 20.04+) |
| **Mobile App** | iOS 15+, Android 10+ |
| **Internet** | Minimum 5 Mbps for optimal performance |

### Quick Start Guide (First 15 Minutes)

```
Minute 1-3:   Create your first project
Minute 4-6:   Add 3-5 tasks with due dates
Minute 7-9:   Invite team members via email
Minute 10-12: Assign tasks to team members
Minute 13-15: Switch to Board view and customize columns
```

---

## Core Features

### 1. Project Boards

**Description:** Visualize work your way with multiple view types.

#### Board Views

| View | Best For | Key Actions |
|------|----------|-------------|
| **Kanban** | Workflow management | Drag-and-drop cards, WIP limits, swimlanes |
| **Gantt** | Timeline planning | Dependencies, critical path, milestones |
| **List** | Detailed task management | Bulk edit, filters, custom sorting |
| **Calendar** | Deadline tracking | Month/week/day views, drag to reschedule |
| **Workload** | Capacity planning | Team availability, overallocation alerts |

#### Creating a Project

```
1. Click "+ New Project" from the sidebar
2. Choose a template or start blank
3. Name your project and set visibility (Private/Team/Public)
4. Configure default view and working days
5. Click "Create Project"
```

#### Project Templates

- **Software Sprint:** 2-week sprint structure with backlog
- **Marketing Campaign:** Campaign phases with content calendar
- **Event Planning:** Timeline with vendor management
- **Product Launch:** Go-to-market checklist with owners
- **Client Onboarding:** Milestone-based client journey
- **Custom:** Build your own template

---

### 2. Task Management

**Description:** Break down work into actionable items with full context.

#### Task Anatomy

```
┌─────────────────────────────────────────────────┐
│ Task Title                                      │
├─────────────────────────────────────────────────┤
│ Description (Rich text with attachments)        │
│ Assignee: @Sarah Chen                           │
│ Due Date: Mar 30, 2026                          │
│ Priority: 🔴 High                               │
│ Status: In Progress                             │
│ Tags: #bug, #urgent, #frontend                  │
│ Subtasks: 3/5 complete                          │
│ Dependencies: Blocks "Deploy to staging"        │
│ Time Estimate: 4h | Logged: 2.5h                │
└─────────────────────────────────────────────────┘
```

#### Task Operations

| Action | How To |
|--------|--------|
| Create Task | Click "+ Add Task" or press `Q` |
| Add Subtask | Open task → "+ Add Subtask" |
| Set Dependency | Open task → Dependencies → "Add blocking/blocked by" |
| Recurring Task | Open task → Repeat → Choose frequency |
| Duplicate Task | Right-click task → "Duplicate" |
| Archive Task | Right-click task → "Archive" |

#### Priority Levels

| Priority | Icon | SLA | Use Case |
|----------|------|-----|----------|
| Critical | 🔴🔴 | 4 hours | Production down, data loss |
| High | 🔴 | 24 hours | Major feature broken |
| Medium | 🟡 | 48 hours | Standard bugs, improvements |
| Low | 🟢 | 1 week | Nice-to-have, future consideration |

---

### 3. Time Tracking

**Description:** Track time directly in tasks for accurate project estimation.

#### Starting a Timer

```
1. Open any task
2. Click the ▶️ timer icon
3. Timer runs in the background while you work
4. Click ⏹️ to stop and log time
```

#### Manual Time Entry

```
1. Open task → Time tab
2. Click "+ Add Time"
3. Enter date, duration, and description
4. Select billable/non-billable
5. Click "Save"
```

#### Timesheets

- **Weekly View:** See all logged time by day
- **Project View:** Time breakdown by project
- **Export:** CSV, Excel, or PDF formats
- **Approval Workflow:** Manager review before billing

---

### 4. Resource Planning

**Description:** Balance workloads and prevent team burnout.

#### Capacity Settings

```
1. Go to Settings → Team → Capacity
2. Set weekly hours for each team member
3. Add time off/vacation dates
4. Configure utilization targets (default: 80%)
```

#### Workload Indicators

| Indicator | Meaning | Action |
|-----------|---------|--------|
| 🟢 Green | Under capacity (0-80%) | Can take more work |
| 🟡 Yellow | At capacity (80-100%) | Monitor closely |
| 🔴 Red | Over capacity (>100%) | Redistribute tasks |

---

### 5. Collaboration Hub

**Description:** Keep all project communication in one place.

#### Comments & Mentions

```
- @mention teammates to notify them
- Use / commands for quick actions:
  - /assign @name - Assign task
  - /due YYYY-MM-DD - Set due date
  - /priority high - Set priority
  - /status done - Mark complete
```

#### File Sharing

| Plan | Storage | Max File Size | Supported Formats |
|------|---------|---------------|-------------------|
| Free | 100 MB | 10 MB | All common formats |
| Starter | 10 GB | 50 MB | All common formats |
| Professional | 100 GB | 100 MB | All common formats |
| Business | Unlimited | 500 MB | All common formats |
| Enterprise | Unlimited | 2 GB | All common formats |

#### Activity Feed

Real-time stream showing:
- Task completions
- Comments and mentions
- File uploads
- Status changes
- Member additions/removals

---

## User Guide

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Q` | Quick add task |
| `Ctrl/Cmd + K` | Global search |
| `Ctrl/Cmd + /` | Show all shortcuts |
| `G + T` | Go to Tasks |
| `G + P` | Go to Projects |
| `G + C` | Go to Calendar |
| `J` / `K` | Navigate down/up in lists |
| `Enter` | Open selected item |
| `Esc` | Close modal/cancel |

### Mobile App Features

#### iOS & Android

- ✅ View and edit tasks
- ✅ Receive push notifications
- ✅ Comment and attach photos
- ✅ Start/stop time timer
- ✅ Scan documents into tasks
- ❌ Gantt chart editing (view only)
- ❌ Admin settings

---

## Admin Guide

### User Management

#### Adding Team Members

```
1. Settings → Team → "+ Invite Member"
2. Enter email addresses (comma-separated for bulk)
3. Choose default role (Member/Admin)
4. Add personal message (optional)
5. Click "Send Invites"
```

#### User Roles & Permissions

| Permission | Admin | Member | Guest |
|------------|-------|--------|-------|
| Create projects | ✅ | ✅ | ❌ |
| Delete projects | ✅ | Own only | ❌ |
| Invite members | ✅ | ❌ | ❌ |
| Access billing | ✅ | ❌ | ❌ |
| Export data | ✅ | ✅ | ❌ |
| View all projects | ✅ | Team only | Assigned only |
| Manage integrations | ✅ | ❌ | ❌ |

### Billing & Subscription

#### Updating Payment Method

```
1. Settings → Billing → Payment Methods
2. Click "+ Add Card" or edit existing
3. Enter card details
4. Set as default if needed
5. Click "Save"
```

#### Plan Comparison

| Feature | Free | Starter | Professional | Business | Enterprise |
|---------|------|---------|--------------|----------|------------|
| Max Projects | 3 | ∞ | ∞ | ∞ | ∞ |
| Storage | 100MB | 10GB | 100GB | ∞ | ∞ |
| Gantt Charts | ❌ | ✅ | ✅ | ✅ | ✅ |
| Time Tracking | ❌ | ❌ | ✅ | ✅ | ✅ |
| Advanced Reports | ❌ | ❌ | ❌ | ✅ | ✅ |
| SSO/SAML | ❌ | ❌ | ❌ | ❌ | ✅ |
| SLA | ❌ | ❌ | ❌ | 99.9% | 99.99% |
| Dedicated CSM | ❌ | ❌ | ❌ | ❌ | ✅ |

### Security Settings

#### Two-Factor Authentication (2FA)

```
1. Settings → Security → Two-Factor Auth
2. Choose method (Authenticator app or SMS)
3. Scan QR code with authenticator app
4. Enter verification code
5. Save backup codes in secure location
```

#### Session Management

- View active sessions across devices
- Revoke suspicious sessions remotely
- Set auto-logout timeout (15min - 24hr)
- Enforce 2FA for all team members (Business+)

---

## Integrations

### Popular Integrations

| Category | Integrations | Setup Time |
|----------|--------------|------------|
| **Communication** | Slack, Microsoft Teams, Discord | 5 min |
| **Development** | GitHub, GitLab, Bitbucket | 10 min |
| **CRM** | Salesforce, HubSpot, Pipedrive | 15 min |
| **Support** | Zendesk, Intercom, Help Scout | 10 min |
| **Cloud Storage** | Google Drive, Dropbox, OneDrive | 5 min |
| **Calendar** | Google Calendar, Outlook | 5 min |
| **Automation** | Zapier, Make, n8n | 20 min |

### Setting Up Slack Integration

```
1. Settings → Integrations → Slack → "Connect"
2. Authorize NexusFlow in Slack
3. Choose channels for notifications
4. Configure event triggers
5. Test with "/nexusflow test" command
```

### Webhooks

```json
POST https://your-server.com/webhook

{
  "event": "task.completed",
  "timestamp": "2026-03-27T10:30:00Z",
  "data": {
    "task_id": "tsk_abc123",
    "project_id": "prj_xyz789",
    "completed_by": "usr_456def",
    "completed_at": "2026-03-27T10:29:58Z"
  }
}
```

---

## API Reference

### Authentication

All API requests require a Bearer token in the header:

```
Authorization: Bearer YOUR_API_KEY
```

Generate API keys at: Settings → Developer → API Keys

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/projects` | List all projects |
| POST | `/api/v1/projects` | Create a project |
| GET | `/api/v1/tasks` | List tasks |
| POST | `/api/v1/tasks` | Create a task |
| PUT | `/api/v1/tasks/{id}` | Update a task |
| DELETE | `/api/v1/tasks/{id}` | Delete a task |
| POST | `/api/v1/time-entries` | Log time |
| GET | `/api/v1/users` | List team members |

### Rate Limits

| Plan | Requests/Minute | Requests/Day |
|------|-----------------|--------------|
| Free | 60 | 1,000 |
| Starter | 120 | 10,000 |
| Professional | 300 | 50,000 |
| Business | 600 | 200,000 |
| Enterprise | Custom | Custom |

---

## Troubleshooting

### Common Issues

#### "Unable to load project"

**Cause:** Browser cache or connectivity issue  
**Solution:**
```
1. Refresh the page (Ctrl/Cmd + R)
2. Clear browser cache
3. Check internet connection
4. Try incognito/private mode
5. Contact support if persists
```

#### "Invitation not received"

**Cause:** Email filtering or typo in address  
**Solution:**
```
1. Check spam/junk folder
2. Verify email address is correct
3. Add noreply@nexusflow.com to contacts
4. Resend invitation from Team settings
5. Try alternative email address
```

#### "Timer won't start"

**Cause:** Browser permissions or extension conflict  
**Solution:**
```
1. Allow notifications for app.nexusflow.com
2. Disable ad blockers for NexusFlow
3. Try desktop app instead
4. Check if task is already being timed
5. Clear app data and relogin
```

#### "Gantt chart not displaying correctly"

**Cause:** Too many tasks or browser performance  
**Solution:**
```
1. Apply filters to reduce visible tasks
2. Switch to List view for bulk edits
3. Use Chrome for best performance
4. Increase browser memory allocation
5. Consider upgrading plan for large projects
```

### Status Page

Check system status at: [status.nexusflow.com](https://status.nexusflow.com)

- Real-time uptime monitoring
- Incident history
- Scheduled maintenance notifications
- Subscribe to updates (Email/SMS/Slack)

---

## FAQs

### General

**Q: Can I switch plans anytime?**  
A: Yes! Upgrade instantly, downgrade at next billing cycle.

**Q: Is there a discount for annual billing?**  
A: Yes, save 20% with annual payment on any plan.

**Q: Do you offer nonprofit discounts?**  
A: Yes, 50% off for registered 501(c)(3) organizations. Contact sales@nexusflow.com.

**Q: Can I export my data?**  
A: Yes, export all data in JSON/CSV format from Settings → Data → Export.

### Billing

**Q: What payment methods do you accept?**  
A: All major credit cards, PayPal, and wire transfer (Enterprise).

**Q: How do I add more seats?**  
A: Admins can add seats anytime; prorated charges apply.

**Q: What happens when I cancel?**  
A: Your workspace becomes read-only for 30 days, then permanently deleted.

### Security

**Q: Where is my data stored?**  
A: US (AWS us-east-1) or EU (AWS eu-central-1) based on your selection.

**Q: Do you backup data?**  
A: Yes, automated backups every 6 hours with 30-day retention.

**Q: Are you GDPR compliant?**  
A: Yes, full GDPR compliance with DPA available for signing.

---

*Last Updated: March 2026*  
*Document Version: 3.2.1*
