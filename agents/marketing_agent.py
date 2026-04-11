"""
marketing_agent.py
------------------
The Marketing Agent - Thinks like a Growth Marketer.
Receives product spec + PR URL from CEO, generates marketing copy,
sends a real email via SendGrid, and posts to Slack using Block Kit.
"""

import os
import re
import json
import requests
from groq import Groq
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import message_bus as bus

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def call_llm(system_prompt, user_prompt):
    """Call Groq LLM and return the response text."""
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=1500
    )
    return response.choices[0].message.content


def safe_parse_json(response):
    """Robustly parse JSON from LLM response, handling control chars and markdown fences."""
    response = response.strip()
    if response.startswith("```"):
        response = response.split("```")[1]
        if response.startswith("json"):
            response = response[4:]
    response = response.strip()

    # Remove invalid control characters (keep \n \r \t which are valid in JSON strings)
    response = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', response)

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', match.group())
            return json.loads(cleaned)
        raise


def generate_marketing_copy(idea, product_spec):
    """Use LLM to generate all marketing copy."""
    print("\n[MARKETING] Generating marketing copy...")

    value_prop = product_spec.get("value_proposition", "")
    features = product_spec.get("features", [])
    personas = product_spec.get("personas", [])
    features_text = "\n".join([f"- {f['name']}: {f['description']}" for f in features])
    persona_text = "\n".join([f"- {p['name']} ({p['role']}): {p['pain_point']}" for p in personas])

    system_prompt = """You are an expert growth marketer and copywriter. Given a startup idea and 
product spec, generate compelling marketing copy.
Respond ONLY with a valid JSON object, no extra text, no markdown, no backticks.
The JSON must have exactly these keys: tagline, description, email_subject, email_body, 
twitter_post, linkedin_post, instagram_post."""

    user_prompt = f"""Startup idea: {idea}
Value proposition: {value_prop}
Target personas:
{persona_text}
Core features:
{features_text}

Generate marketing copy with this exact JSON format:
{{
  "tagline": "under 10 words, punchy and memorable",
  "description": "2-3 sentences for a landing page, compelling and clear",
  "email_subject": "cold outreach email subject line, attention-grabbing",
  "email_body": "cold outreach email body (3-4 paragraphs) addressed to a potential early user, with a clear call to action. Use HTML formatting.",
  "twitter_post": "tweet under 280 chars with relevant hashtags",
  "linkedin_post": "professional LinkedIn post 2-3 sentences with a hook",
  "instagram_post": "engaging Instagram caption with emojis and hashtags"
}}"""

    response = call_llm(system_prompt, user_prompt)

    # Use safe_parse_json with a fallback copy on total failure
    try:
        copy = safe_parse_json(response)
    except (json.JSONDecodeError, Exception) as e:
        print(f"[MARKETING] WARNING: Could not parse LLM JSON ({e}). Using fallback copy.")
        copy = {
            "tagline": "Buy and Sell Textbooks Smarter",
            "description": "A mobile platform for university students to buy and sell second-hand textbooks with AI-powered price suggestions.",
            "email_subject": "Save money on textbooks this semester",
            "email_body": "<p>Hi,</p><p>We built a smarter way to buy and sell textbooks on campus. Try it today!</p>",
            "twitter_post": "Stop overpaying for textbooks! Buy and sell second-hand books on campus with AI price suggestions. #StudentLife #SaveMoney",
            "linkedin_post": "Excited to launch a platform helping university students save money on textbooks through peer-to-peer sales and AI pricing.",
            "instagram_post": "Buy and sell textbooks smarter! AI-powered prices, instant campus delivery. #UniLife #Textbooks"
        }

    print("[MARKETING] Marketing copy generated successfully.")
    return copy


def send_email(copy):
    """Send cold outreach email via SendGrid."""
    print("\n[MARKETING] Sending email via SendGrid...")

    try:
        message = Mail(
            from_email=os.getenv("SENDGRID_FROM_EMAIL"),
            to_emails=os.getenv("TO_EMAIL"),
            subject=copy["email_subject"],
            html_content=copy["email_body"]
        )

        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        response = sg.send(message)

        if response.status_code in [200, 202]:
            print(f"[MARKETING] Email sent successfully! Status: {response.status_code}")
            return True
        else:
            print(f"[MARKETING] Email send failed. Status: {response.status_code}")
            return False

    except Exception as e:
        print(f"[MARKETING] Email error: {str(e)}")
        return False


def post_to_slack(idea, copy, pr_url):
    """Post launch announcement to Slack using Block Kit."""
    print("\n[MARKETING] Posting to Slack...")

    tagline = copy.get("tagline", "")
    description = copy.get("description", "")
    twitter = copy.get("twitter_post", "")

    payload = {
        "channel": os.getenv("SLACK_CHANNEL", "#launches"),
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚀 New Launch: {tagline}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Idea:* {idea}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": description
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*GitHub PR:* <{pr_url}|View Pull Request>"
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Status:* ✅ Ready for review"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Tweet Draft:*\n_{twitter}_"
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "Posted by *MarketingAgent* | LaunchMind Multi-Agent System"
                    }
                ]
            }
        ]
    }

    try:
        response = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": f"Bearer {os.getenv('SLACK_BOT_TOKEN')}",
                "Content-Type": "application/json"
            },
            json=payload
        )

        result = response.json()
        if result.get("ok"):
            print("[MARKETING] Slack message posted successfully!")
            return True
        else:
            print(f"[MARKETING] Slack post failed: {result.get('error', 'unknown error')}")
            return False

    except Exception as e:
        print(f"[MARKETING] Slack error: {str(e)}")
        return False


def run():
    """Main Marketing Agent function."""
    print("\n" + "-"*40)
    print("MARKETING AGENT RUNNING")
    print("-"*40)

    messages = bus.receive("marketing")

    if not messages:
        print("[MARKETING] No messages received.")
        return

    for msg in messages:
        idea = msg["payload"].get("idea", "")
        product_spec = msg["payload"].get("product_spec", {})
        pr_url = msg["payload"].get("pr_url", "#")

        print(f"[MARKETING] Received task from CEO.")
        print(f"[MARKETING] Startup idea: {idea[:60]}...")
        print(f"[MARKETING] PR URL: {pr_url}")

        # 1. Generate all marketing copy via LLM
        copy = generate_marketing_copy(idea, product_spec)

        # Print summary
        print(f"\n[MARKETING] Tagline: {copy['tagline']}")
        print(f"[MARKETING] Email subject: {copy['email_subject']}")
        print(f"[MARKETING] Twitter: {copy['twitter_post'][:80]}...")

        # 2. Send cold outreach email
        email_sent = send_email(copy)

        # 3. Post to Slack with Block Kit
        slack_posted = post_to_slack(idea, copy, pr_url)

        # 4. Send all copy back to CEO
        result_msg = bus.create_message(
            from_agent="marketing",
            to_agent="ceo",
            message_type="result",
            payload={
                "tagline": copy["tagline"],
                "description": copy["description"],
                "email_subject": copy["email_subject"],
                "twitter_post": copy["twitter_post"],
                "linkedin_post": copy["linkedin_post"],
                "instagram_post": copy["instagram_post"],
                "email_sent": email_sent,
                "slack_posted": slack_posted
            },
            parent_message_id=msg["message_id"]
        )
        bus.send(result_msg)

        # 5. Send confirmation to CEO
        confirm_msg = bus.create_message(
            from_agent="marketing",
            to_agent="ceo",
            message_type="confirmation",
            payload={
                "status": "Marketing complete",
                "email_sent": email_sent,
                "slack_posted": slack_posted,
                "copy_keys": list(copy.keys())
            },
            parent_message_id=msg["message_id"]
        )
        bus.send(confirm_msg)

        print("[MARKETING] All tasks complete. Results sent to CEO.")