from agentr.application import APIApplication
from agentr.integration import Integration
from agentr.exceptions import NotAuthorizedError
from loguru import logger
import base64
from email.message import EmailMessage

class GmailApp(APIApplication):
    def __init__(self, integration: Integration) -> None:
        super().__init__(name="gmail", integration=integration)

    def _get_headers(self):
        if not self.integration:
            raise ValueError("Integration not configured for GmailApp")
        credentials = self.integration.get_credentials()
        if not credentials:
            logger.warning("No Gmail credentials found via integration.")
            action = self.integration.authorize()
            raise NotAuthorizedError(action)
            
        if "headers" in credentials:
            return credentials["headers"]
        return {
            "Authorization": f"Bearer {credentials['access_token']}",
            'Content-Type': 'application/json'
        }

    def send_email(self, to: str, subject: str, body: str) -> str:
        """Send an email
        
        Args:
            to: The email address of the recipient
            subject: The subject of the email
            body: The body of the email
            
        Returns:
            A confirmation message
        """
        try:
            url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
            
            # Create email in base64 encoded format
            raw_message = self._create_message(to, subject, body)
            
            # Format the data as expected by Gmail API
            email_data = {
                "raw": raw_message
            }
            
            logger.info(f"Sending email to {to}")
            
            response = self._post(url, email_data)
            
            if response.status_code == 200:
                return f"Successfully sent email to {to}"
            else:
                logger.error(f"Gmail API Error: {response.status_code} - {response.text}")
                return f"Error sending email: {response.status_code} - {response.text}"
        except NotAuthorizedError as e:
            # Return the authorization message directly
            logger.warning(f"Gmail authorization required: {e.message}")
            return e.message
        except KeyError as key_error:
            logger.error(f"Missing key error: {str(key_error)}")
            return f"Configuration error: Missing required key - {str(key_error)}"
        except Exception as e:
            logger.exception(f"Error sending email: {type(e).__name__} - {str(e)}")
            return f"Error sending email: {type(e).__name__} - {str(e)}"
            
    def _create_message(self, to, subject, body):
        try:
            message = EmailMessage()
            message['to'] = to
            message['subject'] = subject
            message.set_content(body)
            
            # Use "me" as the default sender
            message['from'] = "me"
            
            # Encode as base64 string
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            return raw
        except Exception as e:
            logger.error(f"Error creating message: {str(e)}")
            raise
    
    def list_tools(self):
        return [self.send_email]