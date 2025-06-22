import json
import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union
import logging
import asyncio
import sys

# --- Setup a dedicated file logger ---
log_file_path = Path(__file__).parent / "jira_mcp_debug.log"
logger = logging.getLogger("JiraMCPLogger")
logger.setLevel(logging.DEBUG)  # Capture all levels of logs

# Create a file handler to write logs to a file
# Use 'w' to overwrite the file on each run, ensuring a clean log
handler = logging.FileHandler(log_file_path, mode="w")
handler.setLevel(logging.DEBUG)

# Create a formatter to make the logs readable
formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
)
handler.setFormatter(formatter)

# Add the handler to the logger
if not logger.handlers:
    logger.addHandler(handler)

logger.info("Logger initialized. All subsequent logs will go to jira_mcp_debug.log")
# --- End of logger setup ---

try:
    from jira import JIRA
except ImportError:
    from .jira import JIRA
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool
from pydantic import BaseModel

from .jira_v3_api import JiraV3APIClient

try:
    from dotenv import load_dotenv

    # Try to load from .env file if it exists
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
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
    def __init__(
        self,
        server_url: str = None,
        auth_method: str = None,
        username: str = None,
        password: str = None,
        token: str = None,
    ):
        self.server_url = server_url
        self.auth_method = auth_method
        self.username = username
        self.password = password
        self.token = token

        self._v3_api_client = JiraV3APIClient(
            server_url=self.server_url,
            username=self.username,
            token=self.token,
            password=password,
        )
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
                        self.client = JIRA(
                            server=self.server_url,
                            basic_auth=(self.username, self.password),
                        )
                        print("Connection successful with username/password")
                        return True
                    except Exception as e:
                        error_msg = f"Failed basic_auth with username/password: {type(e).__name__}: {str(e)}"
                        print(error_msg)
                        error_messages.append(error_msg)

                if self.username and self.token:
                    try:
                        print(f"Trying basic_auth with username and API token")
                        self.client = JIRA(
                            server=self.server_url,
                            basic_auth=(self.username, self.token),
                        )
                        print("Connection successful with username/token")
                        return True
                    except Exception as e:
                        error_msg = f"Failed basic_auth with username/token: {type(e).__name__}: {str(e)}"
                        print(error_msg)
                        error_messages.append(error_msg)

                print("Error: Username and password/token required for basic auth")
                error_messages.append(
                    "Username and password/token required for basic auth"
                )

            elif self.auth_method == "token_auth":
                # Token auth - just need the token
                if self.token:
                    try:
                        print(f"Trying token_auth with token")
                        self.client = JIRA(
                            server=self.server_url, token_auth=self.token
                        )
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
                    self.client = JIRA(
                        server=self.server_url, basic_auth=(self.username, self.token)
                    )
                    print("Connection successful with fallback basic_auth")
                    return True
                except Exception as e:
                    error_msg = (
                        f"Failed fallback to basic_auth: {type(e).__name__}: {str(e)}"
                    )
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
                    error_msg = (
                        f"Failed fallback to token_auth: {type(e).__name__}: {str(e)}"
                    )
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

    def _get_v3_api_client(self) -> JiraV3APIClient:
        """Get or create a v3 API client instance"""
        if not self._v3_api_client:
            self._v3_api_client = JiraV3APIClient(
                server_url=self.server_url,
                username=self.username,
                password=self.password,
                token=self.token,
            )
        return self._v3_api_client

    async def get_jira_projects(self) -> List[JiraProjectResult]:
        """Get all accessible Jira projects using v3 REST API"""
        logger.info("Starting get_jira_projects...")
        all_projects_data = []
        start_at = 0
        max_results = 50
        page_count = 0

        while True:
            page_count += 1
            logger.info(
                f"Pagination loop, page {page_count}: startAt={start_at}, maxResults={max_results}"
            )

            try:
                response = await self._v3_api_client.get_projects(
                    start_at=start_at, max_results=max_results
                )

                projects = response.get("values", [])
                if not projects:
                    logger.info("No more projects returned. Breaking pagination loop.")
                    break

                all_projects_data.extend(projects)

                if response.get("isLast", False):
                    logger.info("'isLast' is True. Breaking pagination loop.")
                    break

                start_at += len(projects)

                # Yield control to the event loop to prevent deadlocks in the MCP framework.
                await asyncio.sleep(0)

            except Exception as e:
                logger.error(
                    "Error inside get_jira_projects pagination loop", exc_info=True
                )
                raise

        logger.info(
            f"Finished get_jira_projects. Total projects found: {len(all_projects_data)}"
        )

        results = []
        for p in all_projects_data:
            results.append(
                JiraProjectResult(
                    key=p.get("key"),
                    name=p.get("name"),
                    id=str(p.get("id")),
                    lead=(p.get("lead") or {}).get("displayName"),
                )
            )
            logger.info(f"Added project {p.get('key')} to results")
        logger.info(f"Returning {len(results)} projects")
        sys.stdout.flush()  # Flush stdout to ensure it's sent to MCP, otherwise hang occurs
        return results

    def get_jira_issue(self, issue_key: str) -> JiraIssueResult:
        """Get details for a specific issue by key"""
        if not self.client:
            if not self.connect():
                # Connection failed - provide clear error message
                raise ValueError(
                    f"Failed to connect to Jira server at {self.server_url}. Check your authentication credentials."
                )

        try:
            issue = self.client.issue(issue_key)

            # Extract comments if available
            comments = []
            if hasattr(issue.fields, "comment") and hasattr(
                issue.fields.comment, "comments"
            ):
                for comment in issue.fields.comment.comments:
                    comments.append(
                        {
                            "author": (
                                getattr(
                                    comment.author, "displayName", str(comment.author)
                                )
                                if hasattr(comment, "author")
                                else "Unknown"
                            ),
                            "body": comment.body,
                            "created": comment.created,
                        }
                    )

            # Create a fields dictionary with custom fields
            fields = {}
            for field_name in dir(issue.fields):
                if not field_name.startswith("_") and field_name not in [
                    "comment",
                    "attachment",
                    "summary",
                    "description",
                    "status",
                    "assignee",
                    "reporter",
                    "created",
                    "updated",
                ]:
                    value = getattr(issue.fields, field_name)
                    if value is not None:
                        # Handle special field types
                        if hasattr(value, "name"):
                            fields[field_name] = value.name
                        elif hasattr(value, "value"):
                            fields[field_name] = value.value
                        elif isinstance(value, list):
                            if len(value) > 0:
                                if hasattr(value[0], "name"):
                                    fields[field_name] = [item.name for item in value]
                                else:
                                    fields[field_name] = value
                        else:
                            fields[field_name] = str(value)

            return JiraIssueResult(
                key=issue.key,
                summary=issue.fields.summary,
                description=issue.fields.description,
                status=(
                    issue.fields.status.name
                    if hasattr(issue.fields, "status")
                    else None
                ),
                assignee=(
                    issue.fields.assignee.displayName
                    if hasattr(issue.fields, "assignee") and issue.fields.assignee
                    else None
                ),
                reporter=(
                    issue.fields.reporter.displayName
                    if hasattr(issue.fields, "reporter") and issue.fields.reporter
                    else None
                ),
                created=(
                    issue.fields.created if hasattr(issue.fields, "created") else None
                ),
                updated=(
                    issue.fields.updated if hasattr(issue.fields, "updated") else None
                ),
                fields=fields,
                comments=comments,
            )
        except Exception as e:
            print(f"Failed to get issue {issue_key}: {type(e).__name__}: {str(e)}")
            raise ValueError(
                f"Failed to get issue {issue_key}: {type(e).__name__}: {str(e)}"
            )

    def search_jira_issues(
        self, jql: str, max_results: int = 10
    ) -> List[JiraIssueResult]:
        """Search for issues using JQL"""
        if not self.client:
            if not self.connect():
                # Connection failed - provide clear error message
                raise ValueError(
                    f"Failed to connect to Jira server at {self.server_url}. Check your authentication credentials."
                )

        try:
            issues = self.client.search_issues(jql, maxResults=max_results)

            return [
                JiraIssueResult(
                    key=issue.key,
                    summary=issue.fields.summary,
                    description=issue.fields.description,
                    status=(
                        issue.fields.status.name
                        if hasattr(issue.fields, "status")
                        else None
                    ),
                    assignee=(
                        issue.fields.assignee.displayName
                        if hasattr(issue.fields, "assignee") and issue.fields.assignee
                        else None
                    ),
                    reporter=(
                        issue.fields.reporter.displayName
                        if hasattr(issue.fields, "reporter") and issue.fields.reporter
                        else None
                    ),
                    created=(
                        issue.fields.created
                        if hasattr(issue.fields, "created")
                        else None
                    ),
                    updated=(
                        issue.fields.updated
                        if hasattr(issue.fields, "updated")
                        else None
                    ),
                )
                for issue in issues
            ]
        except Exception as e:
            print(f"Failed to search issues: {type(e).__name__}: {str(e)}")
            raise ValueError(f"Failed to search issues: {type(e).__name__}: {str(e)}")

    def create_jira_issue(
        self,
        project: str,
        summary: str,
        description: str,
        issue_type: str,
        fields: Optional[Dict[str, Any]] = None,
    ) -> JiraIssueResult:
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
                raise ValueError(
                    f"Failed to connect to Jira server at {self.server_url}. Check your authentication credentials."
                )

        try:
            # Create a properly formatted issue dictionary
            issue_dict = {}

            # Process required fields first
            # Project field - required
            if isinstance(project, str):
                issue_dict["project"] = {"key": project}
            else:
                issue_dict["project"] = project

            # Summary - required
            issue_dict["summary"] = summary

            # Description
            if description:
                issue_dict["description"] = description

            # Issue type - required, with validation for common issue types
            # Add for better debugging - print available types
            print(f"Processing issue_type: '{issue_type}' (type: {type(issue_type)})")
            common_types = [
                "bug",
                "task",
                "story",
                "epic",
                "improvement",
                "newfeature",
                "new feature",
            ]

            if isinstance(issue_type, str):
                # Check for common issue type variants and fix case-sensitivity issues
                issue_type_lower = issue_type.lower()

                if issue_type_lower in common_types:
                    # Convert first letter to uppercase for standard Jira types
                    issue_type_proper = issue_type_lower.capitalize()
                    if (
                        issue_type_lower == "new feature"
                        or issue_type_lower == "newfeature"
                    ):
                        issue_type_proper = "New Feature"

                    print(
                        f"Note: Converting issue type from '{issue_type}' to '{issue_type_proper}'"
                    )
                    issue_dict["issuetype"] = {"name": issue_type_proper}
                else:
                    # Use the type as provided - some Jira instances have custom types
                    issue_dict["issuetype"] = {"name": issue_type}
            else:
                issue_dict["issuetype"] = issue_type

            # Add any additional fields with proper type handling
            if fields:
                for key, value in fields.items():
                    # Skip fields we've already processed
                    if key in [
                        "project",
                        "summary",
                        "description",
                        "issuetype",
                        "issue_type",
                    ]:
                        continue

                    # Handle special fields that require specific formats
                    if key == "assignees" or key == "assignee":
                        # Convert string to array for assignees or proper format for assignee
                        if isinstance(value, str):
                            if key == "assignees":
                                issue_dict[key] = [value] if value else []
                            else:  # assignee
                                issue_dict[key] = {"name": value} if value else None
                        elif isinstance(value, list) and key == "assignee" and value:
                            # If assignee is a list but should be a dict with name
                            issue_dict[key] = {"name": value[0]}
                        else:
                            issue_dict[key] = value
                    elif key == "labels":
                        # Convert string to array for labels
                        if isinstance(value, str):
                            issue_dict[key] = [value] if value else []
                        else:
                            issue_dict[key] = value
                    elif key == "milestone":
                        # Convert string to number for milestone
                        if isinstance(value, str) and value.isdigit():
                            issue_dict[key] = int(value)
                        else:
                            issue_dict[key] = value
                    else:
                        issue_dict[key] = value

            # Print the finalized issue dict for debugging
            print(
                f"Sending issue dictionary to Jira: {json.dumps(issue_dict, indent=2)}"
            )

            # Use the client's create_issue method with the properly formatted fields dict
            try:
                new_issue = self.client.create_issue(fields=issue_dict)
            except Exception as e:
                error_type = type(e).__name__
                error_message = str(e)

                # Check if the error might be related to the issue type
                if (
                    "issuetype" in error_message.lower()
                    or "issue type" in error_message.lower()
                ):
                    print(
                        f"Issue type error detected! Your Jira instance may require specific issue types."
                    )
                    attempted_type = issue_dict.get("issuetype", {}).get(
                        "name", "Unknown"
                    )
                    print(f"Attempted issue type: '{attempted_type}'")
                    print(f"Full error: {error_type}: {error_message}")

                    # Try to fetch available issue types for this project
                    try:
                        project_key = issue_dict.get("project", {}).get("key")
                        if project_key:
                            print(
                                f"Fetching available issue types for project {project_key}..."
                            )
                            issue_types = asyncio.run(self.get_jira_project_issue_types(project_key))
                            type_names = [t.get("name") for t in issue_types]
                            print(f"Available issue types: {', '.join(type_names)}")

                            # Try to find the closest match
                            closest = None
                            attempted_lower = attempted_type.lower()
                            for t in type_names:
                                if (
                                    attempted_lower in t.lower()
                                    or t.lower() in attempted_lower
                                ):
                                    closest = t
                                    break

                            if closest:
                                print(
                                    f"The closest match to '{attempted_type}' is '{closest}'"
                                )
                                print(f"Try using '{closest}' instead")
                    except Exception as fetch_error:
                        print(f"Could not fetch issue types: {str(fetch_error)}")

                # Re-raise the exception with more details
                if "issuetype" in error_message.lower():
                    raise ValueError(
                        f"Invalid issue type '{issue_dict.get('issuetype', {}).get('name', 'Unknown')}'. "
                        + "Use get_jira_project_issue_types(project_key) to get valid types."
                    )
                raise

            return JiraIssueResult(
                key=new_issue.key,
                summary=new_issue.fields.summary,
                description=new_issue.fields.description,
                status=(
                    new_issue.fields.status.name
                    if hasattr(new_issue.fields, "status")
                    else None
                ),
            )
        except Exception as e:
            print(f"Failed to create issue: {type(e).__name__}: {str(e)}")
            raise ValueError(f"Failed to create issue: {type(e).__name__}: {str(e)}")

    def create_jira_issues(
        self, field_list: List[Dict[str, Any]], prefetch: bool = True
    ) -> List[Dict[str, Any]]:
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
                raise ValueError(
                    f"Failed to connect to Jira server at {self.server_url}. Check your authentication credentials."
                )

        try:
            # Process each field dict to ensure proper formatting
            processed_field_list = []
            for fields in field_list:
                # Create a properly formatted issue dictionary
                issue_dict = {}

                # Process required fields first to ensure they exist
                # Project field - required
                if "project" not in fields:
                    raise ValueError("Each issue must have a 'project' field")
                project_value = fields["project"]
                if isinstance(project_value, str):
                    issue_dict["project"] = {"key": project_value}
                else:
                    issue_dict["project"] = project_value

                # Summary field - required
                if "summary" not in fields:
                    raise ValueError("Each issue must have a 'summary' field")
                issue_dict["summary"] = fields["summary"]

                # Description field
                if "description" in fields:
                    issue_dict["description"] = fields["description"]

                # Issue type field - required, handle both 'issuetype' and 'issue_type'
                issue_type = None
                if "issuetype" in fields:
                    issue_type = fields["issuetype"]
                elif "issue_type" in fields:
                    issue_type = fields["issue_type"]
                else:
                    raise ValueError(
                        "Each issue must have an 'issuetype' or 'issue_type' field"
                    )

                # Check for common issue type variants and fix case-sensitivity issues
                # Add debug information
                print(
                    f"Processing bulk issue_type: '{issue_type}' (type: {type(issue_type)})"
                )
                common_types = [
                    "bug",
                    "task",
                    "story",
                    "epic",
                    "improvement",
                    "newfeature",
                    "new feature",
                ]

                if isinstance(issue_type, str):
                    issue_type_lower = issue_type.lower()

                    if issue_type_lower in common_types:
                        # Convert first letter to uppercase for standard Jira types
                        issue_type_proper = issue_type_lower.capitalize()
                        if (
                            issue_type_lower == "new feature"
                            or issue_type_lower == "newfeature"
                        ):
                            issue_type_proper = "New Feature"

                        print(
                            f"Note: Converting issue type from '{issue_type}' to '{issue_type_proper}'"
                        )
                        issue_dict["issuetype"] = {"name": issue_type_proper}
                    else:
                        # Use the type as provided - some Jira instances have custom types
                        issue_dict["issuetype"] = {"name": issue_type}
                else:
                    issue_dict["issuetype"] = issue_type

                # Process other fields
                for key, value in fields.items():
                    if key in [
                        "project",
                        "summary",
                        "description",
                        "issuetype",
                        "issue_type",
                    ]:
                        # Skip fields we've already processed
                        continue

                    # Handle special fields that require specific formats
                    if key == "assignees" or key == "assignee":
                        # Convert string to array for assignees or proper format for assignee
                        if isinstance(value, str):
                            if key == "assignees":
                                issue_dict[key] = [value] if value else []
                            else:  # assignee
                                issue_dict[key] = {"name": value} if value else None
                        elif isinstance(value, list) and key == "assignee" and value:
                            # If assignee is a list but should be a dict with name
                            issue_dict[key] = {"name": value[0]}
                        else:
                            issue_dict[key] = value
                    elif key == "labels":
                        # Convert string to array for labels
                        if isinstance(value, str):
                            issue_dict[key] = [value] if value else []
                        else:
                            issue_dict[key] = value
                    elif key == "milestone":
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
            print(
                f"Sending field list to Jira: {json.dumps(processed_field_list, indent=2)}"
            )

            try:
                results = self.client.create_issues(
                    processed_field_list, prefetch=prefetch
                )
            except Exception as e:
                # If there's an error, log the field list and re-raise
                error_type = type(e).__name__
                error_msg = str(e)
                print(f"Error in create_issues: {error_type}: {error_msg}")
                print(f"With field list: {json.dumps(processed_field_list, indent=2)}")

                # Check if the error might be related to the issue type
                if (
                    "issuetype" in error_msg.lower()
                    or "issue type" in error_msg.lower()
                ):
                    print(
                        f"Issue type error detected! Your Jira instance may require specific issue types."
                    )

                    # Try to extract all issue types we attempted to use
                    issue_types = []
                    project_key = None
                    for issue in processed_field_list:
                        fields = issue.get("fields", {})
                        if "issuetype" in fields:
                            issue_type = (
                                fields["issuetype"].get("name", "Unknown")
                                if isinstance(fields["issuetype"], dict)
                                else str(fields["issuetype"])
                            )
                            issue_types.append(issue_type)

                        # Get the project key from the first issue
                        if not project_key and "project" in fields:
                            if isinstance(fields["project"], dict):
                                project_key = fields["project"].get("key")

                    print(f"Attempted issue types: {', '.join(issue_types)}")
                    print(f"Full error: {error_type}: {error_msg}")

                    # Try to fetch available issue types for this project
                    if project_key:
                        try:
                            print(
                                f"Fetching available issue types for project {project_key}..."
                            )
                            available_types = asyncio.run(self.get_jira_project_issue_types(
                                project_key
                            ))
                            type_names = [t.get("name") for t in available_types]
                            print(f"Available issue types: {', '.join(type_names)}")

                            # Try to find closest matches
                            for attempted in issue_types:
                                attempted_lower = attempted.lower()
                                closest = None
                                for t in type_names:
                                    if (
                                        attempted_lower in t.lower()
                                        or t.lower() in attempted_lower
                                    ):
                                        closest = t
                                        break

                                if closest:
                                    print(
                                        f"The closest match to '{attempted}' is '{closest}'"
                                    )
                        except Exception as fetch_error:
                            print(f"Could not fetch issue types: {str(fetch_error)}")

                    # Raise a more informative error
                    raise ValueError(
                        f"Invalid issue type(s): {', '.join(issue_types)}. "
                        + "Use get_jira_project_issue_types(project_key) to get valid types."
                    )

                # Try to handle common errors
                if "project" in str(e).lower():
                    # Try alternative format
                    alternative_field_list = []
                    for issue in processed_field_list:
                        # Ensure each issue has the project field
                        fields = issue.get("fields", {})
                        if "project" not in fields:
                            raise ValueError(
                                f"Issue missing 'project' field: {json.dumps(issue)}"
                            )
                        alternative_field_list.append(issue)

                    print(
                        f"Trying alternative format: {json.dumps(alternative_field_list, indent=2)}"
                    )
                    results = self.client.create_issues(
                        alternative_field_list, prefetch=prefetch
                    )
                else:
                    raise

            # Process the results
            processed_results = []
            for result in results:
                # Determine whether the issue was created successfully
                if "issue" in result:
                    issue = result["issue"]
                    # Extract the issue info
                    processed_results.append(
                        {
                            "key": issue.key,
                            "id": issue.id,
                            "self": getattr(issue, "self", None),
                            "success": True,
                        }
                    )
                else:
                    # Error case
                    processed_results.append(
                        {
                            "error": result.get("error", "Unknown error"),
                            "success": False,
                        }
                    )

            return processed_results

        except Exception as e:
            print(f"Failed to create issues in bulk: {type(e).__name__}: {str(e)}")
            raise ValueError(
                f"Failed to create issues in bulk: {type(e).__name__}: {str(e)}"
            )

    async def add_jira_comment(self, issue_key: str, comment: str) -> Dict[str, Any]:
        """Add a comment to an issue using v3 REST API"""
        logger.info("Starting add_jira_comment...")

        try:
            # Use v3 API client
            v3_client = self._get_v3_api_client()
            comment_result = await v3_client.add_comment(
                issue_id_or_key=issue_key,
                comment=comment,
            )

            # Extract useful information from the v3 API response
            response_data = {
                "id": comment_result.get("id"),
                "body": comment_result.get("body", {}),
                "created": comment_result.get("created"),
                "updated": comment_result.get("updated"),
            }

            # Extract author information if available
            if "author" in comment_result:
                author = comment_result["author"]
                response_data["author"] = author.get("displayName", "Unknown")
            else:
                response_data["author"] = "Unknown"

            logger.info(f"Successfully added comment to issue {issue_key}")
            return response_data

        except Exception as e:
            error_msg = (
                f"Failed to add comment to {issue_key}: {type(e).__name__}: {str(e)}"
            )
            logger.error(error_msg, exc_info=True)
            print(error_msg)
            raise ValueError(error_msg)

    async def get_jira_transitions(self, issue_key: str) -> List[JiraTransitionResult]:
        """Get available transitions for an issue using v3 REST API"""
        logger.info("Starting get_jira_transitions...")

        try:
            # Use v3 API client
            v3_client = self._get_v3_api_client()
            response_data = await v3_client.get_transitions(issue_id_or_key=issue_key)

            # Extract transitions from response
            transitions = response_data.get("transitions", [])

            # Convert to JiraTransitionResult objects maintaining compatibility
            results = [
                JiraTransitionResult(id=transition["id"], name=transition["name"])
                for transition in transitions
            ]

            logger.info(f"Found {len(results)} transitions for issue {issue_key}")
            return results

        except Exception as e:
            error_msg = f"Failed to get transitions for {issue_key}: {type(e).__name__}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            print(error_msg)
            raise ValueError(error_msg)

    async def transition_jira_issue(
        self,
        issue_key: str,
        transition_id: str,
        comment: Optional[str] = None,
        fields: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Transition an issue to a new state using v3 REST API"""
        logger.info("Starting transition_jira_issue...")

        try:
            # Use v3 API client
            v3_client = self._get_v3_api_client()
            await v3_client.transition_issue(
                issue_id_or_key=issue_key,
                transition_id=transition_id,
                fields=fields,
                comment=comment,
            )

            logger.info(
                f"Successfully transitioned issue {issue_key} to transition {transition_id}"
            )
            return True

        except Exception as e:
            error_msg = (
                f"Failed to transition {issue_key}: {type(e).__name__}: {str(e)}"
            )
            logger.error(error_msg, exc_info=True)
            print(error_msg)
            raise ValueError(error_msg)

    async def get_jira_project_issue_types(self, project_key: str) -> List[Dict[str, Any]]:
        """Get all available issue types for a specific project using v3 REST API

        Args:
            project_key: The project key (e.g., 'PROJ') - kept for backward compatibility,
                        but the new API returns all issue types for the user

        Returns:
            List of issue type dictionaries with name, id, and description

        Example:
            get_jira_project_issue_types('PROJ')  # Returns all issue types accessible to user
        """
        logger.info("Starting get_jira_project_issue_types...")

        try:
            # Use v3 API client to get all issue types
            v3_client = self._get_v3_api_client()
            response_data = await v3_client.get_issue_types()

            # The new API returns the issue types directly as a list, not wrapped in an object
            issue_types_data = response_data if isinstance(response_data, list) else response_data.get("issueTypes", [])

            # Convert to the expected format maintaining compatibility
            issue_types = []
            for issuetype in issue_types_data:
                issue_types.append(
                    {
                        "id": issuetype.get("id"),
                        "name": issuetype.get("name"),
                        "description": issuetype.get("description"),
                    }
                )

            logger.info(f"Found {len(issue_types)} issue types (project_key: {project_key})")
            return issue_types

        except Exception as e:
            error_msg = f"Failed to get issue types: {type(e).__name__}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            print(error_msg)
            raise ValueError(error_msg)

    async def create_jira_project(
        self,
        key: str,
        name: Optional[str] = None,
        assignee: Optional[str] = None,
        ptype: str = "software",
        template_name: Optional[str] = None,
        avatarId: Optional[int] = None,
        issueSecurityScheme: Optional[int] = None,
        permissionScheme: Optional[int] = None,
        projectCategory: Optional[int] = None,
        notificationScheme: Optional[int] = None,
        categoryId: Optional[int] = None,
        url: str = "",
    ) -> JiraProjectResult:
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
            # Get the v3 API client
            v3_client = self._get_v3_api_client()

            # Create project using v3 API
            response_data = await v3_client.create_project(
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
                url=url,
            )

            # Extract project details from response
            project_id = response_data.get("id", "0")
            project_key = response_data.get("key", key)

            # For lead information, we would need to make another API call
            # For now, return None for lead as it's optional in our result model
            lead = None

            return JiraProjectResult(
                key=project_key, name=name or key, id=str(project_id), lead=lead
            )

        except Exception as e:
            error_msg = str(e)
            print(f"Error creating project with v3 API: {error_msg}")
            raise ValueError(f"Error creating project: {error_msg}")


async def serve(
    server_url: Optional[str] = None,
    auth_method: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    token: Optional[str] = None,
) -> None:
    server = Server("mcp-jira")
    jira_server = JiraServer(
        server_url=server_url,
        auth_method=auth_method,
        username=username,
        password=password,
        token=token,
    )

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available Jira tools."""
        return [
            Tool(
                name=JiraTools.GET_PROJECTS.value,
                description="Get all accessible Jira projects",
                inputSchema={"type": "object", "properties": {}, "required": []},
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
                        },
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
                        },
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
                                "description": "Field dictionary for a single issue",
                            },
                        },
                        "prefetch": {
                            "type": "boolean",
                            "description": "Whether to reload created issues (default: true)",
                        },
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
                        },
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
                        },
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
                            "description": "Mandatory. Must match Jira project key requirements, usually only 2-10 uppercase characters.",
                        },
                        "name": {
                            "type": "string",
                            "description": "If not specified it will use the key value.",
                        },
                        "assignee": {
                            "type": "string",
                            "description": "Lead account ID or username (mapped to leadAccountId in v3 API).",
                        },
                        "ptype": {
                            "type": "string",
                            "description": "Project type key: 'software', 'business', or 'service_desk'. Defaults to 'software'.",
                        },
                        "template_name": {
                            "type": "string",
                            "description": "Project template key for creating from templates (mapped to projectTemplateKey in v3 API).",
                        },
                        "avatarId": {
                            "type": ["integer", "string"],
                            "description": "ID of the avatar to use for the project.",
                        },
                        "issueSecurityScheme": {
                            "type": ["integer", "string"],
                            "description": "Determines the security scheme to use.",
                        },
                        "permissionScheme": {
                            "type": ["integer", "string"],
                            "description": "Determines the permission scheme to use.",
                        },
                        "projectCategory": {
                            "type": ["integer", "string"],
                            "description": "Determines the category the project belongs to.",
                        },
                        "notificationScheme": {
                            "type": ["integer", "string"],
                            "description": "Determines the notification scheme to use. Default is None.",
                        },
                        "categoryId": {
                            "type": ["integer", "string"],
                            "description": "Same as projectCategory. Can be used interchangeably.",
                        },
                        "url": {
                            "type": "string",
                            "description": "A link to information about the project, such as documentation.",
                        },
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
        logger.info(f"call_tool invoked. Tool: '{name}', Arguments: {arguments}")
        try:
            result: Any

            match name:
                case JiraTools.GET_PROJECTS.value:
                    logger.info("About to AWAIT jira_server.get_jira_projects...")
                    result = await jira_server.get_jira_projects()
                    logger.info(
                        f"COMPLETED await jira_server.get_jira_projects. Result has {len(result)} items."
                    )

                case JiraTools.GET_ISSUE.value:
                    logger.info("Calling synchronous tool get_jira_issue...")
                    issue_key = arguments.get("issue_key")
                    if not issue_key:
                        raise ValueError("Missing required argument: issue_key")
                    result = jira_server.get_jira_issue(issue_key)
                    logger.info("Synchronous tool get_jira_issue completed.")

                case JiraTools.SEARCH_ISSUES.value:
                    logger.info("Calling synchronous tool search_jira_issues...")
                    jql = arguments.get("jql")
                    if not jql:
                        raise ValueError("Missing required argument: jql")
                    max_results = arguments.get("max_results", 10)
                    result = jira_server.search_jira_issues(jql, max_results)
                    logger.info("Synchronous tool search_jira_issues completed.")

                case JiraTools.CREATE_ISSUE.value:
                    logger.info("Calling synchronous tool create_jira_issue...")
                    required_args = ["project", "summary", "description", "issue_type"]
                    if not all(arg in arguments for arg in required_args):
                        missing = [arg for arg in required_args if arg not in arguments]
                        raise ValueError(
                            f"Missing required arguments: {', '.join(missing)}"
                        )
                    result = jira_server.create_jira_issue(
                        arguments["project"],
                        arguments["summary"],
                        arguments["description"],
                        arguments["issue_type"],
                        arguments.get("fields", {}),
                    )
                    logger.info("Synchronous tool create_jira_issue completed.")

                case JiraTools.CREATE_ISSUES.value:
                    logger.info("Calling synchronous tool create_jira_issues...")
                    field_list = arguments.get("field_list")
                    if not field_list:
                        raise ValueError("Missing required argument: field_list")
                    prefetch = arguments.get("prefetch", True)
                    result = jira_server.create_jira_issues(field_list, prefetch)
                    logger.info("Synchronous tool create_jira_issues completed.")

                case JiraTools.ADD_COMMENT.value:
                    logger.info("About to AWAIT jira_server.add_jira_comment...")
                    issue_key = arguments.get("issue_key")
                    comment_text = arguments.get("comment") or arguments.get("body")
                    if not issue_key or not comment_text:
                        raise ValueError(
                            "Missing required arguments: issue_key and comment (or body)"
                        )
                    result = await jira_server.add_jira_comment(issue_key, comment_text)
                    logger.info("COMPLETED await jira_server.add_jira_comment.")

                case JiraTools.GET_TRANSITIONS.value:
                    logger.info("About to AWAIT jira_server.get_jira_transitions...")
                    issue_key = arguments.get("issue_key")
                    if not issue_key:
                        raise ValueError("Missing required argument: issue_key")
                    result = await jira_server.get_jira_transitions(issue_key)
                    logger.info("COMPLETED await jira_server.get_jira_transitions.")

                case JiraTools.TRANSITION_ISSUE.value:
                    logger.info("Calling async tool transition_jira_issue...")
                    issue_key = arguments.get("issue_key")
                    transition_id = arguments.get("transition_id")
                    if not issue_key or not transition_id:
                        raise ValueError(
                            "Missing required arguments: issue_key and transition_id"
                        )
                    comment = arguments.get("comment")
                    fields = arguments.get("fields")
                    result = await jira_server.transition_jira_issue(
                        issue_key, transition_id, comment, fields
                    )
                    logger.info("Async tool transition_jira_issue completed.")

                case JiraTools.GET_PROJECT_ISSUE_TYPES.value:
                    logger.info(
                        "Calling asynchronous tool get_jira_project_issue_types..."
                    )
                    project_key = arguments.get("project_key")
                    if not project_key:
                        raise ValueError("Missing required argument: project_key")
                    result = await jira_server.get_jira_project_issue_types(project_key)
                    logger.info(
                        "Asynchronous tool get_jira_project_issue_types completed."
                    )

                case JiraTools.CREATE_PROJECT.value:
                    logger.info("About to AWAIT jira_server.create_jira_project...")
                    key = arguments.get("key")
                    if not key:
                        raise ValueError("Missing required argument: key")
                    # Type conversion logic from original code
                    for int_key in [
                        "avatarId",
                        "issueSecurityScheme",
                        "permissionScheme",
                        "projectCategory",
                        "notificationScheme",
                        "categoryId",
                    ]:
                        if (
                            int_key in arguments
                            and isinstance(arguments[int_key], str)
                            and arguments[int_key].isdigit()
                        ):
                            arguments[int_key] = int(arguments[int_key])
                    result = await jira_server.create_jira_project(**arguments)
                    logger.info("COMPLETED await jira_server.create_jira_project.")

                case _:
                    raise ValueError(f"Unknown tool: {name}")

            logger.debug("Serializing result to JSON...")
            
            # Handle serialization properly for different result types
            if isinstance(result, list):
                # If it's a list, check each item individually
                serialized_result = []
                for item in result:
                    if hasattr(item, "model_dump"):
                        serialized_result.append(item.model_dump())
                    else:
                        # It's already a dict or basic type
                        serialized_result.append(item)
            else:
                # Single item result
                if hasattr(result, "model_dump"):
                    serialized_result = result.model_dump()
                else:
                    # It's already a dict or basic type
                    serialized_result = result
                    
            json_result = json.dumps(serialized_result, indent=2)
            logger.warning("RETURNING HARDCODED DEBUG MESSAGE INSTEAD OF REAL DATA")
            return [TextContent(type="text", text=json_result)]

        except Exception as e:
            logger.critical(
                f"FATAL error in call_tool for tool '{name}'", exc_info=True
            )
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "error": f"Error in tool '{name}': {type(e).__name__}: {str(e)}"
                        }
                    ),
                )
            ]

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options)
