# """
# ceo_agent.py
# ------------
# The CEO Agent - Orchestrator of the entire LaunchMind system.
# Uses LLM twice:
#   1. To decompose the startup idea into tasks for each agent
#   2. To review each agent's output and decide if revision is needed
# """

# import os
# import json
# import re
# from groq import Groq
# from dotenv import load_dotenv
# import message_bus as bus

# load_dotenv()

# client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# def call_llm(system_prompt, user_prompt):
#     """Call Groq LLM and return the response text."""
#     response = client.chat.completions.create(
#         model="llama-3.1-8b-instant",
#         messages=[
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": user_prompt}
#         ],
#         temperature=0.3,
#         max_tokens=1000
#     )
#     return response.choices[0].message.content


# def safe_parse_json(text):
#     """Robustly extract and parse JSON from LLM response."""
#     text = text.strip()

#     # Remove markdown code blocks
#     text = re.sub(r"```json", "", text)
#     text = re.sub(r"```", "", text)
#     text = text.strip()

#     # Try direct parse first
#     try:
#         return json.loads(text)
#     except json.JSONDecodeError:
#         pass

#     # Find first { and last } 
#     start = text.find("{")
#     end = text.rfind("}") + 1
#     if start != -1 and end > start:
#         try:
#             return json.loads(text[start:end])
#         except json.JSONDecodeError:
#             pass

#     # Last resort: replace smart quotes
#     text = text.replace("\u2018", "'").replace("\u2019", "'")
#     text = text.replace("\u201c", '"').replace("\u201d", '"')
#     start = text.find("{")
#     end = text.rfind("}") + 1
#     return json.loads(text[start:end])


# def decompose_idea(idea):
#     """LLM CALL 1: Break the startup idea into tasks for each agent."""
#     print("\n[CEO] Decomposing startup idea into tasks...")

#     system_prompt = """You are the CEO of a startup. Given a startup idea, break it into tasks.
# IMPORTANT: Respond ONLY with a JSON object. No explanation. No markdown. No backticks.
# Use simple ASCII characters only in your response. No apostrophes inside string values."""

#     user_prompt = f"""Startup idea: {idea}

# Respond with ONLY this JSON, no other text:
# {{"product_task": "define user personas features and product spec for this startup", "engineer_task": "build HTML landing page showing the product features and value proposition", "marketing_task": "create tagline description email and social posts for this startup"}}

# Now generate your own version with specific details for this startup idea."""

#     response = call_llm(system_prompt, user_prompt)
#     tasks = safe_parse_json(response)
#     print(f"[CEO] Tasks generated successfully.")
#     print(f"[CEO] Product task: {tasks['product_task'][:80]}...")
#     print(f"[CEO] Engineer task: {tasks['engineer_task'][:80]}...")
#     print(f"[CEO] Marketing task: {tasks['marketing_task'][:80]}...")
#     return tasks


# def review_output(agent_name, output, original_task):
#     """LLM CALL 2: Review an agent's output and decide if it needs revision."""
#     print(f"\n[CEO] Reviewing output from {agent_name} agent...")

#     system_prompt = """You are a strict CEO reviewing work from your team.
# IMPORTANT: Respond ONLY with a JSON object. No explanation. No markdown. No backticks.
# Use simple ASCII characters only. No apostrophes inside string values."""

#     user_prompt = f"""Task given to {agent_name} agent: {original_task}

# Output received has these keys: {list(output.keys()) if isinstance(output, dict) else 'non-dict'}

# Is this output acceptable? It must be specific and complete.
# Respond with ONLY this JSON, no other text:
# {{"verdict": "pass", "reason": "output is complete and specific", "feedback": ""}}

# Or if failing:
# {{"verdict": "fail", "reason": "specific reason it failed", "feedback": "specific improvement needed"}}"""

#     response = call_llm(system_prompt, user_prompt)
#     review = safe_parse_json(response)
#     print(f"[CEO] Review verdict for {agent_name}: {review['verdict'].upper()}")
#     print(f"[CEO] Reason: {review['reason']}")
#     return review


# def post_final_summary(idea, product_result, engineer_result, marketing_result):
#     """Post the final summary to Slack."""
#     import requests

#     pr_url = engineer_result.get("pr_url", "N/A") if engineer_result else "N/A"
#     issue_url = engineer_result.get("issue_url", "N/A") if engineer_result else "N/A"
#     tagline = marketing_result.get("tagline", "N/A") if marketing_result else "N/A"

#     payload = {
#         "channel": os.getenv("SLACK_CHANNEL", "#launches"),
#         "blocks": [
#             {
#                 "type": "header",
#                 "text": {"type": "plain_text", "text": "🚀 LaunchMind — Startup Launch Complete!"}
#             },
#             {
#                 "type": "section",
#                 "text": {"type": "mrkdwn", "text": f"*Idea:* {idea}"}
#             },
#             {
#                 "type": "section",
#                 "text": {"type": "mrkdwn", "text": f"*Tagline:* _{tagline}_"}
#             },
#             {
#                 "type": "section",
#                 "fields": [
#                     {"type": "mrkdwn", "text": f"*GitHub PR:* <{pr_url}|View PR>"},
#                     {"type": "mrkdwn", "text": f"*GitHub Issue:* <{issue_url}|View Issue>"}
#                 ]
#             },
#             {
#                 "type": "section",
#                 "text": {"type": "mrkdwn", "text": "✅ All agents completed successfully!"}
#             }
#         ]
#     }

#     response = requests.post(
#         "https://slack.com/api/chat.postMessage",
#         headers={"Authorization": f"Bearer {os.getenv('SLACK_BOT_TOKEN')}"},
#         json=payload
#     )
#     if response.json().get("ok"):
#         print("[CEO] Final summary posted to Slack successfully!")
#     else:
#         print(f"[CEO] Slack post failed: {response.json()}")


# def run(idea):
#     """Main CEO agent function - orchestrates the entire pipeline."""
#     print("\n" + "="*60)
#     print("CEO AGENT STARTING")
#     print("="*60)
#     print(f"[CEO] Received startup idea: {idea}")

#     # ── STEP 1: Decompose idea into tasks (LLM Call 1) ──
#     tasks = decompose_idea(idea)

#     # ── STEP 2: Send task to Product Agent ──
#     product_msg = bus.create_message(
#         from_agent="ceo",
#         to_agent="product",
#         message_type="task",
#         payload={"idea": idea, "task": tasks["product_task"]}
#     )
#     bus.send(product_msg)

#     # ── STEP 3: Run Product Agent ──
#     print("\n[CEO] Waiting for Product Agent...")
#     from agents.product_agent import run as run_product
#     run_product()

#     # Get product result
#     product_messages = bus.receive("ceo")
#     product_result = None
#     for msg in product_messages:
#         if msg["from_agent"] == "product" and msg["message_type"] == "result":
#             product_result = msg["payload"]
#             break

#     if not product_result:
#         print("[CEO] ERROR: No response from Product Agent!")
#         return

#     # ── STEP 4: Review Product output (LLM Call 2) ──
#     review = review_output("product", product_result, tasks["product_task"])

#     if review["verdict"] == "fail":
#         print(f"\n[CEO] Product output needs revision. Sending revision request...")
#         revision_msg = bus.create_message(
#             from_agent="ceo",
#             to_agent="product",
#             message_type="revision_request",
#             payload={
#                 "idea": idea,
#                 "task": tasks["product_task"],
#                 "feedback": review["feedback"]
#             },
#             parent_message_id=product_msg["message_id"]
#         )
#         bus.send(revision_msg)

#         run_product()
#         product_messages = bus.receive("ceo")
#         for msg in product_messages:
#             if msg["from_agent"] == "product" and msg["message_type"] == "result":
#                 product_result = msg["payload"]
#                 break
#         print("[CEO] Product agent revised its output.")

#     print("\n[CEO] Product spec approved! Sending to Engineer Agent...")

#     # ── STEP 5: Send to Engineer Agent ──
#     engineer_msg = bus.create_message(
#         from_agent="ceo",
#         to_agent="engineer",
#         message_type="task",
#         payload={
#             "idea": idea,
#             "task": tasks["engineer_task"],
#             "product_spec": product_result
#         }
#     )
#     bus.send(engineer_msg)

#     # ── STEP 6: Run Engineer Agent ──
#     print("\n[CEO] Running Engineer Agent...")
#     from agents.engineer_agent import run as run_engineer
#     run_engineer()

#     engineer_messages = bus.receive("ceo")
#     engineer_result = None
#     for msg in engineer_messages:
#         if msg["from_agent"] == "engineer" and msg["message_type"] == "result":
#             engineer_result = msg["payload"]
#             break

#     pr_url = engineer_result.get("pr_url", "N/A") if engineer_result else "N/A"
#     print(f"\n[CEO] Engineer done. PR URL: {pr_url}")

#     # ── STEP 7: Send to Marketing Agent ──
#     print("\n[CEO] Sending task to Marketing Agent...")
#     marketing_msg = bus.create_message(
#         from_agent="ceo",
#         to_agent="marketing",
#         message_type="task",
#         payload={
#             "idea": idea,
#             "task": tasks["marketing_task"],
#             "product_spec": product_result,
#             "pr_url": pr_url
#         }
#     )
#     bus.send(marketing_msg)

#     # ── STEP 8: Run Marketing Agent ──
#     print("\n[CEO] Running Marketing Agent...")
#     from agents.marketing_agent import run as run_marketing
#     run_marketing()

#     marketing_messages = bus.receive("ceo")
#     marketing_result = None
#     for msg in marketing_messages:
#         if msg["from_agent"] == "marketing" and msg["message_type"] == "result":
#             marketing_result = msg["payload"]
#             break

#     # ── STEP 9: Post final summary to Slack ──
#     print("\n[CEO] All agents done! Posting final summary to Slack...")
#     post_final_summary(idea, product_result, engineer_result, marketing_result)

#     print("\n" + "="*60)
#     print("CEO AGENT DONE - All tasks complete!")
#     print("="*60)

#     bus.print_history()

"""
ceo_agent.py
------------
The CEO Agent - Orchestrator of the entire LaunchMind system.
Uses LLM twice (minimum):
  1. To decompose the startup idea into tasks for each agent
  2. To review each agent's output and decide if revision is needed
Also orchestrates the QA agent review loop for bonus marks.
"""

import os
import re
import json
import time
from groq import Groq
from dotenv import load_dotenv
import message_bus as bus

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def call_llm(system_prompt, user_prompt):
    """Call Groq LLM and return the response text."""
    time.sleep(15)  # Avoid Groq TPM rate limit (6000 tokens/min on free tier)
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=1000
    )
    return response.choices[0].message.content


def safe_parse_json(response):
    """Robustly parse JSON from LLM response, handling control chars and markdown fences."""
    # Strip markdown fences
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
        # Fallback: extract first {...} block
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', match.group())
            return json.loads(cleaned)
        raise


def decompose_idea(idea):
    """LLM CALL 1: Break the startup idea into tasks for each agent."""
    print("\n[CEO] Decomposing startup idea into tasks...")

    system_prompt = """You are the CEO of a startup. Given a startup idea, you must break it down 
into specific tasks for three teams: product, engineer, and marketing.
Respond ONLY with a valid JSON object, no extra text, no markdown, no backticks.
The JSON must have exactly these keys: product_task, engineer_task, marketing_task.
Each value should be a specific instruction string for that team."""

    user_prompt = f"""Startup idea: {idea}

Generate specific tasks for each team based on this idea.
Respond with only this JSON format:
{{
  "product_task": "specific instruction for product team",
  "engineer_task": "specific instruction for engineer team",
  "marketing_task": "specific instruction for marketing team"
}}"""

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
Evaluate if the output is specific, complete, and relevant to the task given.
Respond ONLY with a valid JSON object, no extra text, no markdown, no backticks.
The JSON must have exactly these keys: verdict (pass or fail), reason (one sentence), 
feedback (specific improvement if fail, empty string if pass)."""

    user_prompt = f"""Task given to {agent_name} agent: {original_task}

Output received: {json.dumps(output)[:1500]}

Is this output acceptable? Be strict - it must be specific and directly relevant to the startup.
Respond with only this JSON format:
{{
  "verdict": "pass" or "fail",
  "reason": "one sentence explanation",
  "feedback": "specific improvement needed (empty string if pass)"
}}"""

    response = call_llm(system_prompt, user_prompt)
    review = safe_parse_json(response)

    print(f"[CEO] Review verdict for {agent_name}: {review['verdict'].upper()}")
    print(f"[CEO] Reason: {review['reason']}")
    return review


def run(idea):
    """Main CEO agent function - orchestrates the entire pipeline."""
    print("\n" + "="*60)
    print("CEO AGENT STARTING")
    print("="*60)
    print(f"[CEO] Received startup idea: {idea}")

    # ── STEP 1: Decompose idea into tasks ──
    tasks = decompose_idea(idea)

    # ── STEP 2: Send task to Product Agent ──
    product_msg = bus.create_message(
        from_agent="ceo",
        to_agent="product",
        message_type="task",
        payload={
            "idea": idea,
            "task": tasks["product_task"]
        }
    )
    bus.send(product_msg)

    # ── STEP 3: Run Product Agent ──
    print("\n[CEO] Waiting for Product Agent...")
    from agents.product_agent import run as run_product
    run_product()

    # Get product result
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

        # Run product agent again with revision
        run_product()
        product_messages = bus.receive("ceo")
        for msg in product_messages:
            if msg["from_agent"] == "product" and msg["message_type"] == "result":
                product_result = msg["payload"]
                break

        print("[CEO] Product agent revised its output.")

    print("\n[CEO] Product spec approved! Sending to Engineer Agent...")

    # ── STEP 5: Send product spec to Engineer Agent ──
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

    # Collect engineer result
    engineer_messages = bus.receive("ceo")
    engineer_result = None
    for msg in engineer_messages:
        if msg["from_agent"] == "engineer" and msg["message_type"] == "result":
            engineer_result = msg["payload"]
            break

    if not engineer_result:
        print("[CEO] WARNING: No response from Engineer Agent.")
        engineer_result = {"pr_url": "N/A", "issue_url": "N/A"}

    pr_url = engineer_result.get("pr_url", "N/A")
    print(f"\n[CEO] Engineer done. PR URL: {pr_url}")

    # ── STEP 7: Send task to Marketing Agent (with PR URL) ──
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

    # Collect marketing result
    marketing_messages = bus.receive("ceo")
    marketing_result = None
    for msg in marketing_messages:
        if msg["from_agent"] == "marketing" and msg["message_type"] == "result":
            marketing_result = msg["payload"]
            break

    # ── STEP 9: Run QA Agent (bonus) ──
    print("\n[CEO] Sending outputs to QA Agent for review...")
    html_content = engineer_result.get("html_content", "")

    qa_msg = bus.create_message(
        from_agent="ceo",
        to_agent="qa",
        message_type="task",
        payload={
            "html_content": html_content,
            "marketing_copy": marketing_result or {},
            "product_spec": product_result,
            "pr_url": pr_url
        }
    )
    bus.send(qa_msg)

    from agents.qa_agent import run as run_qa
    run_qa()

    # Collect QA result
    qa_messages = bus.receive("ceo")
    qa_result = None
    for msg in qa_messages:
        if msg["from_agent"] == "qa" and msg["message_type"] == "result":
            qa_result = msg["payload"]
            break

    # ── STEP 10: If QA fails, trigger revision ──
    if qa_result and qa_result.get("overall_verdict") == "fail":
        print("\n[CEO] QA failed! Sending revision request to Engineer...")

        html_issues = qa_result.get("html_review", {}).get("issues", [])
        feedback = "; ".join(html_issues) if html_issues else "Improve HTML quality and alignment with product spec."

        engineer_revision_msg = bus.create_message(
            from_agent="ceo",
            to_agent="engineer",
            message_type="revision_request",
            payload={
                "idea": idea,
                "task": tasks["engineer_task"],
                "product_spec": product_result,
                "feedback": feedback
            },
            parent_message_id=engineer_msg["message_id"]
        )
        bus.send(engineer_revision_msg)

        run_engineer()

        # Collect revised engineer result
        revised_messages = bus.receive("ceo")
        for msg in revised_messages:
            if msg["from_agent"] == "engineer" and msg["message_type"] == "result":
                engineer_result = msg["payload"]
                pr_url = engineer_result.get("pr_url", pr_url)
                break

        print("[CEO] Engineer revised its output after QA feedback.")

    # ── STEP 11: Post final summary to Slack ──
    print("\n[CEO] All agents done! Posting final summary to Slack...")
    post_final_summary(idea, product_result, engineer_result, marketing_result, qa_result)

    print("\n" + "="*60)
    print("CEO AGENT DONE - All tasks complete!")
    print("="*60)

    # Print full message history for demo
    bus.print_history()


def post_final_summary(idea, product_result, engineer_result, marketing_result, qa_result=None):
    """Post the final summary to Slack."""
    import requests

    pr_url = engineer_result.get("pr_url", "N/A") if engineer_result else "N/A"
    issue_url = engineer_result.get("issue_url", "N/A") if engineer_result else "N/A"
    tagline = marketing_result.get("tagline", "N/A") if marketing_result else "N/A"
    qa_verdict = qa_result.get("overall_verdict", "N/A").upper() if qa_result else "N/A"

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "🏁 LaunchMind — All Agents Complete!"}
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Startup Idea:* {idea}"}
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Tagline:* _{tagline}_"}
        },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*GitHub PR:* <{pr_url}|View Pull Request>"},
                {"type": "mrkdwn", "text": f"*GitHub Issue:* <{issue_url}|View Issue>"}
            ]
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*QA Verdict:* {qa_verdict}"},
                {"type": "mrkdwn", "text": "*Pipeline:* ✅ Complete"}
            ]
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": "Orchestrated by *CEO Agent* | LaunchMind Multi-Agent System"}
            ]
        }
    ]

    payload = {
        "channel": os.getenv("SLACK_CHANNEL", "#launches"),
        "blocks": blocks
    }

    response = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={
            "Authorization": f"Bearer {os.getenv('SLACK_BOT_TOKEN')}",
            "Content-Type": "application/json"
        },
        json=payload
    )

    if response.json().get("ok"):
        print("[CEO] Final summary posted to Slack successfully!")
    else:
        print(f"[CEO] Slack post failed: {response.json()}")