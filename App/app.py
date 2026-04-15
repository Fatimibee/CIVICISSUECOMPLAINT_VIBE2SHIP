import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from httpx import RequestError
import base64
import uuid

from Agent.Graph import CivicIssueAgent
from langgraph.types import Command

# 🔥 ROOT APP (wrapper for HF)
app = FastAPI()

# 🔥 ACTUAL API APP
api = FastAPI(
    title="Civic Issue Agent API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# 🔥 MOUNT API (CRITICAL FIX)
app.mount("/", api)

# ✅ CORS
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ INIT GRAPH
graph = CivicIssueAgent()
sessions = {}

# ✅ LOAD GOOGLE CREDS
creds = os.getenv("GOOGLE_CREDS_BASE64")
if creds:
    with open("credentials.json", "wb") as f:
        f.write(base64.b64decode(creds))

token = os.getenv("GOOGLE_TOKEN_BASE64")
if token:
    with open("token.json", "wb") as f:
        f.write(base64.b64decode(token))

# ✅ MODEL
class HumanAction(BaseModel):
    thread_id: str
    approval: bool
    suggestion: str | None = None

# ✅ ROOT
@api.get("/")
def root():
    return {"message": "Civic Issue AI Agent running"}

# ✅ HEALTH
@api.get("/health")
def health():
    return {"status": "OK"}

# ✅ DEBUG ROUTE
@api.get("/check")
def check():
    return {"msg": "routes working"}

# ✅ START ISSUE
@api.post("/start_issue")
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

    except (RequestError, TimeoutError):
        return {
            "status": "NETWORK_ERROR",
            "message": "Check internet / API connection"
        }
    except Exception as e:
        return {
            "status": "ERROR",
            "message": str(e)
        }

    return {"status": "completed"}

# ✅ HUMAN ACTION
@api.post("/human_action")
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

    except Exception as e:
        return {"status": "ERROR", "message": str(e)}