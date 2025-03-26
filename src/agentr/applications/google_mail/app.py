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

    def create_draft(self, to: str, subject: str, body: str) -> str:
        """Create a draft email
        
        Args:
            to: The email address of the recipient
            subject: The subject of the email
            body: The body of the email
            
        Returns:
            A confirmation message with the draft ID
        """
        try:
            url = "https://gmail.googleapis.com/gmail/v1/users/me/drafts"
            
            raw_message = self._create_message(to, subject, body)
            
       
            draft_data = {
                "message": {
                    "raw": raw_message
                }
            }
            
            logger.info(f"Creating draft email to {to}")
            
            response = self._post(url, draft_data)
            
            if response.status_code == 200:
                draft_id = response.json().get("id", "unknown")
                return f"Successfully created draft email with ID: {draft_id}"
            else:
                logger.error(f"Gmail API Error: {response.status_code} - {response.text}")
                return f"Error creating draft: {response.status_code} - {response.text}"
        except NotAuthorizedError as e:
            logger.warning(f"Gmail authorization required: {e.message}")
            return e.message
        except KeyError as key_error:
            logger.error(f"Missing key error: {str(key_error)}")
            return f"Configuration error: Missing required key - {str(key_error)}"
        except Exception as e:
            logger.exception(f"Error creating draft: {type(e).__name__} - {str(e)}")
            return f"Error creating draft: {type(e).__name__} - {str(e)}"

    def send_draft(self, draft_id: str) -> str:
        """Send an existing draft email
        
        Args:
            draft_id: The ID of the draft to send
            
        Returns:
            A confirmation message
        """
        try:
            url = "https://gmail.googleapis.com/gmail/v1/users/me/drafts/send"
            
            draft_data = {
                "id": draft_id
            }
            
            logger.info(f"Sending draft email with ID: {draft_id}")
            
            response = self._post(url, draft_data)
            
            if response.status_code == 200:
                message_id = response.json().get("id", "unknown")
                return f"Successfully sent draft email. Message ID: {message_id}"
            else:
                logger.error(f"Gmail API Error: {response.status_code} - {response.text}")
                return f"Error sending draft: {response.status_code} - {response.text}"
        except NotAuthorizedError as e:
            logger.warning(f"Gmail authorization required: {e.message}")
            return e.message
        except KeyError as key_error:
            logger.error(f"Missing key error: {str(key_error)}")
            return f"Configuration error: Missing required key - {str(key_error)}"
        except Exception as e:
            logger.exception(f"Error sending draft: {type(e).__name__} - {str(e)}")
            return f"Error sending draft: {type(e).__name__} - {str(e)}"

    def get_draft(self, draft_id: str, format: str = "full") -> str:
        """Get a specific draft email by ID
        
        Args:
            draft_id: The ID of the draft to retrieve
            format: The format to return the draft in (minimal, full, raw, metadata)
            
        Returns:
            The draft information or an error message
        """
        try:
            url = f"https://gmail.googleapis.com/gmail/v1/users/me/drafts/{draft_id}"
            
            # Add format parameter as query param
            params = {"format": format}
            
            logger.info(f"Retrieving draft with ID: {draft_id}")
            
            response = self._get(url, params=params)
            
            if response.status_code == 200:
                draft_data = response.json()
                
                # Format the response in a readable way
                message = draft_data.get("message", {})
                headers = {}
                
                # Extract headers if they exist
                for header in message.get("payload", {}).get("headers", []):
                    name = header.get("name", "")
                    value = header.get("value", "")
                    headers[name] = value
                
                to = headers.get("To", "Unknown recipient")
                subject = headers.get("Subject", "No subject")
                
                result = (
                    f"Draft ID: {draft_id}\n"
                    f"To: {to}\n"
                    f"Subject: {subject}\n"
                )
                
                return result
            else:
                logger.error(f"Gmail API Error: {response.status_code} - {response.text}")
                return f"Error retrieving draft: {response.status_code} - {response.text}"
        except NotAuthorizedError as e:
            logger.warning(f"Gmail authorization required: {e.message}")
            return e.message
        except KeyError as key_error:
            logger.error(f"Missing key error: {str(key_error)}")
            return f"Configuration error: Missing required key - {str(key_error)}"
        except Exception as e:
            logger.exception(f"Error retrieving draft: {type(e).__name__} - {str(e)}")
            return f"Error retrieving draft: {type(e).__name__} - {str(e)}"
    
    def list_drafts(self, max_results: int = 20, q: str = None, include_spam_trash: bool = False) -> str:
        """List drafts in the user's mailbox
        
        Args:
            max_results: Maximum number of drafts to return (max 500, default 20)
            q: Search query to filter drafts (same format as Gmail search)
            include_spam_trash: Include drafts from spam and trash folders
            
        Returns:
            A formatted list of drafts or an error message
        """
        try:
            url = "https://gmail.googleapis.com/gmail/v1/users/me/drafts"
            
            # Build query parameters
            params = {
                "maxResults": max_results
            }
            
            if q:
                params["q"] = q
                
            if include_spam_trash:
                params["includeSpamTrash"] = "true"
            
            logger.info(f"Retrieving drafts list with params: {params}")
            
            response = self._get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                drafts = data.get("drafts", [])
                result_size = data.get("resultSizeEstimate", 0)
                
                if not drafts:
                    return "No drafts found."
                
                result = f"Found {len(drafts)} drafts (estimated total: {result_size}):\n\n"
                
                for i, draft in enumerate(drafts, 1):
                    draft_id = draft.get("id", "Unknown ID")
                    # The message field only contains id and threadId at this level
                    result += f"{i}. Draft ID: {draft_id}\n"
                
                if "nextPageToken" in data:
                    result += "\nMore drafts available. Use page token to see more."
                
                return result
            else:
                logger.error(f"Gmail API Error: {response.status_code} - {response.text}")
                return f"Error listing drafts: {response.status_code} - {response.text}"
        except NotAuthorizedError as e:
            logger.warning(f"Gmail authorization required: {e.message}")
            return e.message
        except KeyError as key_error:
            logger.error(f"Missing key error: {str(key_error)}")
            return f"Configuration error: Missing required key - {str(key_error)}"
        except Exception as e:
            logger.exception(f"Error listing drafts: {type(e).__name__} - {str(e)}")
            return f"Error listing drafts: {type(e).__name__} - {str(e)}"

    def list_tools(self):
        return [self.send_email, self.create_draft, self.send_draft, self.get_draft, self.list_drafts]

    