"""
Base tool system for Project Synapse.

This module provides the abstract base class and result structures for all tools
used by the Synapse agent in delivery coordination scenarios.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class ToolStatus(Enum):
    """Status indicators for tool execution results."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    TIMEOUT = "timeout"


@dataclass
class ToolResult:
    """Standardized result structure for all tool executions."""
    success: bool
    data: Dict[str, Any]
    message: str
    timestamp: datetime
    execution_time_ms: float
    status: ToolStatus
    tool_name: str
    confidence_score: Optional[float] = None
    additional_context: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "execution_time_ms": self.execution_time_ms,
            "status": self.status.value,
            "tool_name": self.tool_name,
            "confidence_score": self.confidence_score,
            "additional_context": self.additional_context or {}
        }


class BaseTool(ABC):
    """
    Abstract base class for all Synapse delivery coordination tools.
    
    Each tool must implement name, description, and execute methods.
    Tools should handle errors gracefully and return standardized ToolResult objects.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Tool identifier used by the agent for tool selection.
        Should be snake_case and descriptive.
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        Clear, detailed description of tool functionality for LLM understanding.
        Should include when to use the tool and what parameters are required.
        """
        pass

    @property
    def category(self) -> str:
        """Tool category for organization and filtering."""
        return "general"

    @property
    def required_parameters(self) -> list[str]:
        """List of required parameter names for tool execution."""
        return []

    @property
    def optional_parameters(self) -> list[str]:
        """List of optional parameter names for tool execution."""
        return []

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with provided parameters.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            ToolResult: Standardized result object with execution details
            
        Raises:
            Should handle all exceptions internally and return appropriate ToolResult
        """
        pass

    def validate_parameters(self, **kwargs) -> tuple[bool, str]:
        """
        Validate that required parameters are present.
        
        Args:
            **kwargs: Parameters to validate
            
        Returns:
            tuple: (is_valid, error_message)
        """
        missing_params = []
        for param in self.required_parameters:
            if param not in kwargs or kwargs[param] is None:
                missing_params.append(param)
        
        if missing_params:
            return False, f"Missing required parameters: {', '.join(missing_params)}"
        
        return True, ""

    async def safe_execute(self, **kwargs) -> ToolResult:
        """
        Safely execute the tool with parameter validation and error handling.
        
        Args:
            **kwargs: Tool parameters
            
        Returns:
            ToolResult: Execution result with error handling
        """
        start_time = datetime.now()
        
        try:
            # Validate parameters
            is_valid, error_msg = self.validate_parameters(**kwargs)
            if not is_valid:
                return ToolResult(
                    success=False,
                    data={},
                    message=f"Parameter validation failed: {error_msg}",
                    timestamp=start_time,
                    execution_time_ms=0,
                    status=ToolStatus.FAILURE,
                    tool_name=self.name
                )
            
            # Execute tool
            result = await self.execute(**kwargs)
            
            # Calculate execution time
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds() * 1000
            result.execution_time_ms = execution_time
            
            return result
            
        except Exception as e:
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            return ToolResult(
                success=False,
                data={"error": str(e), "error_type": type(e).__name__},
                message=f"Tool execution failed: {str(e)}",
                timestamp=start_time,
                execution_time_ms=execution_time,
                status=ToolStatus.FAILURE,
                tool_name=self.name
            )

    def get_schema(self) -> Dict[str, Any]:
        """
        Get tool schema for LangChain integration.
        
        Returns:
            Dict containing tool schema for agent registration
        """
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "required_parameters": self.required_parameters,
            "optional_parameters": self.optional_parameters
        }


class ToolExecutionError(Exception):
    """Custom exception for tool execution errors."""
    
    def __init__(self, tool_name: str, message: str, original_error: Optional[Exception] = None):
        self.tool_name = tool_name
        self.original_error = original_error
        super().__init__(f"Tool '{tool_name}' execution failed: {message}")


class ToolTimeoutError(ToolExecutionError):
    """Exception raised when tool execution exceeds timeout."""
    pass


class ToolParameterError(ToolExecutionError):
    """Exception raised when tool parameters are invalid."""
    pass
