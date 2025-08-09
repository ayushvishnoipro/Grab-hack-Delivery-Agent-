"""
Agent package initialization.
"""

from .coordinator import SynapseCoordinator, ResolutionResult, get_coordinator, resolve_scenario
from .reasoning import (
    ChainOfThoughtReasoner, 
    ReasoningStep, 
    ReasoningStepType,
    get_global_reasoner,
    reset_reasoning_session
)

__all__ = [
    # Coordinator
    "SynapseCoordinator",
    "ResolutionResult", 
    "get_coordinator",
    "resolve_scenario",
    
    # Demo
    "demo_resolve_scenario",
    
    # Reasoning
    "ChainOfThoughtReasoner",
    "ReasoningStep",
    "ReasoningStepType", 
    "get_global_reasoner",
    "reset_reasoning_session"
]
