"""
Scenario loader for Project Synapse.
Simple version that doesn't depend on external files.
"""


class ScenarioLoader:
    """Simple scenario loader."""
    
    def __init__(self):
        self.scenarios = {
            "traffic_obstruction": {
                "id": "traffic_obstruction",
                "title": "Traffic Obstruction Delay",
                "description": (
                    "Driver reports heavy traffic and a road obstruction near the main highway, "
                    "delivery may be delayed by 20-30 minutes. Need to assess traffic, find alternative "
                    "route, and proactively notify the customer."
                ),
                "severity": "medium",
                "expected_tools": ["check_traffic", "calculate_alternative_route", "notify_customer"]
            },
            "merchant_delay": {
                "id": "merchant_delay",
                "title": "Restaurant Preparation Delay", 
                "description": (
                    "Restaurant indicates order prep delay due to high volume. Determine current prep time, "
                    "coordinate with driver and consider notifying the customer with options."
                ),
                "severity": "medium",
                "expected_tools": ["get_merchant_status", "notify_customer", "contact_recipient"]
            },
            "recipient_unavailable": {
                "id": "recipient_unavailable",
                "title": "Recipient Not Available",
                "description": (
                    "Recipient is not available at the delivery address. Attempt to contact recipient, "
                    "consider alternative delivery options like nearby locker or rescheduling."
                ),
                "severity": "high", 
                "expected_tools": ["contact_recipient", "find_nearby_locker", "notify_customer"]
            },
            "weather_disruption": {
                "id": "weather_disruption",
                "title": "Severe Weather Impact",
                "description": (
                    "Heavy rain and flooding in delivery area. Multiple drivers reporting unsafe "
                    "conditions. Need to assess weather impact, coordinate driver safety, and manage communications."
                ),
                "severity": "high",
                "expected_tools": ["check_traffic", "notify_customer", "calculate_alternative_route"]
            },
            "order_dispute": {
                "id": "order_dispute", 
                "title": "Delivery Dispute Resolution",
                "description": (
                    "Customer claims order was not delivered, but driver marked it as completed. "
                    "Need to investigate evidence, mediate between parties, and reach fair resolution."
                ),
                "severity": "high",
                "expected_tools": ["analyze_evidence", "initiate_mediation_flow", "contact_recipient"]
            }
        }
    
    def list_scenarios(self):
        """List all scenario IDs."""
        return list(self.scenarios.keys())
    
    def get_scenario(self, scenario_id: str):
        """Get scenario by ID."""
        return self.scenarios.get(scenario_id)
    
    def get_scenario_text(self, scenario_id: str):
        """Get scenario description."""
        scenario = self.get_scenario(scenario_id)
        return scenario.get("description") if scenario else None


# Global instance
_loader = None


def get_scenario_loader():
    """Get scenario loader instance."""
    global _loader
    if _loader is None:
        _loader = ScenarioLoader()
    return _loader


def load_scenario_text(scenario_id: str) -> str:
    """Load scenario text by ID."""
    loader = get_scenario_loader()
    return loader.get_scenario_text(scenario_id) or "Default traffic scenario"


def list_available_scenarios():
    """List available scenario IDs."""
    loader = get_scenario_loader()
    return loader.list_scenarios()
