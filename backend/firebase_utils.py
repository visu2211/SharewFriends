import firebase_admin
from firebase_admin import firestore, credentials
from firebase_admin import auth

cred = credentials.Certificate("firekey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

def create_user(email, password):
    """Create a new user in Firebase."""
    return auth.create_user(email=email, password=password)

def sign_in(email, password):
    """Sign in a user (requires Firebase Authentication setup)."""
    # Use Firebase client-side SDK for generating tokens
    raise NotImplementedError("Use Firebase client SDK for password-based sign-in.")

def add_user_to_db(user_id, user_data):
    """Add a user to the Firestore database."""
    db.collection("users").document(user_id).set(user_data)

def add_task(user_id, task_data):
    """Add a task to Firestore for a specific user."""
    tasks_ref = db.collection("users").document(user_id).collection("tasks")
    tasks_ref.add(task_data)

def get_tasks(user_id):
    """Retrieve tasks for a specific user."""
    tasks_ref = db.collection("users").document(user_id).collection("tasks")
    return [doc.to_dict() for doc in tasks_ref.stream()]