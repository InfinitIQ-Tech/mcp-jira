"""
Jira v3 REST API client module

This module provides direct HTTP client functionality for Jira's v3 REST API,
offering enhanced functionality and security for operations that require the latest API features.
"""

import json
import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger("JiraMCPLogger")  # Get the same logger instance


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
        self.server_url = server_url.rstrip("/")
        self.username = username
        self.auth_token = token or password

        if not self.username or not self.auth_token:
            raise ValueError(
                "Jira username and an API token (or password) are required for v3 API."
            )

        self.client = httpx.AsyncClient(
            auth=(self.username, self.auth_token),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=30.0,
            follow_redirects=True,
        )

    async def _make_v3_api_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
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
            logger.info(
                f"COMPLETED httpx.client.request for {url}. Status: {response.status_code}"
            )
            logger.debug(f"Raw response text (first 500 chars): {str(response.text)[:500]}")

            response.raise_for_status()

            if response.status_code == 204:
                return {}

            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP Status Error for {e.request.url!r}: {e.response.status_code}",
                exc_info=True,
            )
            error_details = f"Jira API returned an error: {e.response.status_code} {e.response.reason_phrase}."
            raise ValueError(error_details)

        except httpx.RequestError as e:
            logger.error(f"Request Error for {e.request.url!r}", exc_info=True)
            raise ValueError(f"A network error occurred while connecting to Jira: {e}")
        except Exception as e:
            logger.critical(
                "An unexpected error occurred in _make_v3_api_request", exc_info=True
            )
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
            raise ValueError(
                "Parameter 'assignee' (leadAccountId) is required by the Jira v3 API"
            )

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
        response_data = await self._make_v3_api_request(
            "POST", "/project", data=payload
        )
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
        print(
            f"Fetching projects with v3 API endpoint: {endpoint} with params: {params}"
        )
        response_data = await self._make_v3_api_request("GET", endpoint, params=params)
        print(f"Projects API response: {json.dumps(response_data, indent=2)}")
        return response_data

    async def get_transitions(
        self,
        issue_id_or_key: str,
        expand: Optional[str] = None,
        transition_id: Optional[str] = None,
        skip_remote_only_condition: Optional[bool] = None,
        include_unavailable_transitions: Optional[bool] = None,
        sort_by_ops_bar_and_status: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Get available transitions for an issue using the v3 REST API.

        Returns either all transitions or a transition that can be performed by the user
        on an issue, based on the issue's status.

        Args:
            issue_id_or_key: Issue ID or key (required)
            expand: Expand additional transition fields in response
            transition_id: Get only the transition matching this ID
            skip_remote_only_condition: Skip remote-only conditions check
            include_unavailable_transitions: Include transitions that can't be performed
            sort_by_ops_bar_and_status: Sort transitions by operations bar and status

        Returns:
            Dictionary containing the transitions response with transition details

        Raises:
            ValueError: If the API request fails
        """
        if not issue_id_or_key:
            raise ValueError("issue_id_or_key is required")

        params = {
            "expand": expand,
            "transitionId": transition_id,
            "skipRemoteOnlyCondition": skip_remote_only_condition,
            "includeUnavailableTransitions": include_unavailable_transitions,
            "sortByOpsBarAndStatus": sort_by_ops_bar_and_status,
        }

        params = {k: v for k, v in params.items() if v is not None}

        endpoint = f"/issue/{issue_id_or_key}/transitions"
        logger.debug(
            f"Fetching transitions with v3 API endpoint: {endpoint} with params: {params}"
        )
        response_data = await self._make_v3_api_request("GET", endpoint, params=params)
        logger.debug(f"Transitions API response: {json.dumps(response_data, indent=2)}")
        return response_data

    async def transition_issue(
        self,
        issue_id_or_key: str,
        transition_id: str,
        fields: Optional[Dict[str, Any]] = None,
        comment: Optional[str] = None,
        history_metadata: Optional[Dict[str, Any]] = None,
        properties: Optional[list] = None,
    ) -> Dict[str, Any]:
        """
        Transition an issue using the v3 REST API.

        Performs an issue transition and, if the transition has a screen,
        updates the fields from the transition screen.

        Args:
            issue_id_or_key: Issue ID or key (required)
            transition_id: ID of the transition to perform (required)
            fields: Dict containing field names and values to update during transition
            comment: Simple string comment to add during transition
            history_metadata: Optional history metadata for the transition
            properties: Optional list of properties to set

        Returns:
            Empty dictionary on success (204 No Content response)

        Raises:
            ValueError: If required parameters are missing or transition fails
        """
        if not issue_id_or_key:
            raise ValueError("issue_id_or_key is required")

        if not transition_id:
            raise ValueError("transition_id is required")

        # Build the request payload
        payload = {"transition": {"id": transition_id}}

        # Add fields if provided
        if fields:
            payload["fields"] = fields

        # Add comment if provided - convert simple string to ADF format
        if comment:
            payload["update"] = {
                "comment": [
                    {
                        "add": {
                            "body": {
                                "type": "doc",
                                "version": 1,
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [{"type": "text", "text": comment}],
                                    }
                                ],
                            }
                        }
                    }
                ]
            }

        # Add optional metadata
        if history_metadata:
            payload["historyMetadata"] = history_metadata

        if properties:
            payload["properties"] = properties

        endpoint = f"/issue/{issue_id_or_key}/transitions"
        logger.debug(f"Transitioning issue with v3 API endpoint: {endpoint}")
        logger.debug(f"Transition payload: {json.dumps(payload, indent=2)}")

        response_data = await self._make_v3_api_request("POST", endpoint, data=payload)
        logger.debug(f"Transition response: {response_data}")
        return response_data

    async def get_issue_types(self) -> Dict[str, Any]:
        """
        Get all issue types for user using the v3 REST API.

        Returns all issue types. This operation can be accessed anonymously.

        Permissions required: Issue types are only returned as follows:
        - if the user has the Administer Jira global permission, all issue types are returned.
        - if the user has the Browse projects project permission for one or more projects,
          the issue types associated with the projects the user has permission to browse are returned.
        - if the user is anonymous then they will be able to access projects with the Browse projects for anonymous users
        - if the user authentication is incorrect they will fall back to anonymous

        Returns:
            List of issue type dictionaries with fields like:
            - avatarId: Avatar ID for the issue type
            - description: Description of the issue type
            - hierarchyLevel: Hierarchy level
            - iconUrl: URL of the issue type icon
            - id: Issue type ID
            - name: Issue type name
            - self: REST API URL for the issue type
            - subtask: Whether this is a subtask type

        Raises:
            ValueError: If the API request fails
        """
        endpoint = "/issuetype"
        logger.debug(f"Fetching issue types with v3 API endpoint: {endpoint}")
        response_data = await self._make_v3_api_request("GET", endpoint)
        logger.debug(f"Issue types API response: {json.dumps(response_data, indent=2)}")
        return response_data

    async def create_issue(
        self,
        fields: Dict[str, Any],
        update: Optional[Dict[str, Any]] = None,
        history_metadata: Optional[Dict[str, Any]] = None,
        properties: Optional[list] = None,
        transition: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create an issue using the v3 REST API.

        Creates an issue or, where the option to create subtasks is enabled in Jira, a subtask.
        A transition may be applied, to move the issue or subtask to a workflow step other than
        the default start step, and issue properties set.

        Args:
            fields: Dict containing field names and values (required).
                   Must include project, summary, description, and issuetype.
            update: Dict containing update operations for fields
            history_metadata: Optional history metadata for the issue creation
            properties: Optional list of properties to set
            transition: Optional transition to apply after creation

        Returns:
            Dictionary containing the created issue details:
            - id: Issue ID
            - key: Issue key
            - self: URL to the created issue
            - transition: Transition result if applied

        Raises:
            ValueError: If required parameters are missing or creation fails
        """
        if not fields:
            raise ValueError("fields is required")

        # Build the request payload
        payload = {"fields": fields}

        # Add optional parameters
        if update:
            payload["update"] = update

        if history_metadata:
            payload["historyMetadata"] = history_metadata

        if properties:
            payload["properties"] = properties

        if transition:
            payload["transition"] = transition

        endpoint = "/issue"
        logger.debug(f"Creating issue with v3 API endpoint: {endpoint}")
        logger.debug(f"Create issue payload: {json.dumps(payload, indent=2)}")

        response_data = await self._make_v3_api_request("POST", endpoint, data=payload)
        logger.debug(f"Create issue response: {response_data}")
        return response_data

    async def search_issues(
        self,
        jql: str,
        start_at: int = 0,
        max_results: int = 50,
        fields: Optional[str] = None,
        expand: Optional[str] = None,
        properties: Optional[list] = None,
        fields_by_keys: Optional[bool] = None,
        fail_fast: Optional[bool] = None,
        reconcile_issues: Optional[list] = None,
    ) -> Dict[str, Any]:
        """
        Search for issues using JQL enhanced search (GET) via v3 REST API.
        
        Searches for issues using JQL. Recent updates might not be immediately visible 
        in the returned search results. If you need read-after-write consistency, 
        you can utilize the reconcileIssues parameter to ensure stronger consistency assurances. 
        This operation can be accessed anonymously.

        Args:
            jql: JQL query string
            start_at: Index of the first issue to return (default: 0)
            max_results: Maximum number of results to return (default: 50)
            fields: Comma-separated list of fields to include in response
            expand: Use expand to include additional information about issues
            properties: List of issue properties to include in response
            fields_by_keys: Reference fields by their key (rather than ID)
            fail_fast: Fail fast when JQL query validation fails
            reconcile_issues: List of issue IDs to reconcile for read-after-write consistency

        Returns:
            Dictionary containing search results with:
            - issues: List of issue dictionaries
            - isLast: Boolean indicating if this is the last page
            - startAt: Starting index of results
            - maxResults: Maximum results per page
            - total: Total number of issues matching the query

        Raises:
            ValueError: If the API request fails or JQL is invalid
        """
        if not jql:
            raise ValueError("jql parameter is required")

        # Build query parameters
        params = {
            "jql": jql,
            "startAt": start_at,
            "maxResults": max_results,
        }

        # Add optional parameters if provided
        params["fields"] = fields if fields is not None else "*all"
        if expand:
            params["expand"] = expand
        if properties:
            params["properties"] = properties
        if fields_by_keys is not None:
            params["fieldsByKeys"] = fields_by_keys
        if fail_fast is not None:
            params["failFast"] = fail_fast
        if reconcile_issues:
            params["reconcileIssues"] = reconcile_issues

        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}

        endpoint = "/search/jql"
        logger.debug(f"Searching issues with v3 API endpoint: {endpoint}")
        logger.debug(f"Search params: {params}")
        
        response_data = await self._make_v3_api_request("GET", endpoint, params=params)
        logger.debug(f"Search issues API response: {json.dumps(response_data, indent=2)}")
        return response_data

    async def bulk_create_issues(
        self, 
        issue_updates: list
    ) -> Dict[str, Any]:
        """
        Bulk create issues using the v3 REST API.

        Creates up to 50 issues and, where the option to create subtasks is enabled in Jira,
        subtasks. Transitions may be applied, to move the issues or subtasks to a workflow
        step other than the default start step, and issue properties set.

        Args:
            issue_updates: List of issue creation specifications. Each item should contain
                          'fields' dict with issue fields, and optionally 'update' dict
                          for additional operations during creation.

        Returns:
            Dict containing:
            - issues: List of successfully created issues with their details
            - errors: List of errors for failed issue creations

        Raises:
            ValueError: If required parameters are missing or bulk creation fails
        """
        if not issue_updates:
            raise ValueError("issue_updates list cannot be empty")

        if len(issue_updates) > 50:
            raise ValueError("Cannot create more than 50 issues in a single bulk operation")

        # Build the request payload for v3 API
        payload = {"issueUpdates": issue_updates}

        endpoint = "/issue/bulk"
        logger.debug(f"Bulk creating issues with v3 API endpoint: {endpoint}")
        logger.debug(f"Payload: {json.dumps(payload, indent=2)}")

        response_data = await self._make_v3_api_request("POST", endpoint, data=payload)
        logger.debug(f"Bulk create response: {json.dumps(response_data, indent=2)}")

        return response_data
