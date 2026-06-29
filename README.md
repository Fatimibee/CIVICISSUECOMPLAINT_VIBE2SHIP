---
title: Civic Issue Reporting System
emoji: 🏛️
sdk: streamlit
app_file: app.py
colorFrom: blue
colorTo: green
---

# 🏛️ Civic Issue Reporting System
### AI-Powered Infrastructure Complaint Automation Platform

>

An intelligent civic complaint automation platform that detects public infrastructure issues (such as potholes) from uploaded images, classifies the issue using AI, automatically generates an official complaint email, and routes it through a **Human-in-the-Loop (HITL)** approval workflow before dispatching it via the **Google Gmail API**.

---

# ✨ Features

- 📷 AI-based image classification of civic issues
- 🧠 LangGraph workflow automation
- 🤖 Gemini-powered complaint generation
- 👤 Human-in-the-Loop approval panel
- 📧 Automatic Gmail API email dispatch
- ☁️ Cloudinary image storage
- 🗄️ Database integration
- ⚡ FastAPI backend
- 🎨 Streamlit dashboard
- 🔄 Stateful workflow execution

---

# 🏗️ Project Architecture

```
Citizen Upload
       │
       ▼
Image Classification (AI)
       │
       ▼
Issue Categorization
       │
       ▼
Complaint Email Generation
       │
       ▼
Human Review (HITL)
       │
 Approved? ────────────── No
       │                  │
      Yes                 │
       │                  ▼
       ▼             Rewrite/Edit
Send Email via Gmail API
       │
       ▼
Complaint Registered
```

---

# 📁 Project Structure

```text
.
├── Agent/
│   ├── Graph.py          # LangGraph workflow
│   ├── Nodes.py          # Workflow nodes
│   └── States.py         # Agent state definitions
│
├── App/
│   └── app.py            # Streamlit frontend
│
├── Core/
│   └── SendMail.py       # Gmail API integration
│
├── Services/             # Business logic
│
├── .env                  # Environment variables
├── credentials.json      # Google OAuth credentials
├── token.json            # Gmail OAuth token
├── main.py               # FastAPI backend
├── requirements.txt
└── README.md
```

---

# ⚙️ Technology Stack

| Category | Technology |
|-----------|------------|
| Language | Python |
| Backend | FastAPI |
| Frontend | Streamlit |
| Workflow | LangGraph |
| AI Model | Google Gemini |
| Email | Gmail API |
| Image Hosting | Cloudinary |
| Database | MySQL |
| Authentication | Google OAuth2 |

---

# 🚀 Installation

## 1. Clone Repository

```bash
git clone https://github.com/Fatimibee/CIVICISSUECOMPLAINT_VIBE2SHIP.git

cd Civic-Issue-Reporting-System
```

---

## 2. Create Virtual Environment

### Windows

```bash
python -m venv venv

venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv venv

source venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

# 🔐 Environment Configuration

Create a `.env` file in the project root.

```env
GEMINI_API_KEY=YOUR_GEMINI_API_KEY

DB_HOST=localhost
DB_USER=root
DB_PASS=YourPassword
DB_NAME=civic_db

CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=
```

---

# 📧 Gmail API Setup

## Step 1

Visit

https://console.cloud.google.com/

---

## Step 2

Create a project.

---

## Step 3

Enable

- Gmail API

---

## Step 4

Create OAuth Desktop Credentials.

---

## Step 5

Download

```
credentials.json
```

Place it in the project root.

```
project/
│
├── credentials.json
```

---

## Step 6

Run the backend once.

```bash
python -m uvicorn App.app:app --reload  
```

A browser window will open for Gmail authentication.

After successful authentication,

```
token.json
```

will be generated automatically.

---

# ▶️ Running the Project

## Start FastAPI

```bash
python -m uvicorn App.app:app --reload  
```

Backend:

```
http://127.0.0.1:8000
```

Swagger Documentation:

```
http://127.0.0.1:8000/docs
```

---

## Start Streamlit

Open another terminal.

```bash
streamlit run app.py
```

Frontend:

```
http://localhost:8501
```

---

# 🔄 Workflow

```
Upload Image
      │
      ▼
POST /start_issue
      │
      ▼
AI Classification
      │
      ▼
Generate Complaint
      │
      ▼
Human Approval Panel
      │
      ├───────────── Reject
      │
      ▼
Approve
      │
      ▼
POST /human_action
      │
      ▼
Gmail API
      │
      ▼
Complaint Sent
```

---

# 📡 API Endpoints

## POST `/start_issue`

Starts a new complaint workflow.

### Input

```
multipart/form-data
```

### Request

- Image File

### Process

- Generates thread ID
- Runs LangGraph
- Detects issue
- Generates complaint email
- Stops at HITL approval

---

## POST `/human_action`

Continues the workflow after human review.

### Input

```json
{
  "thread_id": "...",
  "action": "approve"
}
```

or

```json
{
  "thread_id": "...",
  "action": "rewrite",
  "feedback": "Mention that this pothole is near a school."
}
```

### Process

- Resume workflow
- Rewrite if required
- Send official email
- Attach uploaded evidence

---

# 🧠 AI Workflow

```
Image
   │
   ▼
Gemini Vision
   │
   ▼
Issue Classification
   │
   ▼
Department Detection
   │
   ▼
Complaint Draft
   │
   ▼
Human Approval
   │
   ▼
Email Dispatch
```

---

# 📷 Dashboard Features

- Upload civic issue image
- AI classification
- View generated complaint
- Edit complaint
- Approve or rewrite
- Email dispatch status
- Thread tracking

---

# 📂 Required Files

```
credentials.json
```

Google OAuth Credentials

```
token.json
```

Generated automatically after first login.

```
.env
```

Stores API keys and database credentials.

---

# 🛡️ Human-in-the-Loop (HITL)

Before sending any complaint:

- AI generates the complaint.
- User reviews the draft.
- User can edit the complaint.
- User can request regeneration.
- Email is sent only after approval.

This ensures reliability and prevents incorrect automated submissions.

---

# 📌 Future Improvements

- SMS notifications
- WhatsApp integration
- GPS location detection
- Complaint tracking portal
- Department auto-routing
- Multi-language support
- Admin analytics dashboard
- Mobile application
- GIS map visualization

---

# 🤝 Contributing

Contributions are welcome!

1. Fork the repository

2. Create a feature branch

```bash
git checkout -b feature-name
```

3. Commit changes

```bash
git commit -m "Add feature"
```

4. Push

```bash
git push origin feature-name
```

5. Open a Pull Request

---