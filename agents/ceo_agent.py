"""
ceo_agent.py
------------
The CEO Agent - Orchestrator of the entire LaunchMind system.
Uses LLM twice:
  1. To decompose the startup idea into tasks for each agent
  2. To review each agent's output and decide if revision is needed
"""

import os
import json
import re
from groq import Groq
from dotenv import load_dotenv
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
        temperature=0.3,
        max_tokens=1000
    )
    return response.choices[0].message.content


def safe_parse_json(text):
    """Robustly extract and parse JSON from LLM response."""
    text = text.strip()
    text = re.sub(r"```json", "", text)
    text = re.sub(r"```", "", text)
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass

    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    start = text.find("{")
    end = text.rfind("}") + 1
    return json.loads(text[start:end])


def decompose_idea(idea):
    """LLM CALL 1: Break the startup idea into tasks for each agent."""
    print("\n[CEO] Decomposing startup idea into tasks...")

    system_prompt = """You are the CEO of a startup. Given a startup idea, break it into tasks.
IMPORTANT: Respond ONLY with a JSON object. No explanation. No markdown. No backticks.
Use simple ASCII characters only in your response. No apostrophes inside string values."""

    user_prompt = f"""Startup idea: {idea}

Respond with ONLY this JSON, no other text:
{{"product_task": "define user personas features and product spec for this startup", "engineer_task": "build HTML landing page showing the product features and value proposition", "marketing_task": "create tagline description email and social posts for this startup"}}

Now generate your own version with specific details for this startup idea."""

    response = call_llm(system_prompt, user_prompt)
    tasks = safe_parse_json(response)
    print(f"[CEO] Tasks generated successfully.")
    print(f"[CEO] Product task: {tasks['product_task'][:80]}...")
    print(f"[CEO] Engineer task: {tasks['engineer_task'][:80]}...")
    print(f"[CEO] Marketing task: {tasks['marketing_task'][:80]}...")
    return tasks


def review_output(agent_name, output, original_task):
    """LLM CALL 2: Review an agent's output and decide if it needs revision."""
    print(f"\n[CEO] Reviewing output from {agent_name} agent...")

    system_prompt = """You are a strict CEO reviewing work from your team.
IMPORTANT: Respond ONLY with a JSON object. No explanation. No markdown. No backticks.
Use simple ASCII characters only. No apostrophes inside string values."""

    user_prompt = f"""Task given to {agent_name} agent: {original_task}

Output received has these keys: {list(output.keys()) if isinstance(output, dict) else 'non-dict'}

Is this output acceptable? It must be specific and complete.
Respond with ONLY this JSON, no other text:
{{"verdict": "pass", "reason": "output is complete and specific", "feedback": ""}}

Or if failing:
{{"verdict": "fail", "reason": "specific reason it failed", "feedback": "specific improvement needed"}}"""

    response = call_llm(system_prompt, user_prompt)
    review = safe_parse_json(response)
    print(f"[CEO] Review verdict for {agent_name}: {review['verdict'].upper()}")
    print(f"[CEO] Reason: {review['reason']}")
    return review


def post_final_summary(idea, product_result, engineer_result, marketing_result, qa_result=None):
    """Post the final summary to Slack."""
    import requests

    pr_url = engineer_result.get("pr_url", "N/A") if engineer_result else "N/A"
    issue_url = engineer_result.get("issue_url", "N/A") if engineer_result else "N/A"
    tagline = marketing_result.get("tagline", "N/A") if marketing_result else "N/A"
    qa_verdict = qa_result.get("overall_verdict", "N/A").upper() if qa_result else "N/A"

    payload = {
        "channel": os.getenv("SLACK_CHANNEL", "#launches"),
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🚀 LaunchMind — Startup Launch Complete!"}
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Idea:* {idea}"}
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Tagline:* _{tagline}_"}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*GitHub PR:* <{pr_url}|View PR>"},
                    {"type": "mrkdwn", "text": f"*GitHub Issue:* <{issue_url}|View Issue>"}
                ]
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"✅ All agents completed! QA Verdict: *{qa_verdict}*"}
            }
        ]
    }

    response = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {os.getenv('SLACK_BOT_TOKEN')}"},
        json=payload
    )
    if response.json().get("ok"):
        print("[CEO] Final summary posted to Slack successfully!")
    else:
        print(f"[CEO] Slack post failed: {response.json()}")


def run(idea):
    """Main CEO agent function - orchestrates the entire pipeline."""
    print("\n" + "="*60)
    print("CEO AGENT STARTING")
    print("="*60)
    print(f"[CEO] Received startup idea: {idea}")

    # ── STEP 1: Decompose idea into tasks (LLM Call 1) ──
    tasks = decompose_idea(idea)

    # ── STEP 2: Send task to Product Agent ──
    product_msg = bus.create_message(
        from_agent="ceo",
        to_agent="product",
        message_type="task",
        payload={"idea": idea, "task": tasks["product_task"]}
    )
    bus.send(product_msg)

    # ── STEP 3: Run Product Agent ──
    print("\n[CEO] Waiting for Product Agent...")
    from agents.product_agent import run as run_product
    run_product()

    product_messages = bus.receive("ceo")
    product_result = None
    for msg in product_messages:
        if msg["from_agent"] == "product" and msg["message_type"] == "result":
            product_result = msg["payload"]
            break

    if not product_result:
        print("[CEO] ERROR: No response from Product Agent!")
        return

    # ── STEP 4: Review Product output (LLM Call 2) ──
    review = review_output("product", product_result, tasks["product_task"])

    if review["verdict"] == "fail":
        print(f"\n[CEO] Product output needs revision. Sending revision request...")
        revision_msg = bus.create_message(
            from_agent="ceo",
            to_agent="product",
            message_type="revision_request",
            payload={
                "idea": idea,
                "task": tasks["product_task"],
                "feedback": review["feedback"]
            },
            parent_message_id=product_msg["message_id"]
        )
        bus.send(revision_msg)

        run_product()
        product_messages = bus.receive("ceo")
        for msg in product_messages:
            if msg["from_agent"] == "product" and msg["message_type"] == "result":
                product_result = msg["payload"]
                break
        print("[CEO] Product agent revised its output.")

    print("\n[CEO] Product spec approved! Sending to Engineer Agent...")

    # ── STEP 5: Send to Engineer Agent ──
    engineer_msg = bus.create_message(
        from_agent="ceo",
        to_agent="engineer",
        message_type="task",
        payload={
            "idea": idea,
            "task": tasks["engineer_task"],
            "product_spec": product_result
        }
    )
    bus.send(engineer_msg)

    # ── STEP 6: Run Engineer Agent ──
    print("\n[CEO] Running Engineer Agent...")
    from agents.engineer_agent import run as run_engineer
    run_engineer()

    engineer_messages = bus.receive("ceo")
    engineer_result = None
    for msg in engineer_messages:
        if msg["from_agent"] == "engineer" and msg["message_type"] == "result":
            engineer_result = msg["payload"]
            break

    pr_url = engineer_result.get("pr_url", "N/A") if engineer_result else "N/A"
    print(f"\n[CEO] Engineer done. PR URL: {pr_url}")

    # ── STEP 7: Send to Marketing Agent ──
    print("\n[CEO] Sending task to Marketing Agent...")
    marketing_msg = bus.create_message(
        from_agent="ceo",
        to_agent="marketing",
        message_type="task",
        payload={
            "idea": idea,
            "task": tasks["marketing_task"],
            "product_spec": product_result,
            "pr_url": pr_url
        }
    )
    bus.send(marketing_msg)

    # ── STEP 8: Run Marketing Agent ──
    print("\n[CEO] Running Marketing Agent...")
    from agents.marketing_agent import run as run_marketing
    run_marketing()

    marketing_messages = bus.receive("ceo")
    marketing_result = None
    for msg in marketing_messages:
        if msg["from_agent"] == "marketing" and msg["message_type"] == "result":
            marketing_result = msg["payload"]
            break

    # ── STEP 9: Post final summary to Slack ──
    print("\n[CEO] All agents done! Posting final summary to Slack...")
    post_final_summary(idea, product_result, engineer_result, marketing_result)

    print("\n" + "="*60)
    print("CEO AGENT DONE - All tasks complete!")
    print("="*60)

    bus.print_history()