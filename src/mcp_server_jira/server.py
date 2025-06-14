from enum import Enum
import json
import os
from pathlib import Path
from typing import Sequence, Dict, List, Any, Optional, Union

import requests
from jira import JIRA
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource

from pydantic import BaseModel
try:
    from dotenv import load_dotenv
    # Try to load from .env file if it exists
    env_path = Path(__file__).parent.parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
except ImportError:
    # dotenv is optional
    pass


class JiraTools(str, Enum):
    GET_PROJECTS = "get_jira_projects"
    GET_ISSUE = "get_jira_issue" 
    SEARCH_ISSUES = "search_jira_issues"
    CREATE_ISSUE = "create_jira_issue"
    CREATE_ISSUES = "create_jira_issues"
    ADD_COMMENT = "add_jira_comment"
    GET_TRANSITIONS = "get_jira_transitions"
    TRANSITION_ISSUE = "transition_jira_issue"
    CREATE_PROJECT = "create_jira_project"
    GET_PROJECT_ISSUE_TYPES = "get_jira_project_issue_types"


class JiraIssueField(BaseModel):
    name: str
    value: str


class JiraIssueResult(BaseModel):
    key: str
    summary: str
    description: Optional[str] = None
    status: Optional[str] = None
    assignee: Optional[str] = None
    reporter: Optional[str] = None
    created: Optional[str] = None
    updated: Optional[str] = None
    fields: Optional[Dict[str, Any]] = None
    comments: Optional[List[Dict[str, Any]]] = None


class JiraProjectResult(BaseModel):
    key: str
    name: str
    id: str
    lead: Optional[str] = None


class JiraTransitionResult(BaseModel):
    id: str
    name: str


class JiraServer:
    def __init__(self, server_url: str = None, auth_method: str = None, username: str = None, 
                 password: str = None, token: str = None):
        self.server_url = server_url
        self.auth_method = auth_method
        self.username = username
        self.password = password
        self.token = token
        self.client = None

    def connect(self):
        """Connect to Jira server using provided authentication details"""
        if not self.server_url:
            print("Error: Jira server URL not provided")
            return False
        
        error_messages = []
        
        # Try multiple auth methods if possible
        try:
            # First, try the specified auth method
            if self.auth_method == "basic_auth":
                # Basic auth - either username/password or username/token
                if self.username and self.password:
                    try:
                        print(f"Trying basic_auth with username and password")
                        self.client = JIRA(server=self.server_url, basic_auth=(self.username, self.password))
                        print("Connection successful with username/password")
                        return True
                    except Exception as e:
                        error_msg = f"Failed basic_auth with username/password: {type(e).__name__}: {str(e)}"
                        print(error_msg)
                        error_messages.append(error_msg)
                
                if self.username and self.token:
                    try:
                        print(f"Trying basic_auth with username and API token")
                        self.client = JIRA(server=self.server_url, basic_auth=(self.username, self.token))
                        print("Connection successful with username/token")
                        return True
                    except Exception as e:
                        error_msg = f"Failed basic_auth with username/token: {type(e).__name__}: {str(e)}"
                        print(error_msg)
                        error_messages.append(error_msg)
                
                print("Error: Username and password/token required for basic auth")
                error_messages.append("Username and password/token required for basic auth")
            
            elif self.auth_method == "token_auth":
                # Token auth - just need the token
                if self.token:
                    try:
                        print(f"Trying token_auth with token")
                        self.client = JIRA(server=self.server_url, token_auth=self.token)
                        print("Connection successful with token_auth")
                        return True
                    except Exception as e:
                        error_msg = f"Failed token_auth: {type(e).__name__}: {str(e)}"
                        print(error_msg)
                        error_messages.append(error_msg)
                else:
                    print("Error: Token required for token auth")
                    error_messages.append("Token required for token auth")
            
            # If we're here and have a token, try using it with basic_auth for Jira Cloud
            # (even if auth_method wasn't basic_auth)
            if self.token and self.username and not self.client:
                try:
                    print(f"Trying fallback to basic_auth with username and token")
                    self.client = JIRA(server=self.server_url, basic_auth=(self.username, self.token))
                    print("Connection successful with fallback basic_auth")
                    return True
                except Exception as e:
                    error_msg = f"Failed fallback to basic_auth: {type(e).__name__}: {str(e)}"
                    print(error_msg)
                    error_messages.append(error_msg)
            
            # If we're here and have a token, try using token_auth as a fallback
            # (even if auth_method wasn't token_auth)
            if self.token and not self.client:
                try:
                    print(f"Trying fallback to token_auth")
                    self.client = JIRA(server=self.server_url, token_auth=self.token)
                    print("Connection successful with fallback token_auth")
                    return True
                except Exception as e:
                    error_msg = f"Failed fallback to token_auth: {type(e).__name__}: {str(e)}"
                    print(error_msg)
                    error_messages.append(error_msg)
            
            # Last resort: try anonymous access
            try:
                print(f"Trying anonymous access as last resort")
                self.client = JIRA(server=self.server_url)
                print("Connection successful with anonymous access")
                return True
            except Exception as e:
                error_msg = f"Failed anonymous access: {type(e).__name__}: {str(e)}"
                print(error_msg)
                error_messages.append(error_msg)
            
            # If we got here, all connection attempts failed
            print(f"All connection attempts failed: {', '.join(error_messages)}")
            return False
            
        except Exception as e:
            error_msg = f"Unexpected error in connect(): {type(e).__name__}: {str(e)}"
            print(error_msg)
            error_messages.append(error_msg)
            return False
    
    def _make_v3_api_request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make an authenticated request to Jira's v3 REST API
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path (e.g., '/project')
            data: Optional request body data
            
        Returns:
            Response JSON data
            
        Raises:
            ValueError: If the request fails
        """
        if not self.server_url:
            raise ValueError("Server URL not configured")
            
        # Construct the full URL
        url = f"{self.server_url.rstrip('/')}/rest/api/3{endpoint}"
        
        # Prepare headers
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        # Set up authentication
        auth = None
        if self.username and (self.password or self.token):
            # Use basic auth (works for both username/password and username/token)
            auth = (self.username, self.password or self.token)
        elif self.token:
            # Use bearer token auth
            headers['Authorization'] = f'Bearer {self.token}'
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                auth=auth,
                json=data,
                timeout=30
            )
            
            # Check for HTTP errors
            if response.status_code >= 400:
                error_details = ""
                try:
                    error_json = response.json()
                    if 'errorMessages' in error_json:
                        error_details = "; ".join(error_json['errorMessages'])
                    elif 'message' in error_json:
                        error_details = error_json['message']
                except:
                    error_details = response.text[:200] if response.text else "No error details"
                
                raise ValueError(f"HTTP {response.status_code}: {error_details}")
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Request failed: {str(e)}")
        except ValueError:
            # Re-raise ValueError exceptions (including HTTP errors)
            raise
        except Exception as e:
            raise ValueError(f"Unexpected error in API request: {str(e)}")

    def get_jira_projects(self) -> List[JiraProjectResult]:
        """Get all accessible Jira projects
        
        Returns:
            List of JiraProjectResult objects representing all accessible projects
            
        Example:
            get_jira_projects()  # Returns list of all projects you have access to
        """
        if not self.client:
            if not self.connect():
                # Connection failed - provide clear error message
                raise ValueError(f"Failed to connect to Jira server at {self.server_url}. Check your authentication credentials.")
            
        try:
            # Get projects from Jira API - projects() takes no parameters according to docs
            projects = self.client.projects()
            
            # Process the projects into our result model
            result = []
            for project in projects:
                # Extract the project data
                try:
                    project_key = project.key
                    project_name = project.name
                    project_id = project.id
                    
                    # Handle lead carefully
                    lead_name = None
                    if hasattr(project, 'lead') and project.lead:
                        lead_name = getattr(project.lead, 'displayName', None)
                        
                    result.append(JiraProjectResult(
                        key=project_key,
                        name=project_name,
                        id=str(project_id),  # Ensure id is a string
                        lead=lead_name
                    ))
                except AttributeError:
                    # Skip projects that don't have required attributes
                    continue
                    
            return result
        except Exception as e:
            # Log and raise the exception with better details
            error_type = type(e).__name__
            error_msg = str(e)
            print(f"Error getting projects: {error_type}: {error_msg}")
            raise ValueError(f"Failed to get projects: {error_type}: {error_msg}")

    def get_jira_issue(self, issue_key: str) -> JiraIssueResult:
        """Get details for a specific issue by key"""
        if not self.client:
            if not self.connect():
                # Connection failed - provide clear error message
                raise ValueError(f"Failed to connect to Jira server at {self.server_url}. Check your authentication credentials.")
            
        try:
            issue = self.client.issue(issue_key)
            
            # Extract comments if available
            comments = []
            if hasattr(issue.fields, 'comment') and hasattr(issue.fields.comment, 'comments'):
                for comment in issue.fields.comment.comments:
                    comments.append({
                        "author": getattr(comment.author, 'displayName', str(comment.author)) if hasattr(comment, 'author') else "Unknown",
                        "body": comment.body,
                        "created": comment.created
                    })
            
            # Create a fields dictionary with custom fields
            fields = {}
            for field_name in dir(issue.fields):
                if not field_name.startswith('_') and field_name not in ['comment', 'attachment', 'summary', 'description', 'status', 'assignee', 'reporter', 'created', 'updated']:
                    value = getattr(issue.fields, field_name)
                    if value is not None:
                        # Handle special field types
                        if hasattr(value, 'name'):
                            fields[field_name] = value.name
                        elif hasattr(value, 'value'):
                            fields[field_name] = value.value
                        elif isinstance(value, list):
                            if len(value) > 0:
                                if hasattr(value[0], 'name'):
                                    fields[field_name] = [item.name for item in value]
                                else:
                                    fields[field_name] = value
                        else:
                            fields[field_name] = str(value)
            
            return JiraIssueResult(
                key=issue.key,
                summary=issue.fields.summary,
                description=issue.fields.description,
                status=issue.fields.status.name if hasattr(issue.fields, 'status') else None,
                assignee=issue.fields.assignee.displayName if hasattr(issue.fields, 'assignee') and issue.fields.assignee else None,
                reporter=issue.fields.reporter.displayName if hasattr(issue.fields, 'reporter') and issue.fields.reporter else None,
                created=issue.fields.created if hasattr(issue.fields, 'created') else None,
                updated=issue.fields.updated if hasattr(issue.fields, 'updated') else None,
                fields=fields,
                comments=comments
            )
        except Exception as e:
            print(f"Failed to get issue {issue_key}: {type(e).__name__}: {str(e)}")
            raise ValueError(f"Failed to get issue {issue_key}: {type(e).__name__}: {str(e)}")

    def search_jira_issues(self, jql: str, max_results: int = 10) -> List[JiraIssueResult]:
        """Search for issues using JQL"""
        if not self.client:
            if not self.connect():
                # Connection failed - provide clear error message
                raise ValueError(f"Failed to connect to Jira server at {self.server_url}. Check your authentication credentials.")
            
        try:
            issues = self.client.search_issues(jql, maxResults=max_results)
            
            return [
                JiraIssueResult(
                    key=issue.key,
                    summary=issue.fields.summary,
                    description=issue.fields.description,
                    status=issue.fields.status.name if hasattr(issue.fields, 'status') else None,
                    assignee=issue.fields.assignee.displayName if hasattr(issue.fields, 'assignee') and issue.fields.assignee else None,
                    reporter=issue.fields.reporter.displayName if hasattr(issue.fields, 'reporter') and issue.fields.reporter else None,
                    created=issue.fields.created if hasattr(issue.fields, 'created') else None,
                    updated=issue.fields.updated if hasattr(issue.fields, 'updated') else None
                )
                for issue in issues
            ]
        except Exception as e:
            print(f"Failed to search issues: {type(e).__name__}: {str(e)}")
            raise ValueError(f"Failed to search issues: {type(e).__name__}: {str(e)}")

    def create_jira_issue(self, project: str, summary: str, description: str, 
                     issue_type: str, fields: Optional[Dict[str, Any]] = None) -> JiraIssueResult:
        """Create a new Jira issue
        
        Args:
            project: Project key (e.g., 'PROJ')
            summary: Issue summary/title
            description: Issue description
            issue_type: Issue type - common values include 'Bug', 'Task', 'Story', 'Epic', 'New Feature', 'Improvement'
                       Note: Available issue types vary by Jira instance and project
            fields: Optional additional fields dictionary
            
        Returns:
            JiraIssueResult object with the created issue details
            
        Example:
            # Create a bug
            create_jira_issue(
                project='PROJ',
                summary='Login button not working',
                description='The login button on the homepage is not responding to clicks',
                issue_type='Bug'
            )
            
            # Create a task with custom fields
            create_jira_issue(
                project='PROJ',
                summary='Update documentation',
                description='Update API documentation with new endpoints',
                issue_type='Task',
                fields={
                    'assignee': 'jsmith',
                    'labels': ['documentation', 'api'],
                    'priority': {'name': 'High'}
                }
            )
        """
        if not self.client:
            if not self.connect():
                # Connection failed - provide clear error message
                raise ValueError(f"Failed to connect to Jira server at {self.server_url}. Check your authentication credentials.")
            
        try:
            # Create a properly formatted issue dictionary
            issue_dict = {}
            
            # Process required fields first
            # Project field - required
            if isinstance(project, str):
                issue_dict['project'] = {'key': project}
            else:
                issue_dict['project'] = project
                
            # Summary - required
            issue_dict['summary'] = summary
            
            # Description
            if description:
                issue_dict['description'] = description
            
            # Issue type - required, with validation for common issue types
            # Add for better debugging - print available types
            print(f"Processing issue_type: '{issue_type}' (type: {type(issue_type)})")
            common_types = ['bug', 'task', 'story', 'epic', 'improvement', 'newfeature', 'new feature']
            
            if isinstance(issue_type, str):
                # Check for common issue type variants and fix case-sensitivity issues
                issue_type_lower = issue_type.lower()
                
                if issue_type_lower in common_types:
                    # Convert first letter to uppercase for standard Jira types
                    issue_type_proper = issue_type_lower.capitalize()
                    if issue_type_lower == 'new feature' or issue_type_lower == 'newfeature':
                        issue_type_proper = 'New Feature'
                        
                    print(f"Note: Converting issue type from '{issue_type}' to '{issue_type_proper}'")
                    issue_dict['issuetype'] = {'name': issue_type_proper}
                else:
                    # Use the type as provided - some Jira instances have custom types
                    issue_dict['issuetype'] = {'name': issue_type}
            else:
                issue_dict['issuetype'] = issue_type
            
            # Add any additional fields with proper type handling
            if fields:
                for key, value in fields.items():
                    # Skip fields we've already processed
                    if key in ['project', 'summary', 'description', 'issuetype', 'issue_type']:
                        continue
                        
                    # Handle special fields that require specific formats
                    if key == 'assignees' or key == 'assignee':
                        # Convert string to array for assignees or proper format for assignee
                        if isinstance(value, str):
                            if key == 'assignees':
                                issue_dict[key] = [value] if value else []
                            else:  # assignee
                                issue_dict[key] = {'name': value} if value else None
                        elif isinstance(value, list) and key == 'assignee' and value:
                            # If assignee is a list but should be a dict with name
                            issue_dict[key] = {'name': value[0]}
                        else:
                            issue_dict[key] = value
                    elif key == 'labels':
                        # Convert string to array for labels
                        if isinstance(value, str):
                            issue_dict[key] = [value] if value else []
                        else:
                            issue_dict[key] = value
                    elif key == 'milestone':
                        # Convert string to number for milestone
                        if isinstance(value, str) and value.isdigit():
                            issue_dict[key] = int(value)
                        else:
                            issue_dict[key] = value
                    else:
                        issue_dict[key] = value
            
            # Print the finalized issue dict for debugging
            print(f"Sending issue dictionary to Jira: {json.dumps(issue_dict, indent=2)}")
            
            # Use the client's create_issue method with the properly formatted fields dict
            try:
                new_issue = self.client.create_issue(fields=issue_dict)
            except Exception as e:
                error_type = type(e).__name__
                error_message = str(e)
                
                # Check if the error might be related to the issue type
                if 'issuetype' in error_message.lower() or 'issue type' in error_message.lower():
                    print(f"Issue type error detected! Your Jira instance may require specific issue types.")
                    attempted_type = issue_dict.get('issuetype', {}).get('name', 'Unknown')
                    print(f"Attempted issue type: '{attempted_type}'")
                    print(f"Full error: {error_type}: {error_message}")
                    
                    # Try to fetch available issue types for this project
                    try:
                        project_key = issue_dict.get('project', {}).get('key')
                        if project_key:
                            print(f"Fetching available issue types for project {project_key}...")
                            issue_types = self.get_jira_project_issue_types(project_key)
                            type_names = [t.get('name') for t in issue_types]
                            print(f"Available issue types: {', '.join(type_names)}")
                            
                            # Try to find the closest match
                            closest = None
                            attempted_lower = attempted_type.lower()
                            for t in type_names:
                                if attempted_lower in t.lower() or t.lower() in attempted_lower:
                                    closest = t
                                    break
                            
                            if closest:
                                print(f"The closest match to '{attempted_type}' is '{closest}'")
                                print(f"Try using '{closest}' instead")
                    except Exception as fetch_error:
                        print(f"Could not fetch issue types: {str(fetch_error)}")
                
                # Re-raise the exception with more details
                if 'issuetype' in error_message.lower():
                    raise ValueError(f"Invalid issue type '{issue_dict.get('issuetype', {}).get('name', 'Unknown')}'. " + 
                                     "Use get_jira_project_issue_types(project_key) to get valid types.")
                raise
            
            return JiraIssueResult(
                key=new_issue.key,
                summary=new_issue.fields.summary,
                description=new_issue.fields.description,
                status=new_issue.fields.status.name if hasattr(new_issue.fields, 'status') else None
            )
        except Exception as e:
            print(f"Failed to create issue: {type(e).__name__}: {str(e)}")
            raise ValueError(f"Failed to create issue: {type(e).__name__}: {str(e)}")
            
    def create_jira_issues(self, field_list: List[Dict[str, Any]], prefetch: bool = True) -> List[Dict[str, Any]]:
        """Bulk create new Jira issues and return an issue Resource for each successfully created issue.
        
        Parameters:
            field_list (List[Dict[str, Any]]): a list of dicts each containing field names and the values to use. 
                                             Each dict is an individual issue to create.
            prefetch (bool): True reloads the created issue Resource so all of its data is present in the value returned (Default: True)
            
        Returns:
            List[Dict[str, Any]]: List of created issues with their details
            
        Issue Types:
            Common issue types include: 'Bug', 'Task', 'Story', 'Epic', 'New Feature', 'Improvement'
            Note: Available issue types vary by Jira instance and project
            
        Example:
            # Create multiple issues in bulk
            create_jira_issues([
                {
                    'project': 'PROJ',
                    'summary': 'Implement user authentication',
                    'description': 'Add login and registration functionality',
                    'issue_type': 'Story'  # Note: case-sensitive, match to your Jira instance types
                },
                {
                    'project': 'PROJ',
                    'summary': 'Fix navigation bar display on mobile',
                    'description': 'Navigation bar is not displaying correctly on mobile devices',
                    'issue_type': 'Bug',
                    'priority': {'name': 'High'},
                    'labels': ['mobile', 'ui']
                }
            ])
        """
        if not self.client:
            if not self.connect():
                # Connection failed - provide clear error message
                raise ValueError(f"Failed to connect to Jira server at {self.server_url}. Check your authentication credentials.")
            
        try:
            # Process each field dict to ensure proper formatting
            processed_field_list = []
            for fields in field_list:
                # Create a properly formatted issue dictionary
                issue_dict = {}
                
                # Process required fields first to ensure they exist
                # Project field - required
                if 'project' not in fields:
                    raise ValueError("Each issue must have a 'project' field")
                project_value = fields['project']
                if isinstance(project_value, str):
                    issue_dict['project'] = {'key': project_value}
                else:
                    issue_dict['project'] = project_value
                
                # Summary field - required
                if 'summary' not in fields:
                    raise ValueError("Each issue must have a 'summary' field")
                issue_dict['summary'] = fields['summary']
                
                # Description field
                if 'description' in fields:
                    issue_dict['description'] = fields['description']
                
                # Issue type field - required, handle both 'issuetype' and 'issue_type'
                issue_type = None
                if 'issuetype' in fields:
                    issue_type = fields['issuetype']
                elif 'issue_type' in fields:
                    issue_type = fields['issue_type']
                else:
                    raise ValueError("Each issue must have an 'issuetype' or 'issue_type' field")
                
                # Check for common issue type variants and fix case-sensitivity issues
                # Add debug information
                print(f"Processing bulk issue_type: '{issue_type}' (type: {type(issue_type)})")
                common_types = ['bug', 'task', 'story', 'epic', 'improvement', 'newfeature', 'new feature']
                
                if isinstance(issue_type, str):
                    issue_type_lower = issue_type.lower()
                    
                    if issue_type_lower in common_types:
                        # Convert first letter to uppercase for standard Jira types
                        issue_type_proper = issue_type_lower.capitalize()
                        if issue_type_lower == 'new feature' or issue_type_lower == 'newfeature':
                            issue_type_proper = 'New Feature'
                            
                        print(f"Note: Converting issue type from '{issue_type}' to '{issue_type_proper}'")
                        issue_dict['issuetype'] = {'name': issue_type_proper}
                    else:
                        # Use the type as provided - some Jira instances have custom types
                        issue_dict['issuetype'] = {'name': issue_type}
                else:
                    issue_dict['issuetype'] = issue_type
                
                # Process other fields
                for key, value in fields.items():
                    if key in ['project', 'summary', 'description', 'issuetype', 'issue_type']:
                        # Skip fields we've already processed
                        continue
                        
                    # Handle special fields that require specific formats
                    if key == 'assignees' or key == 'assignee':
                        # Convert string to array for assignees or proper format for assignee
                        if isinstance(value, str):
                            if key == 'assignees':
                                issue_dict[key] = [value] if value else []
                            else:  # assignee
                                issue_dict[key] = {'name': value} if value else None
                        elif isinstance(value, list) and key == 'assignee' and value:
                            # If assignee is a list but should be a dict with name
                            issue_dict[key] = {'name': value[0]}
                        else:
                            issue_dict[key] = value
                    elif key == 'labels':
                        # Convert string to array for labels
                        if isinstance(value, str):
                            issue_dict[key] = [value] if value else []
                        else:
                            issue_dict[key] = value
                    elif key == 'milestone':
                        # Convert string to number for milestone
                        if isinstance(value, str) and value.isdigit():
                            issue_dict[key] = int(value)
                        else:
                            issue_dict[key] = value
                    else:
                        issue_dict[key] = value
                
                # Add to the field list
                processed_field_list.append({"fields": issue_dict})
            
            # Debug the issue
            print(f"Processed field list: {json.dumps(processed_field_list, indent=2)}")
            
            # Use the client's create_issues method with the properly formatted fields
            # The Jira API expects an array of objects, each with a 'fields' property
            print(f"Sending field list to Jira: {json.dumps(processed_field_list, indent=2)}")
            
            try:
                results = self.client.create_issues(processed_field_list, prefetch=prefetch)
            except Exception as e:
                # If there's an error, log the field list and re-raise
                error_type = type(e).__name__
                error_msg = str(e)
                print(f"Error in create_issues: {error_type}: {error_msg}")
                print(f"With field list: {json.dumps(processed_field_list, indent=2)}")
                
                # Check if the error might be related to the issue type
                if 'issuetype' in error_msg.lower() or 'issue type' in error_msg.lower():
                    print(f"Issue type error detected! Your Jira instance may require specific issue types.")
                    
                    # Try to extract all issue types we attempted to use
                    issue_types = []
                    project_key = None
                    for issue in processed_field_list:
                        fields = issue.get('fields', {})
                        if 'issuetype' in fields:
                            issue_type = fields['issuetype'].get('name', 'Unknown') if isinstance(fields['issuetype'], dict) else str(fields['issuetype'])
                            issue_types.append(issue_type)
                        
                        # Get the project key from the first issue
                        if not project_key and 'project' in fields:
                            if isinstance(fields['project'], dict):
                                project_key = fields['project'].get('key')
                    
                    print(f"Attempted issue types: {', '.join(issue_types)}")
                    print(f"Full error: {error_type}: {error_msg}")
                    
                    # Try to fetch available issue types for this project
                    if project_key:
                        try:
                            print(f"Fetching available issue types for project {project_key}...")
                            available_types = self.get_jira_project_issue_types(project_key)
                            type_names = [t.get('name') for t in available_types]
                            print(f"Available issue types: {', '.join(type_names)}")
                            
                            # Try to find closest matches
                            for attempted in issue_types:
                                attempted_lower = attempted.lower()
                                closest = None
                                for t in type_names:
                                    if attempted_lower in t.lower() or t.lower() in attempted_lower:
                                        closest = t
                                        break
                                
                                if closest:
                                    print(f"The closest match to '{attempted}' is '{closest}'")
                        except Exception as fetch_error:
                            print(f"Could not fetch issue types: {str(fetch_error)}")
                            
                    # Raise a more informative error
                    raise ValueError(f"Invalid issue type(s): {', '.join(issue_types)}. " + 
                                    "Use get_jira_project_issue_types(project_key) to get valid types.")
                
                # Try to handle common errors
                if 'project' in str(e).lower():
                    # Try alternative format
                    alternative_field_list = []
                    for issue in processed_field_list:
                        # Ensure each issue has the project field
                        fields = issue.get('fields', {})
                        if 'project' not in fields:
                            raise ValueError(f"Issue missing 'project' field: {json.dumps(issue)}")
                        alternative_field_list.append(issue)
                    
                    print(f"Trying alternative format: {json.dumps(alternative_field_list, indent=2)}")
                    results = self.client.create_issues(alternative_field_list, prefetch=prefetch)
                else:
                    raise
            
            # Process the results
            processed_results = []
            for result in results:
                # Determine whether the issue was created successfully
                if 'issue' in result:
                    issue = result['issue']
                    # Extract the issue info
                    processed_results.append({
                        'key': issue.key,
                        'id': issue.id,
                        'self': getattr(issue, 'self', None),
                        'success': True
                    })
                else:
                    # Error case
                    processed_results.append({
                        'error': result.get('error', 'Unknown error'),
                        'success': False
                    })
                    
            return processed_results
            
        except Exception as e:
            print(f"Failed to create issues in bulk: {type(e).__name__}: {str(e)}")
            raise ValueError(f"Failed to create issues in bulk: {type(e).__name__}: {str(e)}")

    def add_jira_comment(self, issue_key: str, comment: str) -> Dict[str, Any]:
        """Add a comment to an issue"""
        if not self.client:
            if not self.connect():
                # Connection failed - provide clear error message
                raise ValueError(f"Failed to connect to Jira server at {self.server_url}. Check your authentication credentials.")
            
        try:
            comment_result = self.client.add_comment(issue_key, comment)
            
            # Return a plain dictionary that doesn't need model_dump
            return {
                "id": comment_result.id,
                "body": comment_result.body,
                "author": getattr(comment_result.author, 'displayName', str(comment_result.author)) if hasattr(comment_result, 'author') else "Unknown",
                "created": str(comment_result.created)  # Convert to string to ensure JSON serializable
            }
        except Exception as e:
            print(f"Failed to add comment to {issue_key}: {type(e).__name__}: {str(e)}")
            raise ValueError(f"Failed to add comment to {issue_key}: {type(e).__name__}: {str(e)}")

    def get_jira_transitions(self, issue_key: str) -> List[JiraTransitionResult]:
        """Get available transitions for an issue"""
        if not self.client:
            if not self.connect():
                # Connection failed - provide clear error message
                raise ValueError(f"Failed to connect to Jira server at {self.server_url}. Check your authentication credentials.")
            
        try:
            transitions = self.client.transitions(issue_key)
            
            return [
                JiraTransitionResult(
                    id=transition['id'],
                    name=transition['name']
                )
                for transition in transitions
            ]
        except Exception as e:
            print(f"Failed to get transitions for {issue_key}: {type(e).__name__}: {str(e)}")
            raise ValueError(f"Failed to get transitions for {issue_key}: {type(e).__name__}: {str(e)}")

    def transition_jira_issue(self, issue_key: str, transition_id: str, 
                         comment: Optional[str] = None, fields: Optional[Dict[str, Any]] = None) -> bool:
        """Transition an issue to a new state"""
        if not self.client:
            if not self.connect():
                # Connection failed - provide clear error message
                raise ValueError(f"Failed to connect to Jira server at {self.server_url}. Check your authentication credentials.")
            
        try:
            # Add fields if provided
            kwargs = {}
            if fields:
                kwargs['fields'] = fields
            if comment:
                kwargs['comment'] = comment
                
            self.client.transition_issue(issue_key, transition_id, **kwargs)
            return True
        except Exception as e:
            print(f"Failed to transition {issue_key}: {type(e).__name__}: {str(e)}")
            raise ValueError(f"Failed to transition {issue_key}: {type(e).__name__}: {str(e)}")
            
    def get_jira_project_issue_types(self, project_key: str) -> List[Dict[str, Any]]:
        """Get all available issue types for a specific project
        
        Args:
            project_key: The project key (e.g., 'PROJ')
            
        Returns:
            List of issue type dictionaries with name, id, and description
            
        Example:
            get_jira_project_issue_types('PROJ')  # Returns issue types for project with key 'PROJ'
        """
        if not self.client:
            if not self.connect():
                raise ValueError(f"Failed to connect to Jira server at {self.server_url}. Check your authentication credentials.")
                
        try:
            # First, try the most direct method - using createmeta
            meta = self.client.createmeta(projectKeys=project_key, expand="projects.issuetypes")
            
            if 'projects' in meta and meta['projects']:
                project = meta['projects'][0]
                if 'issuetypes' in project:
                    issue_types = []
                    for issuetype in project['issuetypes']:
                        issue_types.append({
                            'id': issuetype.get('id'),
                            'name': issuetype.get('name'),
                            'description': issuetype.get('description')
                        })
                    return issue_types
            
            # Fallback: Get all issue types and filter
            all_issue_types = self.client.issue_types()
            
            # Create a formatted list of issue types
            issue_types = []
            for issuetype in all_issue_types:
                issue_types.append({
                    'id': issuetype.id,
                    'name': issuetype.name,
                    'description': issuetype.description
                })
                
            return issue_types
            
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            print(f"Failed to get issue types for project {project_key}: {error_type}: {error_msg}")
            raise ValueError(f"Failed to get issue types for project {project_key}: {error_type}: {error_msg}")
    
    def create_jira_project(self, key: str, name: str = None, assignee: str = None, ptype: str = 'software', 
                       template_name: str = None, avatarId: int = None, issueSecurityScheme: int = None, 
                       permissionScheme: int = None, projectCategory: int = None, 
                       notificationScheme: int = None, categoryId: int = None, url: str = '') -> JiraProjectResult:
        """Create a project using Jira's v3 REST API
        
        Args:
            key: Project key (required) - must match Jira project key requirements
            name: Project name (defaults to key if not provided)
            assignee: Lead account ID or username
            ptype: Project type key ('software', 'business', 'service_desk')
            template_name: Project template key for creating from templates
            avatarId: ID of the avatar to use for the project
            issueSecurityScheme: ID of the issue security scheme
            permissionScheme: ID of the permission scheme  
            projectCategory: ID of the project category
            notificationScheme: ID of the notification scheme
            categoryId: Same as projectCategory (alternative parameter)
            url: URL for project information/documentation
            
        Returns:
            JiraProjectResult with the created project details
            
        Note:
            This method uses Jira's v3 REST API endpoint: POST /rest/api/3/project
            
        Example:
            # Create a basic software project
            create_jira_project(
                key='PROJ',
                name='My Project',
                ptype='software'
            )
            
            # Create with template
            create_jira_project(
                key='BUSI',
                name='Business Project', 
                ptype='business',
                template_name='com.atlassian.jira-core-project-templates:jira-core-simplified-task-tracking'
            )
        """
        if not key:
            raise ValueError("Project key is required")
            
        try:
            # Build the v3 API request payload
            payload = {
                'key': key,
                'name': name or key
            }
            
            # Map project type to projectTypeKey
            if ptype:
                payload['projectTypeKey'] = ptype
                
            # Map template_name to projectTemplateKey  
            if template_name:
                payload['projectTemplateKey'] = template_name
                
            # Map assignee to leadAccountId
            if assignee:
                payload['leadAccountId'] = assignee
                
            # Add optional numeric parameters
            if avatarId is not None:
                payload['avatarId'] = avatarId
            if issueSecurityScheme is not None:
                payload['issueSecurityScheme'] = issueSecurityScheme
            if permissionScheme is not None:
                payload['permissionScheme'] = permissionScheme
            if notificationScheme is not None:
                payload['notificationScheme'] = notificationScheme
                
            # Handle categoryId (prefer categoryId over projectCategory for v3 API)
            if categoryId is not None:
                payload['categoryId'] = categoryId
            elif projectCategory is not None:
                payload['categoryId'] = projectCategory
                
            # Add URL if provided
            if url:
                payload['url'] = url
                
            # Set assigneeType to PROJECT_LEAD (v3 API default)
            payload['assigneeType'] = 'PROJECT_LEAD'
            
            print(f"Creating project with v3 API payload: {json.dumps(payload, indent=2)}")
            
            # Make the v3 API request
            response_data = self._make_v3_api_request('POST', '/project', payload)
            
            print(f"Project creation response: {json.dumps(response_data, indent=2)}")
            
            # Extract project details from response
            project_id = response_data.get('id', '0')
            project_key = response_data.get('key', key)
            project_self_url = response_data.get('self', '')
            
            # For lead information, we would need to make another API call
            # For now, return None for lead as it's optional in our result model
            lead = None
            
            return JiraProjectResult(
                key=project_key,
                name=name or key,
                id=str(project_id),
                lead=lead
            )
            
        except Exception as e:
            error_msg = str(e)
            print(f"Error creating project with v3 API: {error_msg}")
            raise ValueError(f"Error creating project: {error_msg}")


async def serve(
    server_url: str = None, 
    auth_method: str = None,
    username: str = None,
    password: str = None,
    token: str = None
) -> None:
    server = Server("mcp-jira")
    jira_server = JiraServer(
        server_url=server_url,
        auth_method=auth_method,
        username=username,
        password=password,
        token=token
    )

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available Jira tools."""
        return [
            Tool(
                name=JiraTools.GET_PROJECTS.value,
                description="Get all accessible Jira projects",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                },
            ),
            Tool(
                name=JiraTools.GET_ISSUE.value,
                description="Get details for a specific Jira issue by key",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "issue_key": {
                            "type": "string",
                            "description": "The issue key (e.g., PROJECT-123)",
                        }
                    },
                    "required": ["issue_key"],
                },
            ),
            Tool(
                name=JiraTools.SEARCH_ISSUES.value,
                description="Search for Jira issues using JQL (Jira Query Language)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "jql": {
                            "type": "string",
                            "description": "JQL query string (e.g., 'project = MYPROJ AND status = \"In Progress\"')",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default: 10)",
                        }
                    },
                    "required": ["jql"],
                },
            ),
            Tool(
                name=JiraTools.CREATE_ISSUE.value,
                description="Create a new Jira issue. Common issue types include 'Bug', 'Task', 'Story', 'Epic' (capitalization handled automatically)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project": {
                            "type": "string",
                            "description": "Project key (e.g., 'MYPROJ')",
                        },
                        "summary": {
                            "type": "string",
                            "description": "Issue summary/title",
                        },
                        "description": {
                            "type": "string",
                            "description": "Issue description",
                        },
                        "issue_type": {
                            "type": "string",
                            "description": "Issue type (e.g., 'Bug', 'Task', 'Story', 'Epic', 'New Feature', 'Improvement'). IMPORTANT: Types are case-sensitive and vary by Jira instance.",
                        },
                        "fields": {
                            "type": "object",
                            "description": "Additional fields for the issue (optional)",
                        }
                    },
                    "required": ["project", "summary", "description", "issue_type"],
                },
            ),
            Tool(
                name=JiraTools.CREATE_ISSUES.value,
                description="Bulk create new Jira issues. IMPORTANT: For 'issue_type', use the exact case-sensitive types in your Jira instance (common: 'Bug', 'Task', 'Story', 'Epic')",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "field_list": {
                            "type": "array",
                            "description": "A list of field dictionaries, each representing an issue to create",
                            "items": {
                                "type": "object",
                                "description": "Field dictionary for a single issue"
                            }
                        },
                        "prefetch": {
                            "type": "boolean",
                            "description": "Whether to reload created issues (default: true)"
                        }
                    },
                    "required": ["field_list"],
                },
            ),
            Tool(
                name=JiraTools.ADD_COMMENT.value,
                description="Add a comment to a Jira issue",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "issue_key": {
                            "type": "string",
                            "description": "The issue key (e.g., PROJECT-123)",
                        },
                        "comment": {
                            "type": "string",
                            "description": "The comment text",
                        }
                    },
                    "required": ["issue_key", "comment"],
                },
            ),
            Tool(
                name=JiraTools.GET_TRANSITIONS.value,
                description="Get available workflow transitions for a Jira issue",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "issue_key": {
                            "type": "string",
                            "description": "The issue key (e.g., PROJECT-123)",
                        }
                    },
                    "required": ["issue_key"],
                },
            ),
            Tool(
                name=JiraTools.TRANSITION_ISSUE.value,
                description="Transition a Jira issue to a new status",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "issue_key": {
                            "type": "string",
                            "description": "The issue key (e.g., PROJECT-123)",
                        },
                        "transition_id": {
                            "type": "string",
                            "description": "ID of the transition to perform (get IDs using get_transitions)",
                        },
                        "comment": {
                            "type": "string",
                            "description": "Comment to add during transition (optional)",
                        },
                        "fields": {
                            "type": "object",
                            "description": "Additional fields to update during transition (optional)",
                        }
                    },
                    "required": ["issue_key", "transition_id"],
                },
            ),
            Tool(
                name=JiraTools.GET_PROJECT_ISSUE_TYPES.value,
                description="Get all available issue types for a specific Jira project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_key": {
                            "type": "string",
                            "description": "The project key (e.g., 'MYPROJ')",
                        }
                    },
                    "required": ["project_key"],
                },
            ),
            Tool(
                name=JiraTools.CREATE_PROJECT.value,
                description="Create a new Jira project using v3 REST API",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "Mandatory. Must match Jira project key requirements, usually only 2-10 uppercase characters."
                        },
                        "name": {
                            "type": "string",
                            "description": "If not specified it will use the key value."
                        },
                        "assignee": {
                            "type": "string",
                            "description": "Lead account ID or username (mapped to leadAccountId in v3 API)."
                        },
                        "ptype": {
                            "type": "string",
                            "description": "Project type key: 'software', 'business', or 'service_desk'. Defaults to 'software'."
                        },
                        "template_name": {
                            "type": "string",
                            "description": "Project template key for creating from templates (mapped to projectTemplateKey in v3 API)."
                        },
                        "avatarId": {
                            "type": ["integer", "string"],
                            "description": "ID of the avatar to use for the project."
                        },
                        "issueSecurityScheme": {
                            "type": ["integer", "string"],
                            "description": "Determines the security scheme to use."
                        },
                        "permissionScheme": {
                            "type": ["integer", "string"],
                            "description": "Determines the permission scheme to use."
                        },
                        "projectCategory": {
                            "type": ["integer", "string"],
                            "description": "Determines the category the project belongs to."
                        },
                        "notificationScheme": {
                            "type": ["integer", "string"],
                            "description": "Determines the notification scheme to use. Default is None."
                        },
                        "categoryId": {
                            "type": ["integer", "string"],
                            "description": "Same as projectCategory. Can be used interchangeably."
                        },
                        "url": {
                            "type": "string",
                            "description": "A link to information about the project, such as documentation."
                        }
                    },
                    "required": ["key"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(
        name: str, arguments: dict
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool calls for Jira operations."""
        try:
            match name:
                case JiraTools.GET_PROJECTS.value:
                    # projects() takes no parameters according to the docs
                    result = jira_server.get_jira_projects()

                case JiraTools.GET_ISSUE.value:
                    issue_key = arguments.get("issue_key")
                    if not issue_key:
                        raise ValueError("Missing required argument: issue_key")
                    
                    result = jira_server.get_jira_issue(issue_key)

                case JiraTools.SEARCH_ISSUES.value:
                    jql = arguments.get("jql")
                    if not jql:
                        raise ValueError("Missing required argument: jql")
                    
                    max_results = arguments.get("max_results", 10)
                    result = jira_server.search_jira_issues(jql, max_results)

                case JiraTools.CREATE_ISSUE.value:
                    required_args = ["project", "summary", "description", "issue_type"]
                    if not all(arg in arguments for arg in required_args):
                        missing = [arg for arg in required_args if arg not in arguments]
                        raise ValueError(f"Missing required arguments: {', '.join(missing)}")
                    
                    fields = arguments.get("fields", {})
                    result = jira_server.create_jira_issue(
                        arguments["project"],
                        arguments["summary"],
                        arguments["description"],
                        arguments["issue_type"],
                        fields
                    )
                    
                case JiraTools.CREATE_ISSUES.value:
                    field_list = arguments.get("field_list")
                    if not field_list:
                        raise ValueError("Missing required argument: field_list")
                    
                    prefetch = arguments.get("prefetch", True)
                    result = jira_server.create_jira_issues(field_list, prefetch)

                case JiraTools.ADD_COMMENT.value:
                    issue_key = arguments.get("issue_key")
                    comment = arguments.get("comment")
                    body = arguments.get("body")
                    
                    # Support both 'comment' and 'body' parameters for flexibility
                    comment_text = comment or body
                    
                    if not issue_key or not comment_text:
                        raise ValueError("Missing required arguments: issue_key and comment (or body)")
                    
                    result = jira_server.add_jira_comment(issue_key, comment_text)

                case JiraTools.GET_TRANSITIONS.value:
                    issue_key = arguments.get("issue_key")
                    if not issue_key:
                        raise ValueError("Missing required argument: issue_key")
                    
                    result = jira_server.get_jira_transitions(issue_key)

                case JiraTools.TRANSITION_ISSUE.value:
                    issue_key = arguments.get("issue_key")
                    transition_id = arguments.get("transition_id")
                    if not issue_key or not transition_id:
                        raise ValueError("Missing required arguments: issue_key and transition_id")
                    
                    comment = arguments.get("comment")
                    fields = arguments.get("fields")
                    result = jira_server.transition_jira_issue(issue_key, transition_id, comment, fields)
                
                case JiraTools.GET_PROJECT_ISSUE_TYPES.value:
                    project_key = arguments.get("project_key")
                    if not project_key:
                        raise ValueError("Missing required argument: project_key")
                    
                    result = jira_server.get_jira_project_issue_types(project_key)
                    
                case JiraTools.CREATE_PROJECT.value:
                    # Get parameters directly from arguments
                    key = arguments.get("key")  # Required parameter
                    if not key:
                        raise ValueError("Missing required argument: key")
                        
                    name = arguments.get("name")
                    assignee = arguments.get("assignee")
                    ptype = arguments.get("ptype", "software")  # Default to 'software'
                    template_name = arguments.get("template_name")
                    avatarId = arguments.get("avatarId")
                    issueSecurityScheme = arguments.get("issueSecurityScheme")
                    permissionScheme = arguments.get("permissionScheme")
                    projectCategory = arguments.get("projectCategory")
                    notificationScheme = arguments.get("notificationScheme")
                    categoryId = arguments.get("categoryId")
                    url = arguments.get("url", "")  # Default to empty string
                    
                    # Convert string values to integers where necessary
                    if isinstance(avatarId, str) and avatarId.isdigit():
                        avatarId = int(avatarId)
                    if isinstance(issueSecurityScheme, str) and issueSecurityScheme.isdigit():
                        issueSecurityScheme = int(issueSecurityScheme)
                    if isinstance(permissionScheme, str) and permissionScheme.isdigit():
                        permissionScheme = int(permissionScheme)
                    if isinstance(projectCategory, str) and projectCategory.isdigit():
                        projectCategory = int(projectCategory)
                    if isinstance(notificationScheme, str) and notificationScheme.isdigit():
                        notificationScheme = int(notificationScheme)
                    if isinstance(categoryId, str) and categoryId.isdigit():
                        categoryId = int(categoryId)
                    
                    # Call create_project with exactly the parameters from the documentation
                    result = jira_server.create_jira_project(
                        key=key,
                        name=name,
                        assignee=assignee,
                        ptype=ptype,
                        template_name=template_name,
                        avatarId=avatarId,
                        issueSecurityScheme=issueSecurityScheme,
                        permissionScheme=permissionScheme,
                        projectCategory=projectCategory,
                        notificationScheme=notificationScheme,
                        categoryId=categoryId,
                        url=url
                    )

                case _:
                    raise ValueError(f"Unknown tool: {name}")

            return [
                TextContent(type="text", text=json.dumps(
                    result if isinstance(result, bool) else 
                    [r.model_dump() if hasattr(r, 'model_dump') else r for r in result] if isinstance(result, list) else 
                    (result.model_dump() if hasattr(result, 'model_dump') else result),
                    indent=2
                ))
            ]

        except Exception as e:
            # Parse the error properly
            error_type = type(e).__name__
            error_msg = str(e)
            print(f"Error in call_tool: {error_type}: {error_msg}")
            
            # Return a detailed error
            return [TextContent(type="text", text=json.dumps(
                {
                    "error": f"Error processing Jira query: {error_type}: {error_msg}"
                },
                indent=2
            ))]

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options)