from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from httpx import RequestError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import base64
import uuid

import os
import base64
from Agent.Graph import CivicIssueAgent
from langgraph.types import Command

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

graph = CivicIssueAgent()

sessions = {}


creds = os.getenv("GOOGLE_CREDS_BASE64")

if creds:
    with open("credentials.json", "wb") as f:
        f.write(base64.b64decode(creds))

token = os.getenv("GOOGLE_TOKEN_BASE64")

if token:
    with open("token.json", "wb") as f:
        f.write(base64.b64decode(token))
# Pydantic Model

class HumanAction(BaseModel):
    thread_id: str
    approval: bool
    suggestion: str | None = None

@app.get("/")
async def root():
    return {"message": "Civic Issue AI Agent running"}

@app.get("/health")
async def home():
    return {"status": "OK"}

@app.post("/start_issue")
async def start_issue(
    image: UploadFile = File(...),
    userEmail: str = Form(...),
    location: str = Form(...)
):
    try:
        image_bytes = await image.read()
        encoded = base64.b64encode(image_bytes).decode()
        image_base64 = f"data:image/jpeg;base64,{encoded}"

        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}

        initial_input = {
            "issueimage": image_base64,
            "userEmail": userEmail,
            "location": location,
        }

        # Wrap the stream in a try block to catch LLM/Network timeouts
        for event in graph.stream(initial_input, config=config):
            node = list(event.keys())[0]

            if node == "LowScoreEND":
                state = graph.get_state(config)
                return {
                    "status": "IMAGE_TOO_UNCLEAR",
                    "message": state.values.get("errorMessage"),
                }

            if node == "EmailGenerator":
                state = graph.get_state(config)
                sessions[thread_id] = config
                return {
                    "status": "WAITING_FOR_APPROVAL",
                    "thread_id": thread_id,
                    "issue": state.values.get("issueClass"),
                    "location": state.values.get("location"),
                    "emailDraft": state.values.get("emailDraft"),
                }

    except (RequestError, TimeoutError) as e:
        print(f"Network Error: {e}")
        return {
            "status": "NETWORK_ERROR", 
            "message": "Please check your internet connection ."
        }
    except Exception as e:
        print(f"General Error: {str(e)}")
        return {
            "status": "ERROR",
            "message": "An unexpected error occurred while processing the request."
        }

    return {"status": "completed"}


@app.post("/human_action")
async def human_action(data: HumanAction):
    config = sessions.get(data.thread_id)
    if not config:
        return {"error": "Invalid session"}

    try:
        if data.approval:
            command = Command(resume={"approval": True})
        else:
            command = Command(resume={"approval": False, "editSuggestion": data.suggestion})

        for _ in graph.stream(command, config=config):
            pass

        state = graph.get_state(config)
        return {
            "emailSent": state.values.get("emailSend"),
            "issueSaved": state.values.get("issueSaved"),
        }
        
    except (RequestError, TimeoutError):
        return {"status": "ERROR", "message": "Connection timed out. Email may not have been sent."}
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}