import base64
import os

from email.message import EmailMessage

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request


SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

TOKEN_PATH = "token.json"


def get_gmail_service():

    if not os.path.exists(TOKEN_PATH):
        raise Exception(
            "token.json not found. Authenticate locally first."
        )

    creds = Credentials.from_authorized_user_file(
        TOKEN_PATH,
        SCOPES
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    return build("gmail", "v1", credentials=creds)


def sendEmail(to, replyTo, subject, body, image_b64):

    try:

        service = get_gmail_service()

        msg = EmailMessage()

        msg["To"] = to
        msg["Subject"] = subject
        msg["Reply-To"] = replyTo
        msg["From"] = replyTo

        msg.set_content(body)

        if image_b64:

            if "base64," in image_b64:
                _, image_b64 = image_b64.split("base64,")

            image_data = base64.b64decode(image_b64)

            msg.add_attachment(
                image_data,
                maintype="image",
                subtype="jpeg",
                filename="issue.jpg"
            )

        raw = base64.urlsafe_b64encode(
            msg.as_bytes()
        ).decode()

        service.users().messages().send(
            userId="me",
            body={"raw": raw}
        ).execute()

        return True

    except Exception as e:
        print(f"Failed to send email: {e}")
        return False