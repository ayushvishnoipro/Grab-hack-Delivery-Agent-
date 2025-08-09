"""
Demo mode implementation for Project Synapse.

This module provides demo functionality that uses the same coordinator
as the LLM mode.
"""

from .coordinator import resolve_scenario


async def demo_resolve_scenario(scenario: str, **kwargs):
    """
    Demo version of scenario resolution.
    Currently uses the same coordinator as LLM mode.
    """
    return await resolve_scenario(scenario, **kwargs)
