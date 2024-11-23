from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from firebase_admin import auth, firestore
from firebase_utils import add_task, get_tasks, add_user_to_db, db
from gemini import categorize_task
import uuid

app = FastAPI()

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with specific frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Models
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
    """
    Sign up a new user in Firebase Authentication and Firestore.
    """
    try:
        # Create user in Firebase Auth
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


@app.post("/tasks", response_model=TaskResponse)
def create_task(task: TaskInput):
    """
    Create a new task, categorize it using Gemini, and save it to Firestore.
    """
    try:
        # Categorize task description
        category = categorize_task(task.description)

        # Prepare task data
        task_data = {
            "title": task.title,
            "description": task.description,
            "category": category,
            "status": False,  # Default status
        }

        # Save to Firestore
        add_task(task.user_id, task_data)

        return TaskResponse(
            title=task.title,
            description=task.description,
            category=category,
            status=False
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/add-task/", response_model=TaskResponse)
async def add_task_route(task: TaskInput):
    """
    Add a task with unique ID, categorize it, and save to Firestore.
    """
    try:
        # Categorize the task
        category = categorize_task(task.description)

        # Generate unique task ID and prepare data
        task_id = str(uuid.uuid4())
        task_data = {
            "title": task.title,
            "description": task.description,
            "category": category,
            "status": False,
        }

        # Save task to Firestore
        db.collection('tasks').document(task_id).set(task_data)

        return TaskResponse(
            title=task.title,
            description=task.description,
            category=category,
            status=False
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error categorizing or saving task: {str(e)}")


@app.get("/get-tasks/", response_model=list[TaskResponse])
async def get_tasks_route():
    """
    Fetch all tasks from Firestore and return them.
    """
    try:
        tasks_ref = db.collection('tasks')
        tasks = tasks_ref.stream()

        task_list = []
        for task in tasks:
            task_data = task.to_dict()
            task_list.append(TaskResponse(
                title=task_data["title"],
                description=task_data["description"],
                category=task_data["category"],
                status=task_data["status"]
            ))

        return task_list
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching tasks: {str(e)}")


@app.patch("/update-task/{task_id}", response_model=TaskResponse)
async def update_task_status(task_id: str, task_status: bool):
    """
    Update the status of a specific task by ID.
    """
    try:
        task_ref = db.collection('tasks').document(task_id)
        task = task_ref.get()

        if not task.exists:
            raise HTTPException(status_code=404, detail="Task not found")

        # Update the task status
        task_ref.update({"status": task_status})

        task_data = task.to_dict()
        task_data["status"] = task_status

        return TaskResponse(
            title=task_data["title"],
            description=task_data["description"],
            category=task_data["category"],
            status=task_status
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error updating task status: {str(e)}")
