from agentr.application import APIApplication
from agentr.integration import Integration

class RedditApp(APIApplication):
    def __init__(self, integration: Integration) -> None:
        super().__init__(name="reddit", integration=integration)

    def _get_headers(self):
        credentials = self.integration.get_credentials()
        if "headers" in credentials:
            return credentials["headers"]
        return {
            "Authorization": f"Bearer {credentials['access_token']}",
        }

    def get_subreddit_posts(self, subreddit: str) -> str:
        """Get the latest posts from a subreddit
        
        Args:
            subreddit: The subreddit to get posts from
            
        Returns:
            A list of posts from the subreddit
        """
        

    def list_tools(self):
        return []
    
