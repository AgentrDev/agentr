from agentr.applications.zenquotes.app import ZenQuoteApp
from agentr.applications.tavily.app import TavilyApp
from agentr.applications.github.app import GithubApp
from agentr.applications.google_calendar.app import GoogleCalendarApp
from agentr.applications.google_mail.app import GmailApp
from agentr.applications.resend.app import ResendApp
from agentr.applications.reddit.app import RedditApp

def app_from_name(name: str):
    name = name.lower().strip()
    name = name.replace(" ", "-")
    if name == "zenquotes":
        return ZenQuoteApp
    elif name == "tavily":
        return TavilyApp
    elif name == "github":
        return GithubApp
    elif name == "google-calendar":
        return GoogleCalendarApp
    elif name == "google-mail":
        return GmailApp
    elif name == "resend":
        return ResendApp
    elif name == "reddit":
        return RedditApp
    else:
        raise ValueError(f"App {name} not found")
