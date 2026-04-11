"""
message_bus.py
--------------
A simple in-memory message bus using a shared Python dictionary.
Agents send and receive structured JSON messages through this bus.
"""

import uuid
from datetime import datetime, timezone
from collections import defaultdict

# The shared message store: { agent_name: [list of messages] }
_bus: dict = defaultdict(list)

# Full message history for logging/demo purposes
_history: list = []


def create_message(from_agent, to_agent, message_type, payload, parent_message_id=None):
    """Build a valid message object following the assignment schema."""
    msg = {
        "message_id": str(uuid.uuid4()),
        "from_agent": from_agent,
        "to_agent": to_agent,
        "message_type": message_type,  # task | result | revision_request | confirmation
        "payload": payload,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if parent_message_id:
        msg["parent_message_id"] = parent_message_id
    return msg


def send(message):
    """Place a message in the recipient's inbox and log it."""
    to = message["to_agent"]
    _bus[to].append(message)
    _history.append(message)
    print(
        f"  [BUS] {message['from_agent']} → {message['to_agent']} "
        f"({message['message_type']}) | id={message['message_id'][:8]}"
    )


def receive(agent_name):
    """Return and clear all messages waiting for agent_name."""
    messages = _bus[agent_name].copy()
    _bus[agent_name].clear()
    return messages


def get_history():
    """Return the full message history (all messages ever sent)."""
    return _history.copy()


def print_history():
    """Pretty-print every message that passed through the bus."""
    print("\n" + "=" * 60)
    print("FULL MESSAGE HISTORY")
    print("=" * 60)
    for msg in _history:
        print(f"\n[{msg['timestamp']}]")
        print(f"  FROM : {msg['from_agent']}")
        print(f"  TO   : {msg['to_agent']}")
        print(f"  TYPE : {msg['message_type']}")
        print(f"  ID   : {msg['message_id']}")
        if "parent_message_id" in msg:
            print(f"  PARENT: {msg['parent_message_id']}")
        print(f"  PAYLOAD KEYS: {list(msg['payload'].keys())}")
    print("=" * 60 + "\n")