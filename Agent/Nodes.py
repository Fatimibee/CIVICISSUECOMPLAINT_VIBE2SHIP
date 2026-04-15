from Agent.States import AgentState
from Core.SendMail import *
from Data.labels import CIVIC_LABELS
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_core.prompts import ChatPromptTemplate
from langgraph.types import interrupt
from PIL import Image
import io
import base64
import os
from dotenv import load_dotenv
from transformers import CLIPProcessor, CLIPModel
import torch
import requests
from langgraph.types import interrupt, Command
import uuid
import cloudinary
import cloudinary.uploader

load_dotenv()
DepartmentAPI = os.getenv("DEPARTMENT_API")
SaveIssueAPI  = os.getenv("Save_Issue_API")
HF_TOKEN      = os.getenv("HF_TOKEN")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Image Saving at cloudinary cloud storage
cloudinary.config(
    cloud_name=os.getenv("CLOUD_NAME"),
    api_key=os.getenv("CLOUD_API_KEY"),
    api_secret=os.getenv("CLOUD_API_SECRET")
)
# CLIP MODEL

clip_model = None
processor   = None

def load_clip():
    global clip_model, clip_processor

    if clip_model is None:
        clip_model = CLIPModel.from_pretrained(
            "openai/clip-vit-base-patch32",
            low_cpu_mem_usage=True
        )

        clip_processor = CLIPProcessor.from_pretrained(
            "openai/clip-vit-base-patch32"
        )

    return clip_model, clip_processor
# HuggingFace LLM

_endpoint = HuggingFaceEndpoint(
    repo_id="Qwen/Qwen2.5-7B-Instruct",
    huggingfacehub_api_token=HF_TOKEN,
    task="conversational",
    max_new_tokens=500,
    temperature=0.3,
)
llm = ChatHuggingFace(llm=_endpoint)

# NODE : IMAGE CLASSIFY

def IssueClassify(state: AgentState):

    clip_model, clip_processor = load_clip()

    image_base64 = state["issueimage"]
    image_data = image_base64.split(",")[1]
    image_bytes = base64.b64decode(image_data)

    image = Image.open(io.BytesIO(image_bytes))

    inputs = clip_processor(
        text=CIVIC_LABELS,
        images=image,
        return_tensors="pt",
        padding=True
    )

    with torch.no_grad():
        outputs = clip_model(**inputs)

    probs = outputs.logits_per_image.softmax(dim=1)

    score, idx = torch.max(probs, dim=1)

    issue = CIVIC_LABELS[idx.item()]
    score = float(score.item())

    return {"issueClass": issue, "issueScore": score}

# NODE : IMAGE QUALITY

def ImageQuality(state: AgentState):
    # Read directly from state — score set by IssueClassify
    print("FULL STATE IN IMAGEQUALITY:", dict(state))  #  add this
    
    score = state.get("issueScore", 0)
    print("Running ImageQuality | Score:", score)

    if score < 0.55:
        print("Score too low → LowScoreEND")
        return {"errorMessage":"Please Upload Clear Image"}

    print("Score OK → DepartmentInfo")
    return {"errorMessage":None}


# NODE : LOW SCORE END
def LowScoreEND(state: AgentState):
    return {"errorMessage": "Please upload a clear image. Issue could not be identified confidently."}

def ImageRouter(state:AgentState):
    if(state['issueScore'] <0.55) :
        return "LowScoreEND"
    else:
        return "DepartmentInfo"


# NODE : DEPARTMENT INFO
def DepartmentInfo(state: AgentState):
    print("Running DepartmentInfo")
    issue = state["issueClass"]
    url   = f"{DepartmentAPI}/{issue}"

    try:
        response = requests.get(url)
        if response.status_code != 200:
            print("Department API bad status:", response.status_code)
            return {"departmentEmail": None, "departmentId": None}

        data = response.json()
        print("Department Email:", data.get("email"))
        return {
            "departmentEmail": data.get("email"),
            "departmentId":    data.get("department_id"),
        }

    except Exception as e:
        print("Department API error:", e)
        return {"departmentEmail": None, "departmentId": None}



# NODE : EMAIL GENERATOR

def EmailGenerator(state: AgentState):
    print("Running EmailGenerator")

    issue      = state["issueClass"]
    department = state["departmentEmail"]
    location   = state["location"]
    suggestion = state.get("editSuggestion") or "None"
    userEmail  = state["userEmail"]

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are an AI assistant that writes professional civic complaint emails. "
            "Write short, clear , polite  and issue , causes explanable emails."
        ),
        (
            "human",
            """
Write a civic complaint email.

Issue: {issue}
Location: {location}
Suggestion: {suggestion}

Citizen Email: {userEmail}

Rules:
- Include a subject line
- Mention the issue and location
- Mention that an image is attached
- End the email with the citizen email provided
- Do NOT use placeholders like [Your Name]
- Do add Only Dear Sir / Madam .
"""
        )
    ])

    chain = prompt | llm

    response = chain.invoke({
        "issue": issue,
        "location": location,
        "suggestion": suggestion,
        "userEmail": userEmail
    })

    print("Draft:\n", response.content)

    return {"emailDraft": response.content}

# NODE : HUMAN APPROVAL
def HumanApproval(state: AgentState):

    print("Running HumanApproval")

    decision = interrupt({
        "emailDraft": state["emailDraft"],
        "message": "Approve or edit this email"
    })

    if decision.get("approval"):
        print("User Approved Email")
        return {"approval": True}

    print("User suggested edit:", decision.get("editSuggestion"))

    return {
        "approval": False,
        "editSuggestion": decision.get("editSuggestion")
    }

# ROUTER : APPROVAL

def approvalRouter(state: AgentState):
    if state.get("approval"):
        return "sendAndSaveEmailNode"
    return "EmailGenerator"



# NODE : SEND EMAIL + SAVE

def sendAndSaveEmailNode(state: AgentState):
    print("--- Running sendAndSaveEmailNode ---")

    # 1. -------- DECODE IMAGE --------
    image_base64 = state.get("issueimage", "")
    image_url = None

    if image_base64:
        try:
            # Handle potential header in base64 string
            if "," in image_base64:
                image_data = image_base64.split(",")[1]
            else:
                image_data = image_base64
            
            image_bytes = base64.b64decode(image_data)

            # 2. -------- UPLOAD TO CLOUDINARY --------
            upload_result = cloudinary.uploader.upload(io.BytesIO(image_bytes), resource_type="image")
            image_url = upload_result.get("secure_url")
            print(f"Cloudinary Upload Success: {image_url}")
        except Exception as e:
            print(f"Cloudinary Upload Error: {e}")
            # We continue even if upload fails, image_url will be None

    # 3. -------- SEND EMAIL --------
    # Using the original base64 for the email attachment as per your sendEmail logic
    email_success = False
    try:
        email_success = sendEmail(
            to=state["departmentEmail"],
            replyTo=state["userEmail"],
            subject=f"REPORT: {state['issueClass']} at {state['location']}",
            body=state["emailDraft"],
            image_b64=image_base64,
        )
    except Exception as e:
        print(f"Email Dispatch Error: {e}")

    # 4. -------- SAVE ISSUE IN DATABASE --------
    dbStatus = False
    try:
        payload = {
            "email": state["userEmail"],
            "issue_type": state["issueClass"],
            "location": state["location"],
            "department_id": state["departmentId"],
            "image_url": image_url # This is the hosted Cloudinary URL
        }

        print("Sending to Save API...")
        response = requests.post(SaveIssueAPI, json=payload, timeout=10)
        
        # FIX: Check for 200 (OK) OR 201 (Created)
        if 200 <= response.status_code < 300:
            dbStatus = True
            print(f"Save API Success ({response.status_code}): {response.text}")
        else:
            dbStatus = False
            print(f"Save API Failed ({response.status_code}): {response.text}")

    except Exception as e:
        print(f"Save API Critical Error: {e}")

    print(f"FINAL STATUS | Email Sent: {email_success} | DB Saved: {dbStatus}")

    return {
        "emailSend": email_success,
        "issueSaved": dbStatus,
        "image_url": image_url
    }