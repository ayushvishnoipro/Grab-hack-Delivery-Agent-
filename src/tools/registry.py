"""
Tool registry for Project Synapse.

This module manages the registration and discovery of all available tools
for the Synapse delivery coordination agent.
"""

from typing import Dict, List, Type, Optional
from .base import BaseTool
from .logistics import (
    CheckTrafficTool,
    GetMerchantStatusTool,
    NotifyCustomerTool,
    CalculateAlternativeRouteTool,
    ContactRecipientTool,
    FindNearbyLockerTool,
    InitiateMediationFlowTool,
    AnalyzeEvidenceTool
)


class ToolRegistry:
    """Central registry for all Synapse tools."""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._tool_classes: Dict[str, Type[BaseTool]] = {}
        self._initialize_tools()
    
    def _initialize_tools(self):
        """Initialize and register all available tools."""
        tool_classes = [
            CheckTrafficTool,
            GetMerchantStatusTool,
            NotifyCustomerTool,
            CalculateAlternativeRouteTool,
            ContactRecipientTool,
            FindNearbyLockerTool,
            InitiateMediationFlowTool,
            AnalyzeEvidenceTool
        ]
        
        for tool_class in tool_classes:
            tool_instance = tool_class()
            self._tools[tool_instance.name] = tool_instance
            self._tool_classes[tool_instance.name] = tool_class
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Get a tool instance by name."""
        return self._tools.get(tool_name)
    
    def get_all_tools(self) -> Dict[str, BaseTool]:
        """Get all registered tools."""
        return self._tools.copy()
    
    def get_tools_by_category(self, category: str) -> Dict[str, BaseTool]:
        """Get all tools in a specific category."""
        return {
            name: tool for name, tool in self._tools.items()
            if tool.category == category
        }
    
    def list_tool_names(self) -> List[str]:
        """Get list of all tool names."""
        return list(self._tools.keys())
    
    def list_categories(self) -> List[str]:
        """Get list of all tool categories."""
        categories = set(tool.category for tool in self._tools.values())
        return sorted(list(categories))
    
    def get_tool_descriptions(self) -> Dict[str, str]:
        """Get descriptions of all tools for LLM context."""
        return {
            name: tool.description for name, tool in self._tools.items()
        }
    
    def get_tool_schemas(self) -> List[Dict]:
        """Get schemas for all tools for LangChain integration."""
        return [tool.get_schema() for tool in self._tools.values()]
    
    def register_custom_tool(self, tool: BaseTool):
        """Register a custom tool instance."""
        self._tools[tool.name] = tool
        self._tool_classes[tool.name] = type(tool)
    
    def is_tool_available(self, tool_name: str) -> bool:
        """Check if a tool is available."""
        return tool_name in self._tools
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict]:
        """Get detailed information about a specific tool."""
        tool = self.get_tool(tool_name)
        if not tool:
            return None
        
        return {
            "name": tool.name,
            "description": tool.description,
            "category": tool.category,
            "required_parameters": tool.required_parameters,
            "optional_parameters": tool.optional_parameters,
            "class": tool.__class__.__name__
        }


# Global registry instance
tool_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry instance."""
    return tool_registry


def get_available_tools() -> Dict[str, BaseTool]:
    """Convenience function to get all available tools."""
    return tool_registry.get_all_tools()


def get_tool_by_name(tool_name: str) -> Optional[BaseTool]:
    """Convenience function to get a tool by name."""
    return tool_registry.get_tool(tool_name)
