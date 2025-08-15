# pearl_agent.py
import google.generativeai as genai
import json
import time
import asyncio
from typing import Dict, List, Any
# (Task and TaskStatus dataclasses remain the same as before)
from enum import Enum
from dataclasses import dataclass, asdict, field

class TaskStatus(Enum):
    PENDING = "pending"; IN_PROGRESS = "in_progress"; COMPLETED = "completed"; FAILED = "failed"

@dataclass
class Task:
    id: str; description: str; priority: int
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    result: str | None = None; tool: str | None = None; tool_input: str | None = None

class PEARLAgent:
    """Async PEARL Agent with API call Semaphore"""

    def __init__(self, api_key: str, model_name: str, memory_manager, tools: Dict, api_call_semaphore: asyncio.Semaphore):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.memory_manager = memory_manager
        self.tools = tools
        self.api_call_semaphore = api_call_semaphore # Semaphore to limit concurrent API calls
        self.tasks: Dict[str, Task] = {}
        self.context: Dict[str, Any] = {"completed_tasks": 0, "total_tasks": 0}

    async def _generate_content_with_semaphore(self, prompt: str) -> str:
        """Wrapper to call the Gemini API, respecting the semaphore."""
        async with self.api_call_semaphore:
            print("SEMAPHORE: Acquired lock for API call.")
            response = await self.model.generate_content_async(prompt)
            print("SEMAPHORE: Released lock for API call.")
            return response.text.strip().lstrip("```json").rstrip("```")

    async def self_assess(self, goal: str) -> Dict[str, Any]:
        """S: Self-Assessment - Evaluate current state, capabilities, and memories."""
        relevant_memories = await self.memory_manager.retrieve_relevant_memories(goal)
        assessment_prompt = f"""
        You are an AI agent conducting self-assessment. Respond ONLY with valid JSON.

        GOAL: {goal}
        CURRENT_CONTEXT: {json.dumps(self.context, indent=2)}
        RELEVANT_MEMORIES:
        {relevant_memories}

        Provide your assessment as a JSON object with these exact keys:
        {{
            "progress_score": <number 0-100 indicating closeness to the goal>,
            "gaps": ["list of knowledge or capability gaps"],
            "risks": ["list of potential risks or obstacles"],
            "recommendations": ["list of high-level next steps"]
        }}
        """
        
        response_text = await self._generate_content_with_semaphore(assessment_prompt)
        try:
            return json.loads(response_text)
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"Assessment parsing error: {e}. Using default."); return {"progress_score": 10, ...}

    async def adaptive_plan(self, goal: str, assessment: Dict[str, Any]) -> List[Task]:
        """A: Adaptive Planning - Create dynamic, context-aware task decomposition."""
        planning_prompt = f"""
        You are an AI task planner. Respond ONLY with a valid JSON array of tasks.

        MAIN_GOAL: {goal}
        ASSESSMENT: {json.dumps(assessment, indent=2)}
        AVAILABLE_TOOLS: {json.dumps(list(self.tools.keys()))}
        
        Create 2-3 actionable tasks to advance the goal. Tasks can either be research/analysis questions for the AI, or a specific action using an available tool.
        
        - For a tool-based task, set "tool" to the tool's name and "tool_input" to what it needs.
        - For a general AI task, leave "tool" and "tool_input" as null.
        - Ensure task IDs are unique strings (e.g., "task_1", "task_2").

        JSON array format:
        [
            {{
                "id": "task_1",
                "description": "Research the core principles of sustainable urban gardening.",
                "priority": 5,
                "dependencies": [],
                "tool": null,
                "tool_input": null
            }},
            {{
                "id": "task_2",
                "description": "Find recent articles on vertical farming techniques.",
                "priority": 4,
                "dependencies": [],
                "tool": "web_search",
                "tool_input": "recent developments in vertical farming techniques 2025"
            }}
        ]
        """
        response_text = await self._generate_content_with_semaphore(planning_prompt)
        try:
            task_data = json.loads(response_text)
            return [Task(**data) for data in task_data]
        except (json.JSONDecodeError, TypeError, AttributeError) as e:
            print(f"Planning parsing error: {e}. Using fallback."); return [Task(id="fallback", ...)]

    async def execute_goal_oriented(self, task: Task) -> str:
        """G: Goal-oriented Execution - Execute a task using tools or AI reasoning."""
        if task.tool and task.tool in self.tools:
            tool_function = self.tools[task.tool]
            # Assuming tools are synchronous for now. Can be made async if they do I/O.
            return tool_function(task.tool_input)
        else:
            # Execute a reasoning/text-generation task
            execution_prompt = f"""
            As an AI agent, execute the following task. Provide a comprehensive, direct, and actionable result.

            Task: {task.description}
            Context: {json.dumps(self.context, indent=2)}

            Focus on producing a clear and thorough response to fulfill the task's requirements.
            """
            return await self._generate_content_with_semaphore(execution_prompt)

    async def integrate_experience(self, task: Task) -> Dict[str, Any]:
        """E: Experience Integration - Learn from outcomes and update knowledge."""
        integration_prompt = f"""
        You are a learning AI. Reflect on the completed task and its result. Respond ONLY with valid JSON.

        TASK: {task.description}
        RESULT: {task.result[:500]}...
        STATUS: {task.status.value}

        Provide learning insights as a JSON object:
        {{
            "learnings": ["A concise, key insight or fact learned from the result."],
            "adjustments": ["An adjustment for future plans (e.g., 'focus more on X', 'avoid Y')."],
            "confidence_boost": <number from -10 to 10 reflecting change in confidence>
        }}
        """
        response_text = await self._generate_content_with_semaphore(integration_prompt)
        try:
            experience = json.loads(response_text)
            if task.status == TaskStatus.COMPLETED and experience.get("learnings"):
                await self.memory_manager.add_memory(task.description, experience["learnings"][0])
            return experience
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"Experience parsing error: {e}. Using default."); return {"learnings": [...], ...}
    
    # _dependencies_met and _update_context methods do not need to be async
    def _dependencies_met(self, task: Task) -> bool:
        return all(dep_id not in self.tasks or self.tasks[dep_id].status == TaskStatus.COMPLETED for dep_id in task.dependencies)

    def _update_context(self):
        completed_count = sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED)
        self.context.update({"completed_tasks": completed_count, "total_tasks": len(self.tasks)})
