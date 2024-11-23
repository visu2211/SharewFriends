import firebase_admin
from firebase_admin import firestore, credentials

cred = credentials.Certificate("firekey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

def add_task(user_id, task_data):
    """Add a task to Firestore for a specific user."""
    tasks_ref = db.collection("users").document(user_id).collection("tasks")
    tasks_ref.add(task_data)

def get_tasks(user_id):
    """Retrieve tasks for a specific user."""
    tasks_ref = db.collection("users").document(user_id).collection("tasks")
    return [doc.to_dict() for doc in tasks_ref.stream()]