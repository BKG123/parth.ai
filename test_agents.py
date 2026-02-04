"""
Test script for ReactiveAgent and ProactiveAgent.

Usage:
    python test_agents.py reactive <user_id> "<message>"
    python test_agents.py proactive <user_id>
"""

import asyncio
import sys
import json
from dotenv import load_dotenv

load_dotenv()


async def test_reactive(user_id: str, message: str):
    """Test ReactiveAgent with a message."""
    from ai.reactive_agent import ReactiveAgent

    print(f"\n{'='*60}")
    print(f"Testing ReactiveAgent")
    print(f"User ID: {user_id}")
    print(f"Message: {message}")
    print(f"{'='*60}\n")

    agent = ReactiveAgent(user_id=user_id)

    print("Streaming response:\n")
    response_text = ""

    async for event in agent.stream_response(prompt=message):
        if event["type"] == "text":
            print(event["content"], end="", flush=True)
            response_text += event["content"]
        elif event["type"] == "tool_call":
            print(f"\n[Tool: {event['content']}]", end="", flush=True)

    print(f"\n\n{'='*60}")
    print(f"Complete response length: {len(response_text)} chars")
    print(f"{'='*60}\n")


async def test_proactive(user_id: int):
    """Test ProactiveAgent evaluation."""
    from ai.proactive_agent import ProactiveAgent

    print(f"\n{'='*60}")
    print(f"Testing ProactiveAgent")
    print(f"User ID: {user_id}")
    print(f"{'='*60}\n")

    agent = ProactiveAgent()

    # Build context
    print("Building context...")
    context = await agent.build_context(user_id=user_id)

    print("\nContext summary:")
    print(f"  Active goals: {context.get('active_goals_count', 0)}")
    print(f"  Last message: {context.get('last_message_at', 'Never')}")
    print(
        f"  Hours since last message: {context.get('hours_since_last_message', 'N/A')}"
    )

    # Evaluate
    print("\nEvaluating decision...")
    decision = await agent.evaluate(user_id=user_id)

    print(f"\n{'='*60}")
    print("DECISION:")
    print(f"{'='*60}")
    print(json.dumps(decision, indent=2))
    print(f"{'='*60}\n")

    # Ask if should execute
    if decision["action"] != "skip":
        execute = input("\nExecute this decision? (y/n): ")
        if execute.lower() == "y":
            print("\nExecuting decision...")
            result = await agent.execute_decision(user_id=user_id, decision=decision)
            print("\nExecution result:")
            print(json.dumps(result, indent=2))


async def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    mode = sys.argv[1].lower()

    if mode == "reactive":
        if len(sys.argv) < 4:
            print("Usage: python test_agents.py reactive <user_id> \"<message>\"")
            sys.exit(1)
        user_id = sys.argv[2]
        message = sys.argv[3]
        await test_reactive(user_id, message)

    elif mode == "proactive":
        user_id = int(sys.argv[2])
        await test_proactive(user_id)

    else:
        print(f"Unknown mode: {mode}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
