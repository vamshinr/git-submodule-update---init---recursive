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
        """S: Self-Assessment - Now fully asynchronous."""
        relevant_memories = await self.memory_manager.retrieve_relevant_memories(goal)
        assessment_prompt = f"..." # Prompt is the same as before
        
        response_text = await self._generate_content_with_semaphore(assessment_prompt)
        try:
            return json.loads(response_text)
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"Assessment parsing error: {e}. Using default."); return {"progress_score": 10, ...}

    async def adaptive_plan(self, goal: str, assessment: Dict[str, Any]) -> List[Task]:
        """A: Adaptive Planning - Now fully asynchronous."""
        planning_prompt = f"..." # Prompt is the same as before
        
        response_text = await self._generate_content_with_semaphore(planning_prompt)
        try:
            task_data = json.loads(response_text)
            return [Task(**data) for data in task_data]
        except (json.JSONDecodeError, TypeError, AttributeError) as e:
            print(f"Planning parsing error: {e}. Using fallback."); return [Task(id="fallback", ...)]

    async def execute_goal_oriented(self, task: Task) -> str:
        """G: Goal-oriented Execution - Now async."""
        if task.tool and task.tool in self.tools:
            tool_function = self.tools[task.tool]
            # Assuming tools are synchronous for now. Can be made async if they do I/O.
            return tool_function(task.tool_input)
        else:
            execution_prompt = f"..." # Prompt is the same as before
            return await self._generate_content_with_semaphore(execution_prompt)

    async def integrate_experience(self, task: Task) -> Dict[str, Any]:
        """E: Experience Integration - Now async."""
        integration_prompt = f"..." # Prompt is the same as before
        
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
