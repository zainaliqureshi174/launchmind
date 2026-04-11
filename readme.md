# LaunchMind 🚀
### A Multi-Agent AI System That Autonomously Runs a Micro-Startup

LaunchMind is a team of 5 collaborating AI agents that take a startup idea from concept to code, marketing, and deployment — without any human intervention after the initial idea is given.

---

## 💡 Startup Idea

A mobile platform where university students can buy and sell second-hand textbooks, with AI-powered price suggestions and instant campus-to-campus delivery coordination.

---

## 🏗️ Agent Architecture

```
You → main.py → CEO Agent
                    │
                    ├──[task]──→ Product Agent
                    │               │
                    │           [result/revision]
                    │               │
                    ├──[review]─────┘
                    │
                    ├──[task + product_spec]──→ Engineer Agent
                    │                               │
                    │                           - GitHub Issue
                    │                           - Commits HTML
                    │                           - Opens PR
                    │                           [result: PR URL]
                    │
                    ├──[task + product_spec + PR URL]──→ Marketing Agent
                    │                                        │
                    │                                    - Sends Email
                    │                                    - Posts to Slack
                    │                                    [result: copy]
                    │
                    └──[final summary]──→ Slack #launches
```

### Agent Responsibilities

| Agent | Role | LLM Used |
|-------|------|----------|
| CEO Agent | Orchestrator — decomposes idea, reviews outputs, triggers revisions | Groq (LLaMA 3.1) |
| Product Agent | Generates product spec — personas, features, user stories | Groq (LLaMA 3.1) |
| Engineer Agent | Generates HTML landing page, creates GitHub issue, commits code, opens PR | Groq (LLaMA 3.1) |
| Marketing Agent | Generates tagline, email, social posts — sends email and posts to Slack | Groq (LLaMA 3.1) |
| QA Agent | Reviews HTML and marketing copy, posts PR comments, sends verdict to CEO | Groq (LLaMA 3.1) |

---

## 💬 Message Schema

Every message between agents follows this structure:

```json
{
  "message_id": "uuid",
  "from_agent": "ceo",
  "to_agent": "product",
  "message_type": "task | result | revision_request | confirmation",
  "payload": { },
  "timestamp": "2026-04-11T00:00:00Z",
  "parent_message_id": "uuid (optional)"
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
GITHUB_TOKEN=your_github_personal_access_token
GITHUB_REPO=zainaliqureshi174/launchmind
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_CHANNEL=#launches
SENDGRID_API_KEY=SG.your-sendgrid-api-key
SENDGRID_FROM_EMAIL=your-verified-sender@email.com
TO_EMAIL=your-test-recipient@email.com
GROQ_API_KEY=your-groq-api-key
```

### 4. Run the system
```bash
python main.py
```

Or with a custom idea:
```bash
python main.py "Your startup idea here"
```

---

## 🌐 Platform Integrations

| Platform | What the Agent Does |
|----------|-------------------|
| **GitHub** | Engineer Agent creates an issue, commits `index.html` to a new branch, and opens a Pull Request |
| **Slack** | Marketing Agent posts a Block Kit launch announcement to `#launches`. CEO posts a final summary. |
| **SendGrid** | Marketing Agent sends a cold outreach email with LLM-generated subject and body |
| **Groq API** | All agents use LLaMA 3.1 for reasoning, generation, and review |

---

## 🔗 Links

- **GitHub PR (Engineer Agent):** https://github.com/zainaliqureshi174/launchmind/pull/2
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
├── message_bus.py          # Shared in-memory message bus
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── .gitignore              # Excludes .env from commits
└── README.md               # This file
```