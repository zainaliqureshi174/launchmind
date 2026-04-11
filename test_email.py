import os
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

load_dotenv()

message = Mail(
    from_email=os.getenv("SENDGRID_FROM_EMAIL"),
    to_emails=os.getenv("TO_EMAIL"),
    subject="LaunchMind Test Email",
    html_content="<p>SendGrid is working! LaunchMind agents are ready.</p>"
)

sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
response = sg.send(message)
print(f"Status code: {response.status_code}")