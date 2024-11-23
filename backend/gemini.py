import google.generativeai as genai

model = genai.GenerativeModel("gemini-1.5-flash")

def categorize_task(task_description):
    """Categorizes a task into 'urgent', 'personal', 'professional', 'school'.
    The way you categorize this can be as follows:
    "apply to internships" - professional
    "study for test" - school
    "gym, errands" - personal
    "exam tonight" - urgent
    Args:
        task_description (str): The task to be categorized.

    Returns:
        str: The categorized task as a JSON string.
    """

    prompt = f"You are helping a to do app. Categorize the following task: {task_description}. Choose from 'urgent', 'personal', or 'professional'."

    # Configure the API key (replace with your actual API key)
    genai.configure(api_key="AIzaSyDn_nM6Z5iaY3n7f_jCUC5nE-KollzMJcg")

    # Generate text using the Gemini model
    response = model.generate_content(prompt)

    # Extract the category from the response
    category = response.text.strip()

    # Create the JSON response
    json_response = {
        "task": task_description,
        "category": category
    }

    return json_response

task_description = "go get eggs"
categorized_task = categorize_task(task_description)
print(categorized_task)