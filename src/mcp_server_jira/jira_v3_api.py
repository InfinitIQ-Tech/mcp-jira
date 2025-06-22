"""
Jira v3 REST API client module

This module provides direct HTTP client functionality for Jira's v3 REST API,
offering enhanced functionality and security for operations that require the latest API features.
"""

import json
from typing import Any, Dict, Optional
import httpx

import logging
logger = logging.getLogger("JiraMCPLogger") # Get the same logger instance

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
        self.server_url = server_url.rstrip('/')
        self.username = username
        self.auth_token = token or password

        if not self.username or not self.auth_token:
            raise ValueError("Jira username and an API token (or password) are required for v3 API.")

        self.client = httpx.AsyncClient(
            auth=(self.username, self.auth_token),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=30.0,
            follow_redirects=True,
        )

    async def _make_v3_api_request(
        self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Sends an authenticated async HTTP request to a Jira v3 REST API endpoint.
        """
        url = f"{self.server_url}/rest/api/3{endpoint}"
        
        logger.debug(f"Attempting to make request: {method} {url}")
        logger.debug(f"Request params: {params}")
        logger.debug(f"Request JSON data: {data}")

        try:
            logger.info(f"AWAITING httpx.client.request for {method} {url}")
            response = await self.client.request(
                method=method.upper(),
                url=url,
                json=data,
                params=params,
            )
            logger.info(f"COMPLETED httpx.client.request for {url}. Status: {response.status_code}")
            logger.debug(f"Raw response text (first 500 chars): {response.text[:500]}")

            response.raise_for_status()
            
            if response.status_code == 204:
                return {}

            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP Status Error for {e.request.url!r}: {e.response.status_code}", exc_info=True)
            error_details = f"Jira API returned an error: {e.response.status_code} {e.response.reason_phrase}."
            raise ValueError(error_details)
        
        except httpx.RequestError as e:
            logger.error(f"Request Error for {e.request.url!r}", exc_info=True)
            raise ValueError(f"A network error occurred while connecting to Jira: {e}")
        except Exception as e:
            logger.critical("An unexpected error occurred in _make_v3_api_request", exc_info=True)
            raise

    async def create_project(
        self,
        key: str,
        assignee: str,
        name: Optional[str] = None,
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

        if not assignee:
            raise ValueError("Parameter 'assignee' (leadAccountId) is required by the Jira v3 API")

        payload = {
            "key": key,
            "name": name or key,
            "leadAccountId": assignee,
            "assigneeType": "PROJECT_LEAD",
            "projectTypeKey": ptype,
            "projectTemplateKey": template_name,
            "avatarId": avatarId,
            "issueSecurityScheme": issueSecurityScheme,
            "permissionScheme": permissionScheme,
            "notificationScheme": notificationScheme,
            "categoryId": categoryId or projectCategory,
            "url": url,
        }
        
        payload = {k: v for k, v in payload.items() if v is not None}
        
        print(f"Creating project with v3 API payload: {json.dumps(payload, indent=2)}")
        response_data = await self._make_v3_api_request("POST", "/project", data=payload)
        print(f"Project creation response: {json.dumps(response_data, indent=2)}")
        return response_data

    async def get_projects(
        self,
        start_at: int = 0,
        max_results: int = 50,
        order_by: Optional[str] = None,
        ids: Optional[list] = None,
        keys: Optional[list] = None,
        query: Optional[str] = None,
        type_key: Optional[str] = None,
        category_id: Optional[int] = None,
        action: Optional[str] = None,
        expand: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get projects paginated using the v3 REST API.
        
        Returns a paginated list of projects visible to the user using the 
        /rest/api/3/project/search endpoint.
        
        Args:
            start_at: The index of the first item to return (default: 0)
            max_results: The maximum number of items to return per page (default: 50)
            order_by: Order the results by a field:
                     - category: Order by project category
                     - issueCount: Order by total number of issues
                     - key: Order by project key  
                     - lastIssueUpdatedDate: Order by last issue update date
                     - name: Order by project name
                     - owner: Order by project lead
                     - archivedDate: Order by archived date
                     - deletedDate: Order by deleted date
            ids: List of project IDs to return
            keys: List of project keys to return
            query: Filter projects by query string
            type_key: Filter projects by type key
            category_id: Filter projects by category ID
            action: Filter by action permission (view, browse, edit)
            expand: Expand additional project fields in response
            
        Returns:
            Dictionary containing the paginated response with projects and pagination info
            
        Raises:
            ValueError: If the API request fails
        """
        params = {
            "startAt": start_at,
            "maxResults": max_results,
            "orderBy": order_by,
            "id": ids,
            "keys": keys,
            "query": query,
            "typeKey": type_key,
            "categoryId": category_id,
            "action": action,
            "expand": expand,
        }
        
        params = {k: v for k, v in params.items() if v is not None}
        
        endpoint = "/project/search"
        print(f"Fetching projects with v3 API endpoint: {endpoint} with params: {params}")
        response_data = await self._make_v3_api_request("GET", endpoint, params=params)
        print(f"Projects API response: {json.dumps(response_data, indent=2)}")
        return response_data