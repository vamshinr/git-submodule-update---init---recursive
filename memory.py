# memory.py
import asyncio
import chromadb
from chromadb.utils import embedding_functions

class MemoryManager:
    """Manages the agent's long-term memory using ChromaDB with async support."""
    def __init__(self, db_directory: str, collection_name: str):
        print("Initializing memory manager...")
        self.client = chromadb.PersistentClient(path=db_directory)
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"}
        )
        # Mutex to ensure only one async task writes to the DB at a time
        self.lock = asyncio.Lock()
        print("Memory manager initialized.")

    async def add_memory(self, task_description: str, learning: str):
        """Adds a new memory to the collection in an async-safe manner."""
        memory_text = f"From the task '{task_description}', I learned: {learning}"
        memory_id = str(hash(memory_text))
        
        async with self.lock:
            # This block is the critical section protected by the mutex
            try:
                self.collection.add(
                    documents=[memory_text],
                    ids=[memory_id]
                )
                print(f"MEMORY: Added learning to collection: '{learning[:50]}...'")
            except Exception as e:
                print(f"Error adding memory: {e}")

    async def retrieve_relevant_memories(self, query: str, n_results: int = 3) -> str:
        """Retrieves the most relevant memories for a given query."""
        # This operation is read-only and generally thread-safe in Chroma,
        # so we don't need a lock here, which improves performance.
        if self.collection.count() == 0:
            return "No memories available yet."
            
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=min(n_results, self.collection.count())
            )
            memories = results['documents'][0]
            if not memories: return "No relevant memories found."

            formatted_memories = "Relevant Past Learnings:\n"
            for mem in memories:
                formatted_memories += f"- {mem}\n"
            
            print(f"MEMORY: Retrieved {len(memories)} relevant memories for query: '{query}'")
            return formatted_memories
        except Exception as e:
            print(f"Error retrieving memories: {e}")
            return "Could not retrieve memories due to an error."
