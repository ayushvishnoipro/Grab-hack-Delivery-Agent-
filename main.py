import argparse
import asyncio
import json
import sys
from typing import Optional

from src.agent.coordinator import resolve_scenario as resolve_async
from src.scenarios.loader import get_scenario_loader


def load_scenario_text(scenario_id: Optional[str], scenario_text: Optional[str]) -> str:
    if scenario_text:
        return scenario_text
    if scenario_id:
        loader = get_scenario_loader()
        scenario_text = loader.get_scenario_text(scenario_id)
        if scenario_text:
            return scenario_text
        # Fallback to builtin scenarios
        builtin = _get_builtin_scenarios()
        return builtin.get(scenario_id, scenario_id)
    return _get_builtin_scenarios()["traffic_obstruction"]


def _get_builtin_scenarios():
    return {
        "traffic_obstruction": (
            "Driver reports heavy traffic and a road obstruction near the main highway, "
            "delivery may be delayed by 20-30 minutes. Need to assess traffic, find alternative "
            "route, and proactively notify the customer."
        ),
        "merchant_delay": (
            "Restaurant indicates order prep delay due to high volume. Determine current prep time, "
            "coordinate with driver and consider notifying the customer with options."
        ),
        "recipient_unavailable": (
            "Recipient is not available at the delivery address. Attempt to contact recipient, "
            "consider alternative delivery options like nearby locker or rescheduling."
        ),
    }


def list_scenarios(show_details: bool):
    """List available scenarios."""
    try:
        loader = get_scenario_loader()
        scenarios = loader.list_scenarios()
        
        print(f"📚 Available Scenarios ({len(scenarios)} total):\n")
        
        for scenario_id in scenarios:
            scenario = loader.get_scenario(scenario_id)
            if scenario:
                title = scenario.get("title", scenario_id)
                severity = scenario.get("severity", "unknown")
                
                print(f"🔹 {scenario_id}")
                print(f"   Title: {title}")
                print(f"   Severity: {severity}")
                
                if show_details:
                    description = scenario.get("description", "No description")
                    stakeholders = scenario.get("stakeholders", [])
                    expected_tools = scenario.get("expected_tools", [])
                    
                    print(f"   Description: {description}")
                    print(f"   Stakeholders: {', '.join(stakeholders)}")
                    print(f"   Expected Tools: {', '.join(expected_tools)}")
                
                print()
    except Exception as e:
        print(f"❌ Error loading scenarios: {str(e)}")
        print("\n📚 Built-in Scenarios:")
        builtin = _get_builtin_scenarios()
        for scenario_id, description in builtin.items():
            print(f"🔹 {scenario_id}")
            print(f"   Description: {description}")
            print()


def load_scenario_text(scenario_id: Optional[str], scenario_text: Optional[str]) -> str:
    if scenario_text:
        return scenario_text
    if scenario_id:
        return _get_builtin_scenarios().get(scenario_id, scenario_id)
    return _get_builtin_scenarios()["traffic_obstruction"]


def print_result(result, verbose: bool):
    print("=== Synapse Result ===")
    print(f"Success: {result.success}")
    print(f"Confidence: {result.confidence_score:.2f}")
    print(f"Execution time (s): {result.execution_time_seconds:.2f}")
    print(f"Tools used: {', '.join(result.tools_used) if result.tools_used else 'none'}")
    if verbose:
        print("\n-- Reasoning --")
        for step in result.reasoning_steps:
            print(step)
    print("\n-- Solution Plan --")
    print(json.dumps(result.solution_plan, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Project Synapse - Autonomous Delivery Coordination Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py llm --id traffic_obstruction --verbose
  python main.py demo --id merchant_delay
  python main.py list-scenarios --details
        """
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_llm = sub.add_parser("llm", help="Resolve a scenario using LLM + tools")
    p_llm.add_argument("--id", dest="scenario_id", type=str, default=None)
    p_llm.add_argument("--text", dest="scenario_text", type=str, default=None)
    p_llm.add_argument("--verbose", action="store_true")

    p_demo = sub.add_parser("demo", help="Demo run (uses same agent)")
    p_demo.add_argument("--id", dest="scenario_id", type=str, default="traffic_obstruction")
    p_demo.add_argument("--verbose", action="store_true")

    p_list = sub.add_parser("list-scenarios", help="List all available scenarios")
    p_list.add_argument("--details", action="store_true", help="Show detailed information")

    args = parser.parse_args(argv)

    if args.cmd == "list-scenarios":
        list_scenarios(args.details)
        return

    scenario = load_scenario_text(getattr(args, "scenario_id", None), getattr(args, "scenario_text", None))

    async def _run():
        return await resolve_async(scenario)

    result = asyncio.run(_run())
    print_result(result, getattr(args, "verbose", False))


if __name__ == "__main__":
    main()
