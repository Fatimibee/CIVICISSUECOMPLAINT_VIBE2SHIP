from langchain_google_genai import ChatGoogleGenerativeAI

from Agent.States import AgentState
from Core.SendMail import *
from Data.labels import CIVIC_LABELS
from langchain_core.prompts import ChatPromptTemplate
from langgraph.types import interrupt
from PIL import Image
import io
import base64
import os
import re
from dotenv import load_dotenv
import requests
from langgraph.types import interrupt, Command
import uuid
import cloudinary
import cloudinary.uploader
from google import genai
import json
import mysql.connector
import traceback
from google.genai import types
from pydantic import BaseModel, Field

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")

def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)


# 1. Define the structure you want Gemini to return
class CivicIssueSchema(BaseModel):
    issue_type: str = Field(description="The short category of the civic issue (e.g., pothole, garbage, broken streetlight)")
    confidence: float = Field(description="Confidence score as a float between 0.0 and 1.0")

def IssueClassify(state: AgentState):
    print("\n--- [START] Running IssueClassify Node ---")

    image_base64 = state.get("issueimage", "")
    if not image_base64:
        print("🚨 Error: state['issueimage'] is empty or missing.")
        return {"issueClass": "unknown", "issueScore": 0.0}

    try:
        # 2. Extract and decode the raw base64 data strings cleanly
        if "," in image_base64:
            image_data = image_base64.split(",")[1]
        else:
            image_data = image_base64
        image_bytes = base64.b64decode(image_data)

       
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        # 4. Wrap image bytes inside the modern SDK Part layout
        image_part = types.Part.from_bytes(
            data=image_bytes,
            mime_type="image/jpeg"
        )

        print("[DEBUG] Dispatching payload with native structural schema...")
        
        # 5. Request structured JSON extraction directly from the model
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                image_part,
                "Analyze this image and identify the type of civic complaint or hazard shown."
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=CivicIssueSchema,
            ),
        )

        # 6. Parse out the structured response fields directly
        print(f"[DEBUG] Raw JSON back from model: {response.text}")
        result = json.loads(response.text)
        
        print(f"✅ CLASSIFICATION SUCCESS: {result['issue_type']} ({result['confidence']})")
        return {
            "issueClass": result["issue_type"],
            "issueScore": float(result["confidence"])
        }

    except Exception as e:
        print("\n" + "!" * 60)
        print("🚨 CRITICAL SYSTEM EXCEPTION CAUGHT IN 'IssueClassify':")
        
        # Look for the specific Google API Error details
        if hasattr(e, 'status_code'):
            print(f"Google API Status Code: {e.status_code}")
        if hasattr(e, 'message'):
            print(f"Google API Error Message: {e.message}")
            
        print("\n--- FULL TRACEBACK ---")
        traceback.print_exc()
        print("!" * 60 + "\n")
        
        return {"issueClass": "unknown", "issueScore": 0.0}
    
    
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

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
         "SELECT department_id, email FROM departments WHERE LOWER(issue_type) = LOWER(%s)",
        (issue,)
        )
        data = cursor.fetchone()
        cursor.close()
        conn.close()

        if not data:
            print("No department mapped for issue:", issue)
            return {"departmentEmail": None, "departmentId": None}

        print("Department Email:", data["email"])
        return {
            "departmentEmail": data["email"],
            "departmentId":    data["department_id"],
        }

    except Exception as e:
        print("Department DB error:", e)
        return {"departmentEmail": None, "departmentId": None}

# NODE : EMAIL GENERATOR
def EmailGenerator(state: AgentState):
    
    llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GEMINI_API_KEY"),
    temperature=0.3
    )
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

    # 3. -------- SEND EMAIL --------
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
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO issues (issue_id, email, issue_type, location, department_id, image_url)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            str(uuid.uuid4()),
            state["userEmail"],
            state["issueClass"],
            state["location"],
            state["departmentId"],
            image_url
        ))
        conn.commit()
        cursor.close()
        conn.close()
        dbStatus = True
        print("Issue saved to DB")

    except Exception as e:
        print(f"DB Save Error: {e}")

    #  CRITICAL FIX: Return the keys so LangGraph updates your AgentState
    return {
        "emailSend": email_success,
        "issueSaved": dbStatus
    }