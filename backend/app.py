from fastapi import FastAPI, HTTPException, Request 
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from firebase_admin import auth, firestore
from firebase_utils import add_task, get_tasks, add_user_to_db, db
from gemini import categorize_task

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change "*" to your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

class SignUpInput(BaseModel):
    email: str
    password: str
    display_name: str

class SignInInput(BaseModel):
    email: str
    password: str

@app.post("/auth/signup")
def sign_up_user(data: SignUpInput):
    """Sign up a new user and add to the database."""
    try:
        # Create user in Firebase Authentication
        user = auth.create_user(email=data.email, password=data.password, display_name=data.display_name)
        
        # Add user to Firestore
        user_data = {
            "email": data.email,
            "display_name": data.display_name,
            "created_at": firestore.SERVER_TIMESTAMP,
        }
        add_user_to_db(user.uid, user_data)
        
        return {"message": "User created successfully", "user_id": user.uid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/auth/signin")
def sign_in_user(data: SignInInput):
    """Authenticate user. If the user doesn't exist, create a new user."""
    try:
        # Attempt to retrieve the user by email
        try:
            user = auth.get_user_by_email(data.email)
        except auth.UserNotFoundError:
            # If user does not exist, create a new user (if desired)
            user = auth.create_user(email=data.email, password=data.password, display_name=data.email.split('@')[0])

            # Optionally, add the new user to Firestore
            user_data = {
                "email": data.email,
                "display_name": user.display_name,
                "created_at": firestore.SERVER_TIMESTAMP,
            }
            add_user_to_db(user.uid, user_data)

            return {"message": "User created and signed in successfully", "user_id": user.uid}

        # If user exists, simply return the user ID
        return {"message": "Sign-in successful", "user_id": user.uid}
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

@app.get("/users/{user_id}")
def get_user(user_id: str):
    """Retrieve user details from Firestore."""
    user_ref = db.collection("users").document(user_id)
    user = user_ref.get()
    if not user.exists:
        raise HTTPException(status_code=404, detail="User not found")
    return user.to_dict()

@app.post("/tasks", response_model=TaskResponse)
def create_task(task: TaskInput):
    """Create a new task, categorize it, and save to Firestore."""
    try:
        # Categorize the task
        category = categorize_task(task.description)

        # Prepare task data
        task_data = {
            "title": task.title,
            "description": task.description,
            "category": category,
            "status": False,  # Default status (not completed)
        }

        # Save to Firestore
        add_task(task.user_id, task_data)

        return {**task_data, "status": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks/{user_id}")
def get_user_tasks(user_id: str):
    """Retrieve all tasks for a user."""
    try:
        tasks = get_tasks(user_id)
        return tasks
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/friends/request")
def send_friend_request(sender_id: str, receiver_email: str):
    """Send a friend request to a user by email."""
    try:
        # Find the receiver user based on the email
        receiver_ref = db.collection("users").where("email", "==", receiver_email).limit(1).stream()
        receiver_data = None
        for user in receiver_ref:
            receiver_data = user.to_dict()
            receiver_id = user.id
            break
        
        if receiver_data is None:
            raise HTTPException(status_code=404, detail="Receiver not found")

        # Add the sender to the receiver's friend_requests_received
        sender_ref = db.collection("users").document(sender_id)
        sender_ref.update({"friend_requests_sent": firestore.ArrayUnion([receiver_id])})

        # Add the receiver to the sender's friend_requests_sent
        receiver_ref = db.collection("users").document(receiver_id)
        receiver_ref.update({"friend_requests_received": firestore.ArrayUnion([sender_id])})

        return {"message": "Friend request sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/friends/accept")
def accept_friend_request(user_id: str, friend_id: str):
    """Accept a friend request and add both users to each other's friends list."""
    try:
        user_ref = db.collection("users").document(user_id)
        friend_ref = db.collection("users").document(friend_id)

        # Fetch user data
        user_data = user_ref.get().to_dict()
        friend_data = friend_ref.get().to_dict()

        if not user_data or not friend_data:
            raise HTTPException(status_code=404, detail="User not found")

        # Add friend to user's friend list
        user_ref.update({"friends": firestore.ArrayUnion([friend_id])})
        friend_ref.update({"friends": firestore.ArrayUnion([user_id])})

        # Remove the request from both users
        user_ref.update({"friend_requests_received": firestore.ArrayRemove([friend_id])})
        friend_ref.update({"friend_requests_sent": firestore.ArrayRemove([user_id])})

        return {"message": "Friend request accepted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/friends/decline")
def decline_friend_request(user_id: str, friend_id: str):
    """Decline a friend request and remove it from the pending requests."""
    try:
        user_ref = db.collection("users").document(user_id)
        friend_ref = db.collection("users").document(friend_id)

        # Fetch user data
        user_data = user_ref.get().to_dict()
        friend_data = friend_ref.get().to_dict()

        if not user_data or not friend_data:
            raise HTTPException(status_code=404, detail="User not found")

        # Remove the request from the user's pending requests
        user_ref.update({"friend_requests_received": firestore.ArrayRemove([friend_id])})
        friend_ref.update({"friend_requests_sent": firestore.ArrayRemove([user_id])})

        return {"message": "Friend request declined"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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

@app.get("/users/email/{email}")
def find_user_by_email(email: str):
    """Search for a user by email."""
    try:
        users_ref = db.collection("users")
        query = users_ref.where("email", "==", email).limit(1)
        user = query.stream()
        
        user_data = None
        for u in user:
            user_data = u.to_dict()
            break
        
        if user_data is None:
            raise HTTPException(status_code=404, detail="User not found")
        
        return user_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


