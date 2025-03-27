from agentr.application import APIApplication
from agentr.integration import Integration
from agentr.exceptions import NotAuthorizedError
from loguru import logger
from datetime import datetime, timedelta

class GoogleCalendarApp(APIApplication):
    def __init__(self, integration: Integration) -> None:
        super().__init__(name="google-calendar", integration=integration)
        self.base_api_url = "https://www.googleapis.com/calendar/v3/calendars/primary"

    def _get_headers(self):
        if not self.integration:
            raise ValueError("Integration not configured for GoogleCalendarApp")
        credentials = self.integration.get_credentials()
        if not credentials:
            logger.warning("No Google Calendar credentials found via integration.")
            action = self.integration.authorize()
            raise NotAuthorizedError(action)
            
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
        try:
            # Get today's date in ISO format
            today = datetime.now().date()
            tomorrow = today + timedelta(days=1)
            
            # Format dates for API
            time_min = f"{today.isoformat()}T00:00:00Z"
            time_max = f"{tomorrow.isoformat()}T00:00:00Z"
            
            url = f"{self.base_api_url}/events"
            params = {
                "timeMin": time_min,
                "timeMax": time_max,
                "singleEvents": "true",
                "orderBy": "startTime"
            }
            
            logger.info(f"Retrieving calendar events for today ({today.isoformat()})")
            
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
                logger.error(f"Google Calendar API Error: {response.status_code} - {response.text}")
                return f"Error retrieving calendar events: {response.status_code} - {response.text}"
        except NotAuthorizedError as e:
            logger.warning(f"Google Calendar authorization required: {e.message}")
            return e.message
        except Exception as e:
            logger.exception(f"Error retrieving calendar events: {type(e).__name__} - {str(e)}")
            return f"Error retrieving calendar events: {type(e).__name__} - {str(e)}"
    
    def list_tools(self):
        return [self.get_today_events]

    def get_event(self, event_id: str, max_attendees: int = None, time_zone: str = None) -> str:
        """Get a specific event from your Google Calendar by ID
        
        Args:
            event_id: The ID of the event to retrieve
            max_attendees: Optional. The maximum number of attendees to include in the response
            time_zone: Optional. Time zone used in the response (default is calendar's time zone)
            
        Returns:
            A formatted event details or an error message
        """
        try:
            url = f"{self.base_api_url}/events/{event_id}"
            
            # Build query parameters
            params = {}
            if max_attendees is not None:
                params["maxAttendees"] = max_attendees
            if time_zone:
                params["timeZone"] = time_zone
            
            logger.info(f"Retrieving calendar event with ID: {event_id}")
            
            response = self._get(url, params=params)
            
            if response.status_code == 200:
                event = response.json()
                
                # Extract event details
                summary = event.get("summary", "Untitled event")
                description = event.get("description", "No description")
                location = event.get("location", "No location specified")
                
                # Format dates
                start = event.get("start", {})
                end = event.get("end", {})
                
                start_time = start.get("dateTime", start.get("date", "Unknown"))
                end_time = end.get("dateTime", end.get("date", "Unknown"))
                
                # Format datetime if it's a datetime (not all-day)
                if "T" in start_time:
                    start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                    start_time = start_dt.strftime("%Y-%m-%d %I:%M %p")
                
                if "T" in end_time:
                    end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                    end_time = end_dt.strftime("%Y-%m-%d %I:%M %p")
                
                # Get creator and organizer
                creator = event.get("creator", {}).get("email", "Unknown")
                organizer = event.get("organizer", {}).get("email", "Unknown")
                
                # Check if it's a recurring event
                recurrence = "Yes" if "recurrence" in event else "No"
                
                # Get attendees if any
                attendees = event.get("attendees", [])
                attendee_info = ""
                if attendees:
                    attendee_info = "\nAttendees:\n"
                    for i, attendee in enumerate(attendees, 1):
                        email = attendee.get("email", "No email")
                        name = attendee.get("displayName", email)
                        response_status = attendee.get("responseStatus", "Unknown")
                        
                        status_mapping = {
                            "accepted": "Accepted",
                            "declined": "Declined",
                            "tentative": "Maybe",
                            "needsAction": "Not responded"
                        }
                        
                        formatted_status = status_mapping.get(response_status, response_status)
                        attendee_info += f"  {i}. {name} ({email}) - {formatted_status}\n"
                
                # Format the response
                result = f"Event: {summary}\n"
                result += f"ID: {event_id}\n"
                result += f"When: {start_time} to {end_time}\n"
                result += f"Where: {location}\n"
                result += f"Description: {description}\n"
                result += f"Creator: {creator}\n"
                result += f"Organizer: {organizer}\n"
                result += f"Recurring: {recurrence}\n"
                result += attendee_info
                
                return result
            elif response.status_code == 404:
                return f"Event not found with ID: {event_id}"
            else:
                logger.error(f"Google Calendar API Error: {response.status_code} - {response.text}")
                return f"Error retrieving event: {response.status_code} - {response.text}"
        except NotAuthorizedError as e:
            logger.warning(f"Google Calendar authorization required: {e.message}")
            return e.message
        except Exception as e:
            logger.exception(f"Error retrieving event: {type(e).__name__} - {str(e)}")
            return f"Error retrieving event: {type(e).__name__} - {str(e)}"

    def list_tools(self):
        return [self.get_event,self.get_today_events]

    def list_events(self, max_results: int = 10, time_min: str = None, time_max: str = None, 
                   q: str = None, order_by: str = "startTime", single_events: bool = True,
                   time_zone: str = None, event_types: list = None, page_token: str = None) -> str:
        """List events from your Google Calendar with various filtering options
        
        Args:
            max_results: Maximum number of events to return (default: 10, max: 2500)
            time_min: Start time (ISO format, e.g. '2023-12-01T00:00:00Z') - defaults to now if not specified
            time_max: End time (ISO format, e.g. '2023-12-31T23:59:59Z')
            q: Free text search terms (searches summary, description, location, attendees, etc.)
            order_by: How to order results - 'startTime' (default) or 'updated'
            single_events: Whether to expand recurring events (default: True)
            time_zone: Time zone used in the response (default is calendar's time zone)
            event_types: List of event types to include (e.g. ["default", "outOfOffice"])
            page_token: Token for retrieving a specific page of results
            
        Returns:
            A formatted list of events or an error message
        """
        try:
            url = f"{self.base_api_url}/events"
            
            # Build query parameters
            params = {
                "maxResults": max_results,
                "singleEvents": str(single_events).lower(),
                "orderBy": order_by
            }
            
            # Set time boundaries if provided, otherwise default to now for time_min
            if time_min:
                params["timeMin"] = time_min
            else:
                # Default to current time if not specified
                now = datetime.now().isoformat() + "Z"  # 'Z' indicates UTC time
                params["timeMin"] = now
                
            if time_max:
                params["timeMax"] = time_max
                
            # Add optional filters if provided
            if q:
                params["q"] = q
                
            if time_zone:
                params["timeZone"] = time_zone
                
            if page_token:
                params["pageToken"] = page_token
                
            # Add event types if specified
            if event_types and isinstance(event_types, list):
                params["eventTypes"] = ",".join(event_types)
            
            logger.info(f"Retrieving calendar events with params: {params}")
            
            response = self._get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                events = data.get("items", [])
                
                if not events:
                    return "No events found matching your criteria."
                
                # Extract calendar information
                calendar_summary = data.get("summary", "Your Calendar")
                time_zone_info = data.get("timeZone", "Unknown")
                
                result = f"Events from {calendar_summary} (Time Zone: {time_zone_info}):\n\n"
                
                # Process and format each event
                for i, event in enumerate(events, 1):
                    # Get basic event details
                    event_id = event.get("id", "No ID")
                    summary = event.get("summary", "Untitled event")
                    
                    # Get event times and format them
                    start = event.get("start", {})
                    end = event.get("end", {})
                    
                    start_time = start.get("dateTime", start.get("date", "Unknown"))
                    end_time = end.get("dateTime", end.get("date", "Unknown"))
                    
                    # Format datetime if it's a datetime (not all-day)
                    is_all_day = "date" in start and "dateTime" not in start
                    
                    if not is_all_day and "T" in start_time:
                        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                        start_formatted = start_dt.strftime("%Y-%m-%d %I:%M %p")
                    else:
                        # It's an all-day event
                        start_formatted = start_time + " (All day)"
                    
                    # Get location if available
                    location = event.get("location", "No location specified")
                    
                    # Check if it's a recurring event
                    is_recurring = "recurrence" in event
                    recurring_info = " (Recurring)" if is_recurring else ""
                    
                    # Format the event information
                    result += f"{i}. {summary}{recurring_info}\n"
                    result += f"   ID: {event_id}\n"
                    result += f"   When: {start_formatted}\n"
                    result += f"   Where: {location}\n"
                    
                    # Add a separator between events
                    if i < len(events):
                        result += "\n"
                
                # Add pagination info if available
                if "nextPageToken" in data:
                    next_token = data.get("nextPageToken")
                    result += f"\nMore events available. Use page_token='{next_token}' to see more."
                
                return result
            else:
                logger.error(f"Google Calendar API Error: {response.status_code} - {response.text}")
                return f"Error retrieving events: {response.status_code} - {response.text}"
        except NotAuthorizedError as e:
            logger.warning(f"Google Calendar authorization required: {e.message}")
            return e.message
        except Exception as e:
            logger.exception(f"Error retrieving events: {type(e).__name__} - {str(e)}")
            return f"Error retrieving events: {type(e).__name__} - {str(e)}"         

    def list_tools(self):
        return [self.get_event,self.get_today_events,self.list_events]        