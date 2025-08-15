# main.py
import yaml
import uuid
import asyncio
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

from pearl_agent import PEARLAgent
from memory import MemoryManager
from tools import available_tools

# --- App Initialization ---
app = FastAPI(title="Project PEARL API", version="1.0")

# --- Configuration & Global Resources ---
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

API_KEY = config['gemini_api_key']

# Global job store (in a real app, use Redis or a DB)
jobs: Dict[str, Dict[str, Any]] = {}

# Global Semaphore to limit concurrent LLM calls across all agent runs
API_CALL_SEMAPHORE = asyncio.Semaphore(5)

# --- Pydantic Models for API ---
class AgentRunRequest(BaseModel):
    goal: str
    iterations: int = 3

class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str

class JobStatusResponse(BaseModel):
    status: str
    progress: float
    details: Dict[str, Any]

# --- Background Task for PEARL cycle ---
async def run_pearl_cycle(job_id: str, goal: str, iterations: int):
    """The main async function to run the agent's cognitive loop."""
    try:
        jobs[job_id]['status'] = 'in_progress'
        
        memory_manager = MemoryManager(
            db_directory=config['memory']['database_directory'],
            collection_name=config['memory']['collection_name']
        )
        agent = PEARLAgent(
            api_key=API_KEY,
            model_name=config['model_name'],
            memory_manager=memory_manager,
            tools=available_tools,
            api_call_semaphore=API_CALL_SEMAPHORE
        )

        for i in range(iterations):
            jobs[job_id]['details'][f'cycle_{i+1}'] = {'status': 'starting'}
            
            assessment = await agent.self_assess(goal)
            tasks = await agent.adaptive_plan(goal, assessment)
            
            cycle_results = []
            for task in sorted(tasks, key=lambda x: x.priority, reverse=True):
                if agent._dependencies_met(task):
                    result = await agent.execute_goal_oriented(task)
                    task.result = result
                    task.status = agent.TaskStatus.COMPLETED
                    agent.tasks[task.id] = task
                    experience = await agent.integrate_experience(task)
                    cycle_results.append({'task': task.description, 'result': result, 'learning': experience})

            agent._update_context()
            jobs[job_id]['progress'] = (i + 1) / iterations
            jobs[job_id]['details'][f'cycle_{i+1}'] = {
                'status': 'completed',
                'assessment': assessment,
                'results': cycle_results
            }

        jobs[job_id]['status'] = 'completed'
    except Exception as e:
        jobs[job_id]['status'] = 'failed'
        jobs[job_id]['details']['error'] = str(e)


# --- API Endpoints ---
@app.post("/agent/run", response_model=JobResponse)
async def start_agent_run(request: AgentRunRequest, background_tasks: BackgroundTasks):
    """Starts a new PEARL agent run in the background."""
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "pending",
        "progress": 0.0,
        "details": {"goal": request.goal}
    }
    background_tasks.add_task(run_pearl_cycle, job_id, request.goal, request.iterations)
    return JobResponse(job_id=job_id, status="pending", message="Agent run started.")

@app.get("/agent/status/{job_id}", response_model=JobStatusResponse)
async def get_agent_status(job_id: str):
    """Retrieves the status and results of a specific agent run."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(**job)
