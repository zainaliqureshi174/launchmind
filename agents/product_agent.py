"""
product_agent.py
----------------
The Product Agent - Thinks like a Product Manager.
Receives a task from CEO and generates a full product specification.
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
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3,
        max_tokens=1500
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


def generate_product_spec(idea, task, feedback=None):
    """Use LLM to generate a full product specification."""
    print("\n[PRODUCT] Generating product specification...")

    feedback_text = f"\nPrevious feedback to address: {feedback}" if feedback else ""

    system_prompt = """You are an experienced Product Manager. Generate a detailed product specification.
IMPORTANT: Respond ONLY with a valid JSON object. No explanation. No markdown. No backticks.
Use simple ASCII characters only. Do not use apostrophes inside string values - use alternative wording instead."""

    user_prompt = f"""Startup idea: {idea}
Task: {task}{feedback_text}

Respond with ONLY this JSON structure, filled with specific details for this startup:
{{
  "value_proposition": "one sentence describing what the product does and for whom",
  "personas": [
    {{"name": "Alex", "role": "University Student", "pain_point": "specific pain point related to the startup"}},
    {{"name": "Sam", "role": "Graduate Student", "pain_point": "specific pain point related to the startup"}}
  ],
  "features": [
    {{"name": "Feature One", "description": "what it does", "priority": 1}},
    {{"name": "Feature Two", "description": "what it does", "priority": 2}},
    {{"name": "Feature Three", "description": "what it does", "priority": 3}},
    {{"name": "Feature Four", "description": "what it does", "priority": 4}},
    {{"name": "Feature Five", "description": "what it does", "priority": 5}}
  ],
  "user_stories": [
    "As a student I want to list my textbooks so that I can earn money from unused books",
    "As a buyer I want to filter by subject so that I can find the right textbook quickly",
    "As a user I want AI price suggestions so that I can price my books competitively"
  ]
}}"""

    response = call_llm(system_prompt, user_prompt)
    spec = safe_parse_json(response)
    print("[PRODUCT] Product specification generated successfully.")
    return spec


def run():
    """Main Product Agent function."""
    print("\n" + "-"*40)
    print("PRODUCT AGENT RUNNING")
    print("-"*40)

    messages = bus.receive("product")
    if not messages:
        print("[PRODUCT] No messages received.")
        return

    for msg in messages:
        idea = msg["payload"].get("idea", "")
        task = msg["payload"].get("task", "")
        feedback = msg["payload"].get("feedback", None)

        print(f"[PRODUCT] Received {msg['message_type']} from CEO.")
        print(f"[PRODUCT] Task: {task}")
        if feedback:
            print(f"[PRODUCT] Revision feedback: {feedback}")

        spec = generate_product_spec(idea, task, feedback)

        print(f"\n[PRODUCT] Value Proposition: {spec['value_proposition']}")
        print(f"[PRODUCT] Personas: {len(spec['personas'])} defined")
        print(f"[PRODUCT] Features: {len(spec['features'])} defined")
        print(f"[PRODUCT] User Stories: {len(spec['user_stories'])} defined")

        result_msg = bus.create_message(
            from_agent="product",
            to_agent="ceo",
            message_type="result",
            payload=spec,
            parent_message_id=msg["message_id"]
        )
        bus.send(result_msg)

        confirm_msg = bus.create_message(
            from_agent="product",
            to_agent="ceo",
            message_type="confirmation",
            payload={"status": "Product spec ready", "spec_keys": list(spec.keys())},
            parent_message_id=msg["message_id"]
        )
        bus.send(confirm_msg)
        print("[PRODUCT] Spec sent to CEO successfully.")