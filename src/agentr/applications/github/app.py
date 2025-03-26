from agentr.integration import Integration
from agentr.application import APIApplication
from loguru import logger
from agentr.exceptions import NotAuthorizedError

class GithubApp(APIApplication):
    def __init__(self, integration: Integration) -> None:
        super().__init__(name="github", integration=integration)
        self.base_api_url = "https://api.github.com/repos"

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
            repo_full_name = repo_full_name.strip()
            url = f"{self.base_api_url}/{repo_full_name}/commits"
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
                logger.error(response.text)
                return f"Error retrieving commits: {response.status_code} - {response.text}"
        except NotAuthorizedError as e:
            return e.message
        except Exception as e:
            logger.error(e)
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
            url = f"{self.base_api_url}/{repo_full_name}/branches"
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
                logger.error(response.text)
                return f"Error retrieving branches: {response.status_code} - {response.text}"
        except NotAuthorizedError as e:
            return e.message
        except Exception as e:
            logger.error(e)
            return f"Error retrieving branches: {str(e)}"
    
    def list_pull_requests(self, repo_full_name: str, state: str = "open") -> str:
        """List pull requests for a GitHub repository
        
        Args:
            repo_full_name: The full name of the repository (e.g. 'owner/repo')
            state: The state of the pull requests to filter by (open, closed, or all)
            
        Returns:
            A formatted list of pull requests
        """
        try:
            repo_full_name = repo_full_name.strip()
            url = f"{self.base_api_url}/{repo_full_name}/pulls"
            params = {"state": state}
            response = self._get(url, params=params)
            
            if response.status_code == 200:
                pull_requests = response.json()
                if not pull_requests:
                    return f"No pull requests found for repository {repo_full_name} with state '{state}'"
                
                result = f"Pull requests for {repo_full_name} (State: {state}):\n\n"
                for pr in pull_requests:
                    pr_title = pr.get("title", "No Title")
                    pr_number = pr.get("number", "Unknown")
                    pr_state = pr.get("state", "Unknown")
                    pr_user = pr.get("user", {}).get("login", "Unknown")
                    
                    result += f"- PR #{pr_number}: {pr_title} (by {pr_user}, Status: {pr_state})\n"
                
                return result
            elif response.status_code == 404:
                return f"Repository {repo_full_name} not found"
            else:
                logger.error(response.text)
                return f"Error retrieving pull requests: {response.status_code} - {response.text}"
        except NotAuthorizedError as e:
            return e.message
        except Exception as e:
            logger.error(e)
            return f"Error retrieving pull requests: {str(e)}"

    def list_issues(self, repo_full_name: str, per_page: int = 30, page: int = 1) -> str:
        """List issues for a GitHub repository
        
        Args:
            repo_full_name: The full name of the repository (e.g. 'owner/repo')
            per_page: The number of results per page (max 100)
            page: The page number of the results to fetch
            
        Returns:
            A formatted list of issues
        """
        try:
            repo_full_name = repo_full_name.strip()
            url = f"{self.base_api_url}/{repo_full_name}/issues/events"
            params = {
                "per_page": per_page,
                "page": page
            }
            response = self._get(url, params=params)
            
            if response.status_code == 200:
                issues = response.json()
                if not issues:
                    return f"No issues found for repository {repo_full_name}"
                
                result = f"Issues for {repo_full_name} (Page {page}):\n\n"
                for issue in issues:
                    issue_title = issue.get("issue", {}).get("title", "No Title")
                    issue_number = issue.get("issue", {}).get("number", "Unknown")
                    issue_state = issue.get("issue", {}).get("state", "Unknown")
                    issue_user = issue.get("issue", {}).get("user", {}).get("login", "Unknown")
                    
                    result += f"- Issue #{issue_number}: {issue_title} (by {issue_user}, Status: {issue_state})\n"
                
                return result
            elif response.status_code == 404:
                return f"Repository {repo_full_name} not found"
            else:
                logger.error(response.text)
                return f"Error retrieving issues: {response.status_code} - {response.text}"
        except NotAuthorizedError as e:
            return e.message
        except Exception as e:
            logger.error(e)
            return f"Error retrieving issues: {str(e)}"

    def get_pull_request(self, repo_full_name: str, pull_number: int) -> str:
        """Get a specific pull request for a GitHub repository
        
        Args:
            repo_full_name: The full name of the repository (e.g. 'owner/repo')
            pull_number: The number of the pull request to retrieve
            
        Returns:
            A formatted string with pull request details
        """
        try:
            repo_full_name = repo_full_name.strip()
            url = f"{self.base_api_url}/{repo_full_name}/pulls/{pull_number}"
            response = self._get(url)
            
            if response.status_code == 200:
                pr = response.json()
                pr_title = pr.get("title", "No Title")
                pr_number = pr.get("number", "Unknown")
                pr_state = pr.get("state", "Unknown")
                pr_user = pr.get("user", {}).get("login", "Unknown")
                pr_body = pr.get("body", "No description provided.")
                
                result = (
                    f"Pull Request #{pr_number}: {pr_title}\n"
                    f"Created by: {pr_user}\n"
                    f"Status: {pr_state}\n"
                    f"Description: {pr_body}\n"
                )
                
                return result
            elif response.status_code == 404:
                return f"Pull request #{pull_number} not found in repository {repo_full_name}"
            else:
                logger.error(response.text)
                return f"Error retrieving pull request: {response.status_code} - {response.text}"
        except NotAuthorizedError as e:
            return e.message
        except Exception as e:
            logger.error(e)
            return f"Error retrieving pull request: {str(e)}"

    def create_pull_request(self, repo_full_name: str, title: str, head: str, base: str, body: str = "", 
                            maintainer_can_modify: bool = True, draft: bool = False) -> str:
        """Create a new pull request for a GitHub repository
        
        Args:
            repo_full_name: The full name of the repository (e.g. 'owner/repo')
            title: The title of the new pull request
            head: The name of the branch where your changes are implemented
            base: The name of the branch you want the changes pulled into
            body: The contents of the pull request
            maintainer_can_modify: Indicates whether maintainers can modify the pull request
            draft: Indicates whether the pull request is a draft
            
        Returns:
            A confirmation message with the new pull request details
        """
        try:
            repo_full_name = repo_full_name.strip()
            url = f"{self.base_api_url}/{repo_full_name}/pulls"
            
            pull_request_data = {
                "title": title,
                "head": head,
                "base": base,
                "body": body,
                "maintainer_can_modify": maintainer_can_modify,
                "draft": draft
            }
            
            response = self._post(url, pull_request_data)
            
            if response.status_code in [200, 201]:
                pr = response.json()
                pr_number = pr.get("number", "Unknown")
                pr_url = pr.get("html_url", "")
                
                return f"Successfully created pull request #{pr_number}:\n" \
                       f"Title: {title}\n" \
                       f"From: {head} → To: {base}\n" \
                       f"URL: {pr_url}"
            else:
                logger.error(response.text)
                return f"Error creating pull request: {response.status_code} - {response.text}"
        except NotAuthorizedError as e:
            return e.message
        except Exception as e:
            logger.error(e)
            return f"Error creating pull request: {str(e)}"

    def list_tools(self):
        return [self.star_repository, self.list_commits, self.list_branches, 
                self.list_pull_requests, self.list_issues, self.get_pull_request, 
                self.create_pull_request]