from agentr.application import APIApplication
from agentr.integration import Integration
from loguru import logger
from datetime import datetime, timedelta

class GoogleCalendarApp(APIApplication):
    def __init__(self, integration: Integration) -> None:
        super().__init__(name="google-calendar", integration=integration)

    def _get_headers(self):
        credentials = self.integration.get_credentials()
        if "headers" in credentials:
            return credentials["headers"]
        return {
            "Authorization": f"Bearer {credentials['access_token']}",
            "Accept": "application/json"
        }
    
    
    def get_today_events(self) -> str:
        """Get events from your Google Calendar for today
        
        Returns:
            A formatted list of today's events or an error message
        """
        if not self.validate():
            logger.warning("Connection not configured correctly")
            return self.authorize()
        
        try:
            # Get today's date in ISO format
            today = datetime.now().date()
            tomorrow = today + timedelta(days=1)
            
            # Format dates for API
            time_min = f"{today.isoformat()}T00:00:00Z"
            time_max = f"{tomorrow.isoformat()}T00:00:00Z"
            
            url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
            params = {
                "timeMin": time_min,
                "timeMax": time_max,
                "singleEvents": "true",
                "orderBy": "startTime"
            }
            
            response = self._get(url, params=params)
            
            if response.status_code == 200:
                events = response.json().get("items", [])
                if not events:
                    return "No events scheduled for today."
                
                result = "Today's events:\n\n"
                for event in events:
                    start = event.get("start", {})
                    start_time = start.get("dateTime", start.get("date", "All day"))
                    if "T" in start_time:  # Format datetime
                        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                        start_time = start_dt.strftime("%I:%M %p")
                    
                    summary = event.get("summary", "Untitled event")
                    result += f"- {start_time}: {summary}\n"
                
                return result
            else:
                logger.error(response.text)
                return f"Error retrieving calendar events: {response.text}"
        except Exception as e:
            logger.error(e)
            return f"Error retrieving calendar events: {e}"
    
    def list_tools(self):
        return [self.get_today_events]