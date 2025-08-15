# Project PEARL: An Autonomous AI Agent Framework

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Framework: FastAPI](https://img.shields.io/badge/Framework-FastAPI-green.svg)](https://fastapi.tiangolo.com/)

**PEARL** (**P**roactive **E**xecution and **A**daptive **R**easoning **L**oop) is a sophisticated framework for building autonomous AI agents. This project provides a scalable, asynchronous backend using FastAPI that allows an AI agent to tackle complex goals by planning, acting, and learning from its experiences in a continuous cycle.

## Features

* **Cognitive Cycle (PEARL)**: The agent operates on an intelligent loop of proactive execution and adaptive reasoning, allowing it to dynamically adjust its strategy.
* **Asynchronous FastAPI Backend**: Built with modern, high-performance FastAPI, enabling it to handle multiple concurrent agent tasks without blocking.
* **Concurrency Controls**:
    * **Semaphore**: Manages and limits concurrent calls to the external LLM API, preventing rate-limiting and controlling costs.
    * **Mutex (Lock)**: Ensures thread-safe writes to the shared memory database, preventing data corruption.
* **Tool Use**: The agent can leverage external tools (e.g., web search) to gather information and interact with its environment, extending its capabilities beyond text generation.
* **Long-Term Memory**: Integrates a **ChromaDB** vector database to store and retrieve learnings from past tasks, enabling the agent to improve its performance over time.
* **Scalable & Decoupled**: The API-based architecture separates the agent's core logic from any user interface, allowing for flexible integration with various frontends or services.

---

## Architecture

The PEARL agent operates on a cyclical cognitive process, managed as a background task within the FastAPI application.

1.  **API Request**: A user sends a goal to the `POST /agent/run` endpoint. FastAPI creates a unique `job_id` and starts a background task.
2.  **Adaptive Reasoning & Planning**: The agent assesses the goal against its current context and relevant memories retrieved from ChromaDB. It then reasons about the best strategy and creates an actionable, multi-step plan.
3.  **Proactive Execution**: The agent begins executing the tasks in its plan. It can use its internal LLM for reasoning-based tasks or call external tools for data gathering.
4.  **Experience Integration & Learning**: After each task, the agent reflects on the outcome. The key insight or "learning" is vectorized and stored in its ChromaDB long-term memory, protected by a mutex lock.
5.  **Loop**: The agent loops through this cycle, refining its understanding and plan with each iteration until the goal is achieved or the maximum number of iterations is reached.
6.  **Status Monitoring**: The user can poll the `GET /agent/status/{job_id}` endpoint at any time to get real-time progress and final results.

---

## Technology Stack

* **Backend Framework**: FastAPI
* **Web Server**: Uvicorn
* **Generative AI**: Google Gemini
* **Vector Database**: ChromaDB
* **Concurrency**: Python's `asyncio` (Semaphore, Lock)
* **Tooling**: DuckDuckGo Search

---

## Getting Started

Follow these steps to set up and run the PEARL agent on your local machine.

### ### 1. Prerequisites

* Python 3.9+
* Git

### ### 2. Clone the Repository

```bash
git clone [https://github.com/vamshinr/pearl-agent-framework.git](https://github.com/vamshinr/pearl-agent-framework.git)
cd pearl-agent-framework
```

### ### 3. Set Up a Virtual Environment

It's recommended to use a virtual environment to manage dependencies.

```bash
# Create a virtual environment
python -m venv venv

# Activate it
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### ### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### ### 5. Configure Your API Key

1.  Open the `config.yaml` file.
2.  Paste your Google Gemini API key into the `gemini_api_key` field. You can get a free key from [Google AI Studio](https://makersuite.google.com/app/apikey).

### ### 6. Run the API Server

```bash
uvicorn main:app --reload
```

The API will now be running at `http://127.0.0.1:8000`. You can access the auto-generated documentation at `http://127.0.0.1:8000/docs`.

---

## API Usage Examples

You can interact with the running API using `curl` or any API client.

### ### 1. Start a New Agent Task

Send a `POST` request with your goal. The server will respond immediately with a `job_id`.

```bash
curl -X POST "[http://127.0.0.1:8000/agent/run](http://127.0.0.1:8000/agent/run)" \
-H "Content-Type: application/json" \
-d '{
  "goal": "Write a short summary of the key differences between Web2 and Web3.",
  "iterations": 2
}'
```

**Example Response:**

```json
{
  "job_id": "c4e1a2b3-f4d5-6e78-9a01-b2c3d4e5f6a7",
  "status": "pending",
  "message": "Agent run started."
}
```

### ### 2. Check the Task Status

Use the `job_id` from the previous step to poll for updates and results.

```bash
curl [http://127.0.0.1:8000/agent/status/c4e1a2b3-f4d5-6e78-9a01-b2c3d4e5f6a7](http://127.0.0.1:8000/agent/status/c4e1a2b3-f4d5-6e78-9a01-b2c3d4e5f6a7)
```

**Example Response (while in progress):**

```json
{
    "status": "in_progress",
    "progress": 0.5,
    "details": {
        "goal": "Write a short summary of the key differences between Web2 and Web3.",
        "cycle_1": {
            "status": "completed",
            "assessment": { /* ... */ },
            "results": [ /* ... */ ]
        }
    }
}
```

**Example Response (when completed):**

```json
{
    "status": "completed",
    "progress": 1.0,
    "details": {
        /* Full log of all cycles and their results */
    }
}
```

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
