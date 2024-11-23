from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from firebase_utils import add_task, get_tasks, db
from firebase_admin import firestore

app = FastAPI()

# Pydantic models
class TaskInput(BaseModel):
    title: str
    description: str
    user_id: str

class TaskResponse(BaseModel):
    title: str
    description: str
    category: str
    status: bool

@app.get("/tasks/{user_id}")
def get_user_tasks(user_id: str):
    """Retrieve all tasks for a user."""
    try:
        tasks = get_tasks(user_id)
        return tasks
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/friends/request")
def send_friend_request(sender_id: str, receiver_id: str):
    """Send a friend request."""
    sender_ref = db.collection("users").document(sender_id)
    receiver_ref = db.collection("users").document(receiver_id)

    if not receiver_ref.get().exists:
        raise HTTPException(status_code=404, detail="Receiver does not exist")

    # Simulate adding the request to both users (customize to use a separate request collection if needed)
    sender_ref.update({"friend_requests_sent": firestore.ArrayUnion([receiver_id])})
    receiver_ref.update({"friend_requests_received": firestore.ArrayUnion([sender_id])})

    return {"message": "Friend request sent"}

@app.post("/friends/accept")
def accept_friend_request(user_id: str, friend_id: str):
    """Accept a friend request."""
    user_ref = db.collection("users").document(user_id)
    friend_ref = db.collection("users").document(friend_id)

    # Add each user to the other's friends list
    user_ref.update({"friends": firestore.ArrayUnion([friend_id])})
    friend_ref.update({"friends": firestore.ArrayUnion([user_id])})

    # Optionally remove requests from both sides
    user_ref.update({"friend_requests_received": firestore.ArrayRemove([friend_id])})
    friend_ref.update({"friend_requests_sent": firestore.ArrayRemove([user_id])})

    return {"message": "Friend added successfully"}

@app.get("/tasks/friends/{user_id}")
def get_friends_tasks(user_id: str):
    """Fetch all tasks from user's friends."""
    user_ref = db.collection("users").document(user_id)
    user_data = user_ref.get().to_dict()

    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    friends = user_data.get("friends", [])
    all_tasks = []

    # Fetch tasks for each friend
    for friend_id in friends:
        friend_tasks = db.collection("users").document(friend_id).collection("tasks").stream()
        for task in friend_tasks:
            task_data = task.to_dict()
            if not task_data.get("is_private"):  # Only include non-private tasks
                all_tasks.append({**task_data, "friend_id": friend_id})

    return all_tasks
