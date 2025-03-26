from agentr.application import APIApplication
from agentr.integration import Integration
from agentr.exceptions import NotAuthorizedError
from loguru import logger
import httpx 

class RedditApp(APIApplication):
    def __init__(self, integration: Integration) -> None:
        super().__init__(name="reddit", integration=integration)
        self.base_api_url = "https://oauth.reddit.com" 

    def _get_headers(self):
        if not self.integration:
            raise ValueError("Integration not configured for RedditApp")
        credentials = self.integration.get_credentials()
        if not credentials:
            logger.warning("No Reddit credentials found via integration.")
            action = self.integration.authorize()
            raise NotAuthorizedError(action) 
            
        if "access_token" not in credentials:
             logger.error("Reddit credentials found but missing 'access_token'.")
             raise ValueError("Invalid Reddit credentials format.")

        return {
            "Authorization": f"Bearer {credentials['access_token']}",
            "User-Agent": "agentr-reddit-app/0.1 by AgentR"
        }

    def get_subreddit_posts(self, subreddit: str, limit: int = 5, timeframe: str = "day") -> str:
        """Get the top posts from a specified subreddit over a given timeframe.
        
        Args:
            subreddit: The name of the subreddit (e.g., 'python', 'worldnews') without the 'r/'.
            limit: The maximum number of posts to return (default: 5, max: 100).
            timeframe: The time period for top posts. Valid options: 'hour', 'day', 'week', 'month', 'year', 'all' (default: 'day').
            
        Returns:
            A formatted string listing the top posts or an error message.
        """
        valid_timeframes = ['hour', 'day', 'week', 'month', 'year', 'all']
        if timeframe not in valid_timeframes:
            return f"Error: Invalid timeframe '{timeframe}'. Please use one of: {', '.join(valid_timeframes)}"
        
        if not 1 <= limit <= 100:
             return f"Error: Invalid limit '{limit}'. Please use a value between 1 and 100."

        try:
            url = f"{self.base_api_url}/r/{subreddit}/top"
            params = {
                "limit": limit,
                "t": timeframe
            }
            
            logger.info(f"Requesting top {limit} posts from r/{subreddit} for timeframe '{timeframe}'")
            response = self._get(url, params=params)
            
            # _get already raises for status >= 400, but we can add specific checks if needed
            # response.raise_for_status() # This is already done in _get

            data = response.json()
            
            if "error" in data:
                 logger.error(f"Reddit API error: {data['error']} - {data.get('message', '')}")
                 return f"Error from Reddit API: {data['error']} - {data.get('message', '')}"

            posts = data.get("data", {}).get("children", [])
            
            if not posts:
                return f"No top posts found in r/{subreddit} for the timeframe '{timeframe}'."

            result_lines = [f"Top {len(posts)} posts from r/{subreddit} (timeframe: {timeframe}):\n"]
            for i, post_container in enumerate(posts):
                post = post_container.get("data", {})
                title = post.get('title', 'No Title')
                score = post.get('score', 0)
                author = post.get('author', 'Unknown Author')
                # Construct full URL from permalink
                permalink = post.get('permalink', '')
                full_url = f"https://www.reddit.com{permalink}" if permalink else "No Link"
                
                result_lines.append(f"{i+1}. \"{title}\" by u/{author} (Score: {score})")
                result_lines.append(f"   Link: {full_url}")

            return "\n".join(result_lines)

        except NotAuthorizedError as e:
            # Intercept the NotAuthorizedError and return its message directly
            logger.warning(f"Reddit authorization needed: {e.message}")
            return e.message 
        except httpx.HTTPStatusError as e:
            # Handle specific HTTP errors, like 404 for non-existent subreddit
            if e.response.status_code == 403:
                 logger.error(f"Access denied to r/{subreddit}. It might be private or quarantined.")
                 return f"Error: Access denied to r/{subreddit}. It might be private, quarantined, or require specific permissions."
            elif e.response.status_code == 404:
                 logger.error(f"Subreddit r/{subreddit} not found.")
                 return f"Error: Subreddit r/{subreddit} not found."
            else:
                 logger.error(f"HTTP error fetching posts from r/{subreddit}: {e.response.status_code} - {e.response.text}")
                 return f"Error fetching posts: Received status code {e.response.status_code}."
        except Exception as e:
            logger.exception(f"An unexpected error occurred while fetching posts from r/{subreddit}: {e}")
            return f"An unexpected error occurred while trying to get posts from r/{subreddit}."

    def search_subreddits(self, query: str, limit: int = 5, sort: str = "relevance") -> str:
        """Search for subreddits matching a query string.
        
        Args:
            query: The text to search for in subreddit names and descriptions.
            limit: The maximum number of subreddits to return (default: 5, max: 100).
            sort: The order of results. Valid options: 'relevance', 'activity' (default: 'relevance').
            
        Returns:
            A formatted string listing the found subreddits and their descriptions, or an error message.
        """
        valid_sorts = ['relevance', 'activity']
        if sort not in valid_sorts:
            return f"Error: Invalid sort option '{sort}'. Please use one of: {', '.join(valid_sorts)}"
        
        if not 1 <= limit <= 100:
             return f"Error: Invalid limit '{limit}'. Please use a value between 1 and 100."

        try:
            url = f"{self.base_api_url}/subreddits/search"
            params = {
                "q": query,
                "limit": limit,
                "sort": sort,
                # Optionally include NSFW results? Defaulting to false for safety.
                # "include_over_18": "false" 
            }
            
            logger.info(f"Searching for subreddits matching '{query}' (limit: {limit}, sort: {sort})")
            response = self._get(url, params=params)
            
            data = response.json()

            if "error" in data:
                 logger.error(f"Reddit API error during subreddit search: {data['error']} - {data.get('message', '')}")
                 return f"Error from Reddit API during search: {data['error']} - {data.get('message', '')}"

            subreddits = data.get("data", {}).get("children", [])
            
            if not subreddits:
                return f"No subreddits found matching the query '{query}'."

            result_lines = [f"Found {len(subreddits)} subreddits matching '{query}' (sorted by {sort}):\n"]
            for i, sub_container in enumerate(subreddits):
                sub_data = sub_container.get("data", {})
                display_name = sub_data.get('display_name', 'N/A') # e.g., 'python'
                title = sub_data.get('title', 'No Title') # Often the same as display_name or slightly longer
                subscribers = sub_data.get('subscribers', 0)
                # Use public_description if available, fallback to title
                description = sub_data.get('public_description', '').strip() or title
                
                # Format subscriber count nicely
                subscriber_str = f"{subscribers:,}" if subscribers else "Unknown"
                
                result_lines.append(f"{i+1}. r/{display_name} ({subscriber_str} subscribers)")
                if description:
                    result_lines.append(f"   Description: {description}")
                
            return "\n".join(result_lines)

        except NotAuthorizedError as e:
            logger.warning(f"Reddit authorization needed for search: {e.message}")
            return e.message 
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error searching subreddits for '{query}': {e.response.status_code} - {e.response.text}")
            # Don't expose raw response text unless debugging
            return f"Error searching subreddits: Received status code {e.response.status_code}."
        except Exception as e:
            logger.exception(f"An unexpected error occurred while searching subreddits for '{query}': {e}")
            return f"An unexpected error occurred while trying to search for subreddits."

    def list_tools(self):
        # Add the new tool to the list
        return [
            self.get_subreddit_posts, 
            self.search_subreddits  # <<< Added this line
        ]