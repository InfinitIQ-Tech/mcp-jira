"""
Jira v3 REST API client module

This module provides direct HTTP client functionality for Jira's v3 REST API,
offering enhanced functionality and security for operations that require the latest API features.
"""

import json
from typing import Any, Dict, Optional

import requests


class JiraV3APIClient:
    """Client for making direct requests to Jira's v3 REST API"""

    def __init__(
        self,
        server_url: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        token: Optional[str] = None,
    ):
        """Initialize the v3 API client

        Args:
            server_url: Jira server URL
            username: Username for authentication
            password: Password for basic auth
            token: API token for auth
        """
        self.server_url = server_url
        self.username = username
        self.password = password
        self.token = token

    def _make_v3_api_request(
        self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Sends an authenticated HTTP request to a Jira v3 REST API endpoint and returns the parsed JSON response.
        
        Args:
            method: The HTTP method to use (e.g., 'GET', 'POST', 'PUT', 'DELETE').
            endpoint: The Jira v3 API endpoint path (e.g., '/project').
            data: Optional dictionary representing the JSON request body.
        
        Returns:
            The JSON-decoded response from the Jira API.
        
        Raises:
            ValueError: If the server URL is not configured, the request fails, or the API returns an error response.
        """
        if not self.server_url:
            raise ValueError("Server URL not configured")

        # Construct the full URL
        url = f"{self.server_url.rstrip('/')}/rest/api/3{endpoint}"

        # Prepare headers
        headers = {"Accept": "application/json", "Content-Type": "application/json"}

        # Set up authentication
        auth = None
        if self.username and (self.password or self.token):
            # Use basic auth (works for both username/password and username/token)
            auth = (self.username, self.password or self.token)
        elif self.token:
            # Use bearer token auth
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                auth=auth,
                json=data,
                timeout=30,
            )

            # Check for HTTP errors
            if response.status_code >= 400:
                error_details = ""
                try:
                    error_json = response.json()
                    if "errorMessages" in error_json:
                        error_details = "; ".join(error_json["errorMessages"])
                    elif "message" in error_json:
                        error_details = error_json["message"]
                except:
                    error_details = (
                        response.text[:200] if response.text else "No error details"
                    )

                raise ValueError(f"HTTP {response.status_code}: {error_details}\nRequest payload: {json.dumps(data)}\nResponse body: {response.text}")

            response_data: Dict[str, Any] = response.json()
            return response_data

        except requests.exceptions.RequestException as e:
            raise ValueError(f"Request failed: {str(e)}")
        except ValueError:
            # Re-raise ValueError exceptions (including HTTP errors)
            raise
        except Exception as e:
            raise ValueError(f"Unexpected error in API request: {str(e)}")

    def create_project(
        self,
        key: str,
        name: Optional[str] = None,
        assignee: Optional[str] = None,
        ptype: str = None,
        template_name: Optional[str] = None,
        avatarId: Optional[int] = None,
        issueSecurityScheme: Optional[int] = None,
        permissionScheme: Optional[int] = None,
        projectCategory: Optional[int] = None,
        notificationScheme: Optional[int] = None,
        categoryId: Optional[int] = None,
        url: str = None,
    ) -> Dict[str, Any]:
        """
        Creates a new Jira project using the v3 REST API.
        
        Requires a project key and the Atlassian accountId of the project lead (`assignee`). The v3 API mandates that `leadAccountId` is always provided, regardless of default project lead settings or UI behavior. Additional project attributes such as name, type, template, avatar, schemes, category, and documentation URL can be specified.
        
        Args:
            key: The unique project key (required).
            name: The project name. Defaults to the key if not provided.
            assignee: Atlassian accountId of the project lead (required by v3 API).
            ptype: Project type key (e.g., 'software', 'business', 'service_desk').
            template_name: Project template key for template-based creation.
            avatarId: ID of the avatar to assign to the project.
            issueSecurityScheme: ID of the issue security scheme.
            permissionScheme: ID of the permission scheme.
            projectCategory: ID of the project category.
            notificationScheme: ID of the notification scheme.
            categoryId: Alternative to projectCategory; preferred for v3 API.
            url: URL for project information or documentation.
        
        Returns:
            A dictionary containing details of the created project as returned by Jira.
        
        Raises:
            ValueError: If required parameters are missing or project creation fails.
        """
        if not key:
            raise ValueError("Project key is required")

        try:
            # Build the v3 API request payload
            payload = {"key": key, "name": name or key}

            # Map project type to projectTypeKey
            if ptype is not None:
                payload["projectTypeKey"] = ptype

            # Map template_name to projectTemplateKey
            if template_name is not None:
                payload["projectTemplateKey"] = template_name

            # Map assignee to leadAccountId and set assigneeType to PROJECT_LEAD
            if assignee is not None:
                payload["leadAccountId"] = assignee
                payload["assigneeType"] = "PROJECT_LEAD"

            # Add optional numeric parameters
            if avatarId is not None:
                payload["avatarId"] = avatarId
            if issueSecurityScheme is not None:
                payload["issueSecurityScheme"] = issueSecurityScheme
            if permissionScheme is not None:
                payload["permissionScheme"] = permissionScheme
            if notificationScheme is not None:
                payload["notificationScheme"] = notificationScheme

            # Handle categoryId (prefer categoryId over projectCategory for v3 API)
            if categoryId is not None:
                payload["categoryId"] = categoryId
            elif projectCategory is not None:
                payload["categoryId"] = projectCategory

            # Add URL if provided (only include when non-empty)
            if url:
                payload["url"] = url



            print(
                f"Creating project with v3 API payload: {json.dumps(payload, indent=2)}"
            )

            # Make the v3 API request
            response_data = self._make_v3_api_request("POST", "/project", payload)

            print(f"Project creation response: {json.dumps(response_data, indent=2)}")

            return response_data

        except Exception as e:
            error_msg = str(e)
            print(f"Error creating project with v3 API: {error_msg}")
            raise ValueError(f"Error creating project: {error_msg}")
