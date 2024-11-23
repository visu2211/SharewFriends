import requests

GEMINI_API_KEY = "your_gemini_api_key"
GEMINI_API_URL = "https://gemini-api-url.com/categorize"  # Replace with actual API endpoint.

def categorize_task(task_description):
    """Send a task description to the Gemini API for categorization."""
    response = requests.post(
        GEMINI_API_URL,
        headers={"Authorization": f"Bearer {GEMINI_API_KEY}", "Content-Type": "application/json"},
        json={"task_description": task_description},
    )
    if response.status_code == 200:
        return response.json().get("category", "Uncategorized")
    else:
        raise Exception(f"Gemini API error: {response.status_code} - {response.text}")