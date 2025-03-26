from agentr.integration import Integration
from agentr.application import APIApplication
from loguru import logger
from agentr.exceptions import NotAuthorizedError

class GithubApp(APIApplication):
    def __init__(self, integration: Integration) -> None:
        super().__init__(name="github", integration=integration)

    def _get_headers(self):
        if not self.integration:
            raise ValueError("Integration not configured")
        credentials = self.integration.get_credentials()
        if not credentials:
            logger.warning("No credentials found")
            action = self.integration.authorize()
            raise NotAuthorizedError(action)
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
        except NotAuthorizedError as e:
            return e.message
        except Exception as e:
            logger.error(e)
            raise e
       

    def list_commits(self, repo_full_name: str) -> str:
        """List recent commits for a GitHub repository
        
        Args:
            repo_full_name: The full name of the repository (e.g. 'owner/repo')
            
        Returns:
            A formatted list of recent commits
        """
        try:
            # Clean the repo_full_name by removing any whitespace or newlines
            repo_full_name = repo_full_name.strip()
            
            url = f"https://api.github.com/repos/{repo_full_name}/commits"
            response = self._get(url)
            
            if response.status_code == 200:
                commits = response.json()
                if not commits:
                    return f"No commits found for repository {repo_full_name}"
                
                result = f"Recent commits for {repo_full_name}:\n\n"
                for commit in commits[:12]:  # Limit to 12 commits 
                    sha = commit.get("sha", "")[:7]
                    message = commit.get("commit", {}).get("message", "").split('\n')[0]
                    author = commit.get("commit", {}).get("author", {}).get("name", "Unknown")
                    
                    result += f"- {sha}: {message} (by {author})\n"
                
                return result
            elif response.status_code == 404:
                return f"Repository {repo_full_name} not found"
            else:
                return f"Error retrieving commits: {response.status_code} - {response.text}"
        except Exception as e:
            return f"Error retrieving commits: {str(e)}"

    def list_branches(self, repo_full_name: str) -> str:
        """List branches for a GitHub repository
        
        Args:
            repo_full_name: The full name of the repository (e.g. 'owner/repo')
            
        Returns:
            A formatted list of branches
        """
        try:
            repo_full_name = repo_full_name.strip()
            
            url = f"https://api.github.com/repos/{repo_full_name}/branches"
            response = self._get(url)
            
            if response.status_code == 200:
                branches = response.json()
                if not branches:
                    return f"No branches found for repository {repo_full_name}"
                
                result = f"Branches for {repo_full_name}:\n\n"
                for branch in branches:
                    branch_name = branch.get("name", "Unknown")
                    result += f"- {branch_name}\n"
                
                return result
            elif response.status_code == 404:
                return f"Repository {repo_full_name} not found"
            else:
                return f"Error retrieving branches: {response.status_code} - {response.text}"
        except Exception as e:
            return f"Error retrieving branches: {str(e)}"

    def list_tools(self):
        return [self.star_repository, self.list_commits, self.list_branches]