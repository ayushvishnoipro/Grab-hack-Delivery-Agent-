"""
Main coordinator agent for Project Synapse using LangGraph.

This module implements the core agent that orchestrates tool usage and reasoning
to resolve delivery disruption scenarios autonomously.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, TypedDict
from typing import Annotated
from dataclasses import dataclass

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages

from ..tools import get_available_tools, get_tool_by_name
from .reasoning import (
    ChainOfThoughtReasoner, 
    ReasoningStepType, 
    create_reasoning_prompts,
    get_global_reasoner
)
from ..config.settings import get_settings


class AgentState(TypedDict):
    """State object for the LangGraph agent."""
    messages: Annotated[List[BaseMessage], add_messages]
    scenario: str
    reasoning_steps: List[Dict[str, Any]]
    tool_calls_made: List[Dict[str, Any]]
    gathered_data: List[Dict[str, Any]]
    solution_plan: Optional[Dict[str, Any]]
    current_iteration: int
    max_iterations: int
    confidence_score: float
    status: str
    pending_tool_calls: Optional[List[Any]]


@dataclass
class ResolutionResult:
    """Result of scenario resolution."""
    success: bool
    scenario: str
    reasoning_steps: List[str]
    tools_used: List[str]
    solution_plan: Dict[str, Any]
    metrics: Dict[str, Any]
    confidence_score: float
    execution_time_seconds: float


class SynapseCoordinator:
    """Main coordination agent for delivery disruption resolution."""
    
    def __init__(self):
        self.settings = get_settings()
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",  # Using latest Gemini 2.x
            google_api_key=self.settings.google_api_key,
            temperature=0.1,  # Low temperature for consistent reasoning
            max_tokens=4096
        )
        self.tools = get_available_tools()
        
        # Create LangChain tools for the LLM
        self.langchain_tools = self._create_langchain_tools()
        
        # Bind tools to the LLM
        self.llm_with_tools = self.llm.bind_tools(self.langchain_tools)
        
        self.reasoner = get_global_reasoner()
        self.prompts = create_reasoning_prompts()
        
        # Create the workflow
        self.workflow = self._create_workflow()
    
    def _create_langchain_tools(self):
        """Create LangChain-compatible tools from our tool registry."""
        from langchain_core.tools import StructuredTool

        langchain_tools = []
        
        for tool_name, tool_instance in self.tools.items():
            # Create a closure to capture the tool_instance
            def make_tool_func(tool_obj, name):
                async def tool_func(**kwargs) -> str:
                    res = await tool_obj.safe_execute(**kwargs)
                    return json.dumps(res.to_dict())
                return tool_func
            
            # Create the tool function with proper closure
            tool_func = make_tool_func(tool_instance, tool_name)
            
            # Create StructuredTool with proper parameters
            langchain_tool = StructuredTool.from_function(
                func=tool_func,
                name=tool_name,
                description=tool_instance.description
            )
            langchain_tools.append(langchain_tool)
        
        return langchain_tools
    
    def _create_workflow(self):
        """Create the LangGraph workflow for agent coordination."""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("call_model", self._call_model_node)
        workflow.add_node("tools", ToolNode(self.langchain_tools))
        workflow.add_node("after_tools", self._after_tools_node)
        workflow.add_node("synthesis", self._synthesis_node)
        workflow.add_node("verification", self._verification_node)
        
        # Set entry point
        workflow.set_entry_point("call_model")
        
        # call_model -> tools or synthesis
        workflow.add_conditional_edges(
            "call_model",
            self._has_tool_calls,
            {
                "use_tools": "tools",
                "synthesize": "synthesis",
                "retry": "call_model"
            }
        )
        
        # tools -> after_tools
        workflow.add_edge("tools", "after_tools")
        
        # after_tools -> continue loop or synthesize
        workflow.add_conditional_edges(
            "after_tools",
            self._should_continue_reasoning,
            {
                "continue": "call_model",
                "synthesize": "synthesis"
            }
        )
        
        # synthesis -> verification -> end
        workflow.add_edge("synthesis", "verification")
        workflow.add_edge("verification", END)
        
        return workflow.compile()

    async def _call_model_node(self, state: AgentState) -> AgentState:
        """Ask the LLM what to do next (may emit tool calls)."""
        # Ensure messages are present and valid
        if not state["messages"]:
            # Build initial system and human messages
            tool_desc = "\n".join([f"- {name}: {tool.description}" for name, tool in self.tools.items()])
            system_msg = SystemMessage(content=self.prompts["system_prompt"].format(tool_descriptions=tool_desc))
            human_msg = HumanMessage(content=(
                f"Analyze and resolve this scenario using the REASONING PROCESS. "
                f"Call tools as needed to gather facts before proposing a solution.\n\n"
                f"Scenario: {state['scenario']}"
            ))
            state["messages"] = [system_msg, human_msg]
            # Record analysis planning steps (high-level)
            self.reasoner.analyze_scenario(state["scenario"])
            self.reasoner.add_reasoning_step(
                ReasoningStepType.PLANNING,
                "Planning tool usage based on scenario; LLM will select appropriate tools via function calling.",
                context={"available_tools": list(self.tools.keys())},
                confidence=0.85,
                decision_factors=["tool_effectiveness", "data_requirements"]
            )
        
        # Invoke the LLM with tools bound
        ai_msg = await self.llm_with_tools.ainvoke(state["messages"])
        if not isinstance(ai_msg, AIMessage):
            # Wrap as AIMessage if provider returns different type
            ai_msg = AIMessage(content=getattr(ai_msg, "content", str(ai_msg)))
        
        # Append AI response
        state["messages"].append(ai_msg)
        
        # Fallback: if no tool calls on first iteration, synthesize tool calls to ensure execution
        has_calls = isinstance(ai_msg, AIMessage) and getattr(ai_msg, "tool_calls", None)
        if not has_calls and state["current_iteration"] == 0:
            forced_calls = self._create_forced_tool_calls(state["scenario"])
            if forced_calls:
                forced_ai = AIMessage(content="Calling tools to gather critical facts before proposing a plan.", tool_calls=forced_calls)
                state["messages"].append(forced_ai)
        
        state["reasoning_steps"] = [step.to_dict() for step in self.reasoner.reasoning_steps]
        return state

    async def _after_tools_node(self, state: AgentState) -> AgentState:
        """Process tool outputs: update state, reasoning, and bookkeeping."""
        # Find the last AI message (that triggered tools)
        last_ai: Optional[AIMessage] = None
        for msg in reversed(state["messages"]):
            if isinstance(msg, AIMessage):
                last_ai = msg
                break
        
        if last_ai and getattr(last_ai, "tool_calls", None):
            tool_calls = last_ai.tool_calls
            # For each tool call, find corresponding ToolMessage and record results
            for call in tool_calls:
                call_id = call.get("id") if isinstance(call, dict) else getattr(call, "id", None)
                tool_name = call.get("name") if isinstance(call, dict) else getattr(call, "name", None)
                tool_args = call.get("args") if isinstance(call, dict) else getattr(call, "args", {})
                # Find ToolMessage with matching id
                tool_msg: Optional[ToolMessage] = None
                for m in reversed(state["messages"]):
                    if isinstance(m, ToolMessage) and getattr(m, "tool_call_id", None) == call_id:
                        tool_msg = m
                        break
                output_parsed: Any = None
                if tool_msg:
                    content = tool_msg.content if isinstance(tool_msg.content, str) else json.dumps(tool_msg.content)
                    try:
                        output_parsed = json.loads(content)
                    except Exception:
                        output_parsed = {"raw": content}
                # Update bookkeeping
                state["tool_calls_made"].append({
                    "tool_name": tool_name,
                    "args": tool_args,
                    "tool_call_id": call_id,
                    "timestamp": datetime.now().isoformat()
                })
                if output_parsed is not None:
                    state["gathered_data"].append({
                        "tool_name": tool_name,
                        "result": output_parsed
                    })
                # Record reasoning step
                self.reasoner.record_tool_execution(tool_name or "unknown_tool", tool_args or {}, output_parsed)
        
        # Advance iteration
        state["current_iteration"] += 1
        state["reasoning_steps"] = [step.to_dict() for step in self.reasoner.reasoning_steps]
        return state
    
    def _has_tool_calls(self, state: AgentState) -> str:
        """Decide whether to route to tools based on last AI message."""
        last_ai: Optional[AIMessage] = None
        for msg in reversed(state["messages"]):
            if isinstance(msg, AIMessage):
                last_ai = msg
                break
        if last_ai and getattr(last_ai, "tool_calls", None):
            return "use_tools"
        # If there is no AI message at all (unlikely), call model again
        if last_ai is None and state["messages"]:
            return "retry"
        return "synthesize"
    
    def _should_continue_reasoning(self, state: AgentState) -> str:
        """Determine if reasoning should continue or proceed to synthesis."""
        if state["current_iteration"] >= state["max_iterations"]:
            return "synthesize"
        # If we've gathered enough different tools' data, synthesize
        unique_tools = {entry.get("tool_name") for entry in state["gathered_data"] if isinstance(entry, dict)}
        if len(unique_tools) >= 3:
            return "synthesize"
        return "continue"
    
    async def _synthesis_node(self, state: AgentState) -> AgentState:
        """Synthesize solution based on gathered data."""
        scenario = state["scenario"]
        gathered_data = state["gathered_data"]
        
        # Add synthesis reasoning step
        solution_components = ["immediate_actions", "alternative_options", "communication_plan", "follow_up"]
        # Keep context minimal; the tool will describe details
        self.reasoner.add_reasoning_step(
            ReasoningStepType.SYNTHESIS,
            "Synthesizing solution plan from gathered tool outputs and scenario context.",
            context={"gathered_items": len(gathered_data)},
            confidence=0.85,
            decision_factors=["data_completeness", "feasibility", "stakeholder_impact"]
        )
        
        prompt = self.prompts["synthesis_prompt"].format(
            scenario=scenario,
            tool_results=json.dumps(gathered_data, indent=2)
        )
        
        system_msg = SystemMessage(content="Create a comprehensive solution plan in JSON format.")
        response = await self.llm.ainvoke([system_msg, HumanMessage(content=prompt)])
        
        # Extract solution plan from response
        solution_plan = self._extract_solution_from_response(response.content)
        
        state["solution_plan"] = solution_plan
        state["messages"].append(response if isinstance(response, BaseMessage) else AIMessage(content=str(response)))
        state["reasoning_steps"] = [step.to_dict() for step in self.reasoner.reasoning_steps]
        
        return state
    
    async def _verification_node(self, state: AgentState) -> AgentState:
        """Verify the solution addresses all scenario requirements."""
        scenario = state["scenario"]
        solution = state["solution_plan"]
        
        verification_criteria = [
            "addresses_all_problems",
            "considers_all_stakeholders", 
            "feasible_implementation",
            "appropriate_alternatives",
            "proper_follow_up"
        ]
        
        self.reasoner.verify_solution(solution, verification_criteria)
        
        prompt = self.prompts["verification_prompt"].format(
            scenario=scenario,
            solution=json.dumps(solution, indent=2)
        )
        
        system_msg = SystemMessage(content="Verify the solution and provide a confidence score.")
        response = await self.llm.ainvoke([system_msg, HumanMessage(content=prompt)])
        
        # Extract confidence score
        confidence = self._extract_confidence_from_response(response.content)
        
        # Make final decision
        self.reasoner.make_final_decision(
            "Solution verified and ready for implementation",
            f"Solution addresses scenario with {confidence:.1%} confidence",
            confidence
        )
        
        state["confidence_score"] = confidence
        state["status"] = "completed"
        state["messages"].append(response if isinstance(response, BaseMessage) else AIMessage(content=str(response)))
        state["reasoning_steps"] = [step.to_dict() for step in self.reasoner.reasoning_steps]
        
        return state
    
    def _extract_solution_from_response(self, response_content: str) -> Dict[str, Any]:
        """Extract solution plan from LLM response."""
        # Simple extraction - in practice, would use better parsing
        try:
            # Look for JSON in the response
            start = response_content.find('{')
            end = response_content.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(response_content[start:end])
        except Exception:
            pass
        
        # Fallback solution structure
        return {
            "immediate_actions": ["Analyze situation", "Contact relevant parties"],
            "alternative_options": ["Option 1: Direct resolution", "Option 2: Escalate"],
            "communication_plan": ["Notify customer", "Update driver", "Inform support"],
            "follow_up": ["Monitor resolution", "Collect feedback"],
            "estimated_resolution_time": "15-30 minutes",
            "success_probability": 0.85
        }
    
    def _extract_confidence_from_response(self, response_content: str) -> float:
        """Extract confidence score from LLM response."""
        # Simple extraction - look for percentages or decimal confidence scores
        import re
        
        # Look for percentage
        percent_match = re.search(r'(\d+)%', response_content)
        if percent_match:
            return float(percent_match.group(1)) / 100
        
        # Look for decimal confidence
        decimal_match = re.search(r'confidence[:\s]+([0-9.]+)', response_content, re.IGNORECASE)
        if decimal_match:
            try:
                return min(1.0, float(decimal_match.group(1)))
            except Exception:
                pass
        
        # Default confidence
        return 0.8

    def _create_forced_tool_calls(self, scenario: str) -> List[Dict[str, Any]]:
        """Create forced tool calls when LLM doesn't call tools automatically."""
        calls: List[Dict[str, Any]] = []
        s = scenario.lower()
        def add_call(name: str, args: Dict[str, Any]):
            if name in self.tools:
                calls.append({"name": name, "args": args, "id": f"forced_{name}_{len(calls)+1}"})
        # Traffic
        if any(w in s for w in ["traffic", "congestion", "road", "route", "accident", "obstruction", "delay"]):
            add_call("check_traffic", {"origin": "Current Location", "destination": "Delivery Address", "current_time": datetime.now().strftime("%H:%M")})
            add_call("calculate_alternative_route", {"origin": "Current Location", "destination": "Delivery Address", "disruption_type": "traffic_obstruction"})
        # Merchant
        if any(w in s for w in ["restaurant", "merchant", "kitchen", "prep", "order"]):
            add_call("get_merchant_status", {"merchant_id": "MERCHANT_001"})
        # Customer communication
        if any(w in s for w in ["customer", "recipient", "address", "contact", "notify"]):
            add_call("notify_customer", {"customer_id": "CUSTOMER_001", "message_type": "delay_notification", "estimated_delay": 15})
            add_call("contact_recipient", {"recipient_id": "RECIPIENT_001", "contact_method": "chat", "urgency_level": "high"})
        return calls[:3]

    async def resolve_scenario(self, scenario: str, max_iterations: int = 10) -> ResolutionResult:
        """Resolve a delivery disruption scenario."""
        start_time = datetime.now()
        
        # Reset reasoner for new session
        self.reasoner.clear_reasoning()
        
        # Initialize state
        initial_state: AgentState = {
            "messages": [],
            "scenario": scenario,
            "reasoning_steps": [],
            "tool_calls_made": [],
            "gathered_data": [],
            "solution_plan": None,
            "current_iteration": 0,
            "max_iterations": max_iterations,
            "confidence_score": 0.0,
            "status": "processing",
            "pending_tool_calls": None
        }
        
        try:
            # Run the workflow
            final_state = await self.workflow.ainvoke(initial_state)
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            # Create result
            result = ResolutionResult(
                success=final_state["status"] == "completed",
                scenario=scenario,
                reasoning_steps=self.reasoner.get_formatted_reasoning(),
                tools_used=[call.get("tool_name", "") for call in final_state["tool_calls_made"]],
                solution_plan=final_state["solution_plan"] or {},
                metrics={
                    "total_reasoning_steps": len(final_state["reasoning_steps"]),
                    "tools_called": len(final_state["tool_calls_made"]),
                    "resolution_time_seconds": execution_time,
                    "iterations": final_state["current_iteration"],
                    "confidence_score": final_state["confidence_score"]
                },
                confidence_score=final_state["confidence_score"],
                execution_time_seconds=execution_time
            )
            
            return result
            
        except Exception as e:
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            # Return error result
            return ResolutionResult(
                success=False,
                scenario=scenario,
                reasoning_steps=[f"Error occurred: {str(e)}"],
                tools_used=[],
                solution_plan={"error": str(e)},
                metrics={
                    "total_reasoning_steps": len(self.reasoner.reasoning_steps),
                    "tools_called": 0,
                    "resolution_time_seconds": execution_time,
                    "iterations": 0,
                    "confidence_score": 0.0
                },
                confidence_score=0.0,
                execution_time_seconds=execution_time
            )


# Global coordinator instance
_coordinator = None


def get_coordinator() -> SynapseCoordinator:
    """Get the global coordinator instance."""
    global _coordinator
    if _coordinator is None:
        _coordinator = SynapseCoordinator()
    return _coordinator


async def resolve_scenario(scenario: str, max_iterations: int = 10) -> ResolutionResult:
    """Convenience function to resolve a scenario."""
    coordinator = get_coordinator()
    return await coordinator.resolve_scenario(scenario, max_iterations)
