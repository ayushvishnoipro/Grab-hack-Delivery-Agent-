"""
Chain-of-thought reasoning implementation for Project Synapse.

This module provides transparent reasoning capabilities that log and explain
every decision step taken by the Synapse agent.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class ReasoningStepType(Enum):
    """Types of reasoning steps for categorization."""
    ANALYSIS = "analysis"
    PLANNING = "planning"
    TOOL_SELECTION = "tool_selection"
    EXECUTION = "execution"
    SYNTHESIS = "synthesis"
    VERIFICATION = "verification"
    DECISION = "decision"


@dataclass
class ReasoningStep:
    """Individual step in the chain-of-thought reasoning process."""
    step_number: int
    step_type: ReasoningStepType
    reasoning: str
    timestamp: datetime
    context: Dict[str, Any]
    confidence: float
    alternatives_considered: List[str]
    decision_factors: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert reasoning step to dictionary."""
        return {
            "step_number": self.step_number,
            "step_type": self.step_type.value,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
            "confidence": self.confidence,
            "alternatives_considered": self.alternatives_considered,
            "decision_factors": self.decision_factors
        }


class ChainOfThoughtReasoner:
    """Manages chain-of-thought reasoning for the Synapse agent."""
    
    def __init__(self):
        self.reasoning_steps: List[ReasoningStep] = []
        self.current_step = 0
        self.reasoning_session_id = f"reasoning_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def add_reasoning_step(
        self,
        step_type: ReasoningStepType,
        reasoning: str,
        context: Dict[str, Any] = None,
        confidence: float = 0.8,
        alternatives_considered: List[str] = None,
        decision_factors: List[str] = None
    ) -> ReasoningStep:
        """Add a new reasoning step to the chain."""
        self.current_step += 1
        
        step = ReasoningStep(
            step_number=self.current_step,
            step_type=step_type,
            reasoning=reasoning,
            timestamp=datetime.now(),
            context=context or {},
            confidence=confidence,
            alternatives_considered=alternatives_considered or [],
            decision_factors=decision_factors or []
        )
        
        self.reasoning_steps.append(step)
        return step
    
    def analyze_scenario(self, scenario: str) -> ReasoningStep:
        """Add analysis step for the given scenario."""
        return self.add_reasoning_step(
            ReasoningStepType.ANALYSIS,
            f"Analyzing delivery scenario: {scenario}. Identifying key problems, constraints, and stakeholders involved.",
            context={"scenario": scenario},
            confidence=0.9,
            decision_factors=["scenario_complexity", "stakeholder_count", "time_constraints"]
        )
    
    def plan_tool_usage(self, available_tools: List[str], scenario_needs: List[str]) -> ReasoningStep:
        """Add planning step for tool selection and usage order."""
        reasoning = (
            f"Planning tool usage strategy. Available tools: {', '.join(available_tools)}. "
            f"Scenario needs: {', '.join(scenario_needs)}. Determining optimal tool sequence."
        )
        
        return self.add_reasoning_step(
            ReasoningStepType.PLANNING,
            reasoning,
            context={
                "available_tools": available_tools,
                "scenario_needs": scenario_needs
            },
            confidence=0.85,
            decision_factors=["tool_effectiveness", "execution_order", "dependency_chain"]
        )
    
    def select_tool(self, tool_name: str, reasoning: str, alternatives: List[str] = None) -> ReasoningStep:
        """Add tool selection step with rationale."""
        full_reasoning = f"Selecting tool '{tool_name}': {reasoning}"
        
        return self.add_reasoning_step(
            ReasoningStepType.TOOL_SELECTION,
            full_reasoning,
            context={"selected_tool": tool_name},
            confidence=0.8,
            alternatives_considered=alternatives or [],
            decision_factors=["tool_capability", "expected_outcome", "execution_time"]
        )
    
    def record_tool_execution(self, tool_name: str, parameters: Dict[str, Any], result: Any) -> ReasoningStep:
        """Record tool execution and outcome."""
        success = getattr(result, 'success', True) if hasattr(result, 'success') else True
        
        reasoning = (
            f"Executed tool '{tool_name}' with parameters {list(parameters.keys())}. "
            f"Result: {'Success' if success else 'Failed'}. "
            f"Gathering information for next decision."
        )
        
        return self.add_reasoning_step(
            ReasoningStepType.EXECUTION,
            reasoning,
            context={
                "tool_name": tool_name,
                "parameters": parameters,
                "success": success,
                "result_summary": str(result)[:200] if result else None
            },
            confidence=0.9 if success else 0.5
        )
    
    def synthesize_solution(self, gathered_data: Dict[str, Any], solution_plan: Dict[str, Any]) -> ReasoningStep:
        """Add solution synthesis step."""
        reasoning = (
            f"Synthesizing comprehensive solution based on gathered data from {len(gathered_data)} sources. "
            f"Created solution plan with {len(solution_plan.get('immediate_actions', []))} immediate actions "
            f"and {len(solution_plan.get('alternative_options', []))} alternatives."
        )
        
        return self.add_reasoning_step(
            ReasoningStepType.SYNTHESIS,
            reasoning,
            context={
                "data_sources": list(gathered_data.keys()),
                "solution_components": list(solution_plan.keys())
            },
            confidence=0.85,
            decision_factors=["data_completeness", "solution_feasibility", "stakeholder_impact"]
        )
    
    def verify_solution(self, solution: Dict[str, Any], verification_criteria: List[str]) -> ReasoningStep:
        """Add solution verification step."""
        reasoning = (
            f"Verifying solution against {len(verification_criteria)} criteria. "
            f"Checking completeness, feasibility, and alignment with scenario requirements."
        )
        
        return self.add_reasoning_step(
            ReasoningStepType.VERIFICATION,
            reasoning,
            context={
                "verification_criteria": verification_criteria,
                "solution_aspects": list(solution.keys())
            },
            confidence=0.9,
            decision_factors=verification_criteria
        )
    
    def make_final_decision(self, decision: str, reasoning: str, confidence: float) -> ReasoningStep:
        """Add final decision step."""
        full_reasoning = f"Final decision: {decision}. Rationale: {reasoning}"
        
        return self.add_reasoning_step(
            ReasoningStepType.DECISION,
            full_reasoning,
            context={"final_decision": decision},
            confidence=confidence,
            decision_factors=["solution_completeness", "stakeholder_satisfaction", "implementation_feasibility"]
        )
    
    def get_reasoning_summary(self) -> Dict[str, Any]:
        """Get a summary of the reasoning process."""
        step_types = {}
        total_confidence = 0
        
        for step in self.reasoning_steps:
            step_type = step.step_type.value
            step_types[step_type] = step_types.get(step_type, 0) + 1
            total_confidence += step.confidence
        
        avg_confidence = total_confidence / len(self.reasoning_steps) if self.reasoning_steps else 0
        
        return {
            "session_id": self.reasoning_session_id,
            "total_steps": len(self.reasoning_steps),
            "step_types": step_types,
            "average_confidence": round(avg_confidence, 2),
            "reasoning_duration": (
                self.reasoning_steps[-1].timestamp - self.reasoning_steps[0].timestamp
            ).total_seconds() if len(self.reasoning_steps) > 1 else 0,
            "reasoning_quality": "high" if avg_confidence > 0.8 else "medium" if avg_confidence > 0.6 else "low"
        }
    
    def get_formatted_reasoning(self) -> List[str]:
        """Get formatted reasoning steps for display."""
        formatted_steps = []
        
        for step in self.reasoning_steps:
            timestamp = step.timestamp.strftime("%H:%M:%S")
            confidence_str = f"({step.confidence:.1%} confidence)"
            
            formatted_step = f"Step {step.step_number} [{step.step_type.value.upper()}] {timestamp} {confidence_str}"
            formatted_step += f"\n  {step.reasoning}"
            
            if step.alternatives_considered:
                formatted_step += f"\n  Alternatives considered: {', '.join(step.alternatives_considered)}"
            
            if step.decision_factors:
                formatted_step += f"\n  Decision factors: {', '.join(step.decision_factors)}"
            
            formatted_steps.append(formatted_step)
        
        return formatted_steps
    
    def export_reasoning_log(self) -> Dict[str, Any]:
        """Export complete reasoning log for analysis."""
        return {
            "session_id": self.reasoning_session_id,
            "summary": self.get_reasoning_summary(),
            "steps": [step.to_dict() for step in self.reasoning_steps],
            "metadata": {
                "total_steps": len(self.reasoning_steps),
                "start_time": self.reasoning_steps[0].timestamp.isoformat() if self.reasoning_steps else None,
                "end_time": self.reasoning_steps[-1].timestamp.isoformat() if self.reasoning_steps else None
            }
        }
    
    def clear_reasoning(self):
        """Clear all reasoning steps for a new session."""
        self.reasoning_steps.clear()
        self.current_step = 0
        self.reasoning_session_id = f"reasoning_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def create_reasoning_prompts() -> Dict[str, str]:
    """Create prompt templates for chain-of-thought reasoning."""
    
    return {
        "system_prompt": """
You are the Synapse Agent, an autonomous coordinator for last-mile delivery disruptions.

REASONING PROCESS - Follow this exact sequence:
1. ANALYZE: Break down the scenario and identify key problems, stakeholders, and constraints
2. PLAN: Determine which tools are needed and in what sequence
3. EXECUTE: Use tools systematically to gather information and take actions
4. SYNTHESIZE: Create comprehensive solution plan based on gathered data
5. VERIFY: Ensure all aspects of the problem are addressed
6. DECIDE: Make final recommendations with confidence scores

REASONING REQUIREMENTS:
- Explain every decision step with clear rationale
- Consider multiple alternatives before selecting tools
- Document what information each tool provides
- Show how gathered data influences your decisions
- Provide confidence scores for each step
- Be transparent about uncertainty or limitations

TOOL SELECTION CRITERIA:
- Choose tools based on their specific capabilities and expected outcomes
- Consider dependencies between tools (some data may be needed before others)
- Balance information gathering with time efficiency
- Explain why each tool is the best choice for the current step

Available tools: {tool_descriptions}

Always maintain professional, clear communication while showing your reasoning process.
""",
        
        "analysis_prompt": """
Analyze this delivery scenario step by step:

Scenario: {scenario}

Your analysis should identify:
1. Primary problems and disruptions
2. Affected stakeholders (customer, driver, merchant, etc.)
3. Time constraints and urgency level
4. Potential consequences if not resolved
5. Key information gaps that need to be filled

Provide your reasoning for each identified aspect.
""",
        
        "planning_prompt": """
Based on your analysis of: {scenario}

Create a strategic plan for resolution:

1. List the specific information you need to gather
2. Identify which tools can provide this information
3. Determine the optimal sequence for tool usage
4. Consider dependencies between different tools
5. Estimate the overall approach and expected outcomes

Explain your reasoning for the tool selection and sequencing.
""",
        
        "synthesis_prompt": """
Synthesize a comprehensive solution based on all gathered information:

Scenario: {scenario}
Tool Results: {tool_results}

Create a solution plan that includes:
1. Immediate actions to address urgent issues
2. Alternative options for different scenarios
3. Communication strategy for all stakeholders
4. Contingency plans for potential complications
5. Success metrics and follow-up requirements

Explain how each piece of gathered information contributed to your solution.
""",
        
        "verification_prompt": """
Verify your proposed solution addresses all aspects:

Original Scenario: {scenario}
Proposed Solution: {solution}

Check that your solution:
1. Addresses all identified problems
2. Considers all affected stakeholders
3. Is feasible within time and resource constraints
4. Provides appropriate alternatives
5. Includes proper follow-up and monitoring

Provide confidence scores and identify any remaining uncertainties.
"""
    }


# Global reasoner instance for the agent
global_reasoner = ChainOfThoughtReasoner()


def get_global_reasoner() -> ChainOfThoughtReasoner:
    """Get the global reasoner instance."""
    return global_reasoner


def reset_reasoning_session():
    """Reset the global reasoning session."""
    global_reasoner.clear_reasoning()
