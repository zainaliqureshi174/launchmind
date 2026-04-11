# 🚀 LaunchMind — Multi-Agent AI Startup System

A multi-agent AI system that autonomously runs a micro-startup — from idea to product spec, code, marketing, and deployment — using collaborating LLM-powered agents.

---

## 💡 Startup Idea

A mobile platform where university students can buy and sell second-hand textbooks, with AI-powered price suggestions and instant campus-to-campus delivery coordination. The platform targets students who overpay for new textbooks and those stuck with books they no longer need.

---

## 🏗️ Agent Architecture

```
You → main.py → CEO Agent
                    │
                    ├──[task]──→ Product Agent
                    │               │
                    │           [result / revision_request]
                    │               │
                    ├──[LLM review]─┘
                    │
                    ├──[task + product_spec]──→ Engineer Agent
                    │                               │
                    │                           - GitHub Issue
                    │                           - Commits index.html
                    │                           - Opens PR
                    │                           [result: PR URL]
                    │
                    ├──[task + product_spec + PR URL]──→ Marketing Agent
                    │                                        │
                    │                                    - Sends Email (SendGrid)
                    │                                    - Posts to Slack (Block Kit)
                    │                                    [result: copy JSON]
                    │
                    ├──[html + copy + spec]──→ QA Agent
                    │                               │
                    │                           - Reviews HTML vs spec
                    │                           - Reviews marketing copy
                    │                           - Posts PR comments on GitHub
                    │                           [result: pass/fail verdict]
                    │
                    ├──[revision_request if QA fails]──→ Engineer Agent (revision)
                    │
                    └──[final summary]──→ Slack #launches
```

### Agent Responsibilities

| Agent | Role | LLM Used |
|-------|------|----------|
| CEO Agent | Orchestrator — decomposes idea, reviews outputs, triggers revisions | Groq LLaMA 3.1 |
| Product Agent | Generates product spec — personas, features, user stories | Groq LLaMA 3.1 |
| Engineer Agent | Generates HTML, creates GitHub issue, commits code, opens PR | Groq LLaMA 3.1 |
| Marketing Agent | Generates tagline, email, social posts — sends email and posts to Slack | Groq LLaMA 3.1 |
| QA Agent | Reviews HTML and copy, posts PR comments, sends verdict to CEO | Groq LLaMA 3.1 |

---

## 💬 Message Schema

Every agent-to-agent message follows this exact structure:

```json
{
  "message_id": "uuid-string",
  "from_agent": "ceo",
  "to_agent": "product",
  "message_type": "task | result | revision_request | confirmation",
  "payload": { "...": "..." },
  "timestamp": "2026-04-11T00:00:00Z",
  "parent_message_id": "optional-uuid"
}
```

---

## ⚙️ Setup Instructions

### 1. Clone the repository
```bash
git clone https://github.com/zainaliqureshi174/launchmind.git
cd launchmind
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up environment variables
```bash
cp .env.example .env
```

Fill in your API keys in `.env`:

```
GROQ_API_KEY=your_groq_api_key_here
GITHUB_TOKEN=your_github_personal_access_token
GITHUB_REPO=zainaliqureshi174/launchmind
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_CHANNEL=#launches
SENDGRID_API_KEY=SG.your-sendgrid-api-key
SENDGRID_FROM_EMAIL=your-verified-sender@email.com
TO_EMAIL=your-test-recipient@email.com
```

### 4. Run the system
```bash
python main.py
```

Or with a custom startup idea:
```bash
python main.py "Your startup idea here"
```

---

## 🌐 Platform Integrations

| Platform | What the Agent Does |
|----------|-------------------|
| **GitHub** | Engineer Agent creates an issue, commits `index.html` to a new branch `agent-landing-page`, and opens a Pull Request. QA Agent posts inline review comments on the PR. |
| **Slack** | Marketing Agent posts a Block Kit launch announcement to `#launches`. CEO Agent posts a final summary when all agents are done. |
| **SendGrid** | Marketing Agent sends a cold outreach email with LLM-generated subject line and body to a test inbox. |
| **Groq API** | All agents use `llama-3.1-8b-instant` for reasoning, generation, and review. |

---

## 🔗 Links

- **GitHub PR (opened by Engineer Agent):** https://github.com/zainaliqureshi174/launchmind/pull/2
- **GitHub Issues:** https://github.com/zainaliqureshi174/launchmind/issues

---

## 📁 Repository Structure

```
launchmind/
├── agents/
│   ├── ceo_agent.py        # Orchestrator — decomposes, reviews, coordinates
│   ├── product_agent.py    # Generates product spec
│   ├── engineer_agent.py   # Builds HTML, commits to GitHub, opens PR
│   ├── marketing_agent.py  # Sends email, posts to Slack
│   └── qa_agent.py         # Reviews HTML and copy, posts PR comments
├── main.py                 # Entry point — run this to start the system
├── message_bus.py          # Shared in-memory message bus (Python dict)
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template (no real keys)
├── .gitignore              # Excludes .env from commits
└── README.md               # This file
```

---

## 🔑 Required Environment Variables

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | Groq API key — free at console.groq.com |
| `GITHUB_TOKEN` | GitHub Personal Access Token (repo + workflow scopes) |
| `GITHUB_REPO` | Your repo in `username/repo-name` format |
| `SLACK_BOT_TOKEN` | Slack Bot Token (starts with `xoxb-`) |
| `SLACK_CHANNEL` | Slack channel (e.g. `#launches`) |
| `SENDGRID_API_KEY` | SendGrid API key — free at sendgrid.com |
| `SENDGRID_FROM_EMAIL` | Verified sender email in SendGrid |
| `TO_EMAIL` | Recipient email for cold outreach test |

---

## 👥 Group Members & Agent Assignments

| Member | Agent |
|--------|-------|
| Muhammad Zain Ali | CEO Agent + Engineer Agent |
| Muhammad Abdullah| Product Agent + Marketing Agent + QA Agent |
