"""
demo.py

Command-Line Interface (CLI) Demo for the Hybrid v2 AI Customer Support Agent.
Interactively processes customer messages using TF-IDF intent routing,
FAISS semantic retrieval, local Ollama response generation, and 3-tier
context-aware escalation guardrails.
"""

import sys
from src.llm.hybrid_agent import HybridSupportAgent


def print_header() -> None:
    print("\n" + "=" * 40)
    print(" AI CUSTOMER SUPPORT AGENT — HYBRID V2")
    print("=" * 40)
    print("Type your inquiry below. Type 'help' for guidance or 'exit'/'quit' to exit.\n")


def print_help() -> None:
    print("\n[HELP]")
    print("- Enter any customer message (e.g. 'My package was supposed to arrive yesterday and still hasn\'t come.')")
    print("- The agent will classify the intent, decide whether to auto-handle or escalate,")
    print("  and generate an empathetic, policy-compliant draft response.")
    print("- Commands:")
    print("    help : Show this help message")
    print("    exit : Exit the CLI demo\n")


def format_result(result: dict) -> None:
    intent = result.get("intent", "unknown")
    escalation = result.get("escalation_decision", "AUTO_HANDLE")
    reason = result.get("escalation_reason", "")
    draft = result.get("draft_response", "")

    print("\n" + "-" * 40)
    print(f"INTENT       : {intent}")
    print(f"DECISION     : {escalation}\n")
    print("REASON")
    print(f"{reason}\n")
    print("DRAFT RESPONSE")
    print(f"{draft}")
    print("-" * 40 + "\n")


def main() -> None:
    print_header()
    
    # Initialize the Hybrid Support Agent (loads TF-IDF model, FAISS index, Ollama client)
    print("Initializing Hybrid Support Agent...", end=" ", flush=True)
    try:
        agent = HybridSupportAgent()
        print("Ready!\n")
    except Exception as e:
        print(f"\n[ERROR] Failed to initialize agent: {e}")
        sys.exit(1)

    while True:
        try:
            print("Customer:")
            user_input = input("> ").strip()
            
            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "q", ":q"):
                print("\nExiting AI Customer Support Agent. Goodbye!")
                break

            if user_input.lower() == "help":
                print_help()
                continue

            # Process customer message through Hybrid v2 pipeline
            result = agent.process_message(user_input)
            format_result(result)

        except KeyboardInterrupt:
            print("\n\nSession interrupted by user. Goodbye!")
            break
        except Exception as e:
            print(f"\n[ERROR] An error occurred while processing message: {e}\n")


if __name__ == "__main__":
    main()
