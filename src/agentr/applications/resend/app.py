from agentr.application import APIApplication
from agentr.integration import Integration

class ResendApp(APIApplication):
    def __init__(self, user_id, integration: Integration) -> None:
        super().__init__(name="resend", user_id=user_id, integration=integration)

    def send_email(self, to: str, subject: str, content: str) -> str:
        """Send an email using the Resend API

        Args:
            to: The email address to send the email to
            subject: The subject of the email
            content: The content of the email
            
        Returns:
            A message indicating that the email was sent successfully
        """
        url = "https://api.resend.com/emails"
        body = {
            "from": "Manoj <manoj@agentr.dev>",
            "to": [to],
            "subject": subject,
            "text": content
        }
        self._post(url, body)
        return "Sent Successfully"

    def list_tools(self):
        return [self.send_email]

