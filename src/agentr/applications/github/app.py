from agentr.integration import Integration
from agentr.application import APIApplication
from loguru import logger


class GithubApp(APIApplication):
    def __init__(self, user_id, integration: Integration) -> None:
        super().__init__(name="github", user_id=user_id, integration=integration)

    def _get_headers(self):
        credentials = self.integration.get_credentials()
        if "headers" in credentials:
            return credentials["headers"]
        return {
            "Authorization": f"Bearer {credentials['access_token']}",
            "Accept": "application/vnd.github.v3+json"
        }
    

    def star_repository(self, repo_full_name: str) -> str:
        """Star a GitHub repository
        
            Args:
                repo_full_name: The full name of the repository (e.g. 'owner/repo')
                
            Returns:
            
                A confirmation message
        """
        if not self.validate():
            logger.warning("Connection not configured correctly")
            return self.authorize()
        try:
            url = f"https://api.github.com/user/starred/{repo_full_name}"
            response = self._put(url, data={})
            
            if response.status_code == 204:
                return f"Successfully starred repository {repo_full_name}"
            elif response.status_code == 404:
                return f"Repository {repo_full_name} not found"
            else:
                logger.error(response.text)
                return f"Error starring repository: {response.text}"
        except Exception as e:
            logger.error(e)
            return f"Error starring repository: {e}"

    
    def list_tools(self):
        return [self.star_repository]