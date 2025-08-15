# tools.py
import json
from duckduckgo_search import DDGS

print("Initializing tools...")

def perform_web_search(query: str) -> str:
    """
    Performs a web search using the DuckDuckGo Search API and returns the top results.

    Args:
        query: The search query.

    Returns:
        A formatted string of the top search results or an error message.
    """
    try:
        print(f"TOOL: Performing web search for query: '{query}'")
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=5)]
            if not results:
                return "No results found."
            
            # Format the results for the LLM
            formatted_results = "Search Results:\n"
            for r in results:
                formatted_results += f"- Title: {r.get('title', 'N/A')}\n"
                formatted_results += f"  Snippet: {r.get('body', 'N/A')}\n"
                formatted_results += f"  Link: {r.get('href', 'N/A')}\n\n"
            return formatted_results
    except Exception as e:
        return f"Error during web search: {e}"

# A dictionary mapping tool names to their functions
available_tools = {
    "web_search": perform_web_search,
}
print("Tools initialized.")
