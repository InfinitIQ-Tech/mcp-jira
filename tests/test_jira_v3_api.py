# pylint: disable=import-error, protected-access
"""
Tests for the Jira v3 API client functionality.
"""


from unittest.mock import Mock, patch

import pytest  # pylint: disable=import-error

from src.mcp_server_jira.jira_v3_api import JiraV3APIClient


class TestJiraV3APIClient:
    """Test suite for JiraV3APIClient"""

    def test_init_with_username_password(self):
        """Test initialization with username and password"""
        client = JiraV3APIClient(
            server_url="https://test.atlassian.net",
            username="testuser",
            password="testpass",
        )
        assert client.server_url == "https://test.atlassian.net"
        assert client.username == "testuser"
        assert client.password == "testpass"
        assert client.token is None

    def test_init_with_token(self):
        """Test initialization with token only"""
        client = JiraV3APIClient(
            server_url="https://test.atlassian.net", token="test-token"
        )
        assert client.server_url == "https://test.atlassian.net"
        assert client.username is None
        assert client.password is None
        assert client.token == "test-token"

    @patch("src.mcp_server_jira.jira_v3_api.requests.request")
    def test_make_v3_api_request_success(self, mock_request):
        """Test successful API request"""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"key": "TEST", "name": "Test Project"}
        mock_request.return_value = mock_response

        client = JiraV3APIClient(
            server_url="https://test.atlassian.net",
            username="testuser",
            token="testtoken",
        )

        result = client._make_v3_api_request("POST", "/project", {"test": "data"})

        assert result == {"key": "TEST", "name": "Test Project"}
        mock_request.assert_called_once()

    @patch("src.mcp_server_jira.jira_v3_api.requests.request")
    def test_make_v3_api_request_error(self, mock_request):
        """Test API request with error response"""
        # Setup mock error response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"errorMessages": ["Bad request"]}
        mock_request.return_value = mock_response

        client = JiraV3APIClient(
            server_url="https://test.atlassian.net",
            username="testuser",
            token="testtoken",
        )

        with pytest.raises(ValueError, match="HTTP 400"):
            client._make_v3_api_request("POST", "/project", {"test": "data"})

    @patch("src.mcp_server_jira.jira_v3_api.requests.request")
    def test_create_project_success(self, mock_request):
        """Test successful project creation"""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "self": "https://test.atlassian.net/rest/api/3/project/10000",
            "id": "10000",
            "key": "TEST",
            "name": "Test Project",
        }
        mock_request.return_value = mock_response

        client = JiraV3APIClient(
            server_url="https://test.atlassian.net",
            username="testuser",
            token="testtoken",
        )

        result = client.create_project(
            key="TEST", name="Test Project", ptype="software"
        )

        assert result["key"] == "TEST"
        assert result["name"] == "Test Project"
        mock_request.assert_called_once()

        # Verify the request was made with correct data
        call_args = mock_request.call_args
        assert call_args[1]["method"] == "POST"
        assert "/rest/api/3/project" in call_args[1]["url"]

        # Check the request body
        request_data = call_args[1]["json"]
        assert request_data["key"] == "TEST"
        assert request_data["name"] == "Test Project"
        assert request_data["projectTypeKey"] == "software"
        assert request_data["assigneeType"] == "PROJECT_LEAD"

    @patch("src.mcp_server_jira.jira_v3_api.requests.request")
    def test_create_project_with_template(self, mock_request):
        """Test project creation with template"""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "self": "https://test.atlassian.net/rest/api/3/project/10000",
            "id": "10000",
            "key": "TEMP",
            "name": "Template Project",
        }
        mock_request.return_value = mock_response

        client = JiraV3APIClient(
            server_url="https://test.atlassian.net",
            username="testuser",
            token="testtoken",
        )

        result = client.create_project(
            key="TEMP",
            name="Template Project",
            ptype="business",
            template_name="com.atlassian.jira-core-project-templates:jira-core-project-management",
            assignee="user123",
        )

        assert result["key"] == "TEMP"
        mock_request.assert_called_once()

        # Verify the request data includes template information
        call_args = mock_request.call_args
        request_data = call_args[1]["json"]
        assert (
            request_data["projectTemplateKey"]
            == "com.atlassian.jira-core-project-templates:jira-core-project-management"
        )
        assert request_data["leadAccountId"] == "user123"
        assert request_data["projectTypeKey"] == "business"

    def test_create_project_missing_key(self):
        """Test project creation with missing key"""
        client = JiraV3APIClient(
            server_url="https://test.atlassian.net",
            username="testuser",
            token="testtoken",
        )

        with pytest.raises(ValueError, match="Project key is required"):
            client.create_project(key="")

    def test_create_project_missing_assignee(self):
        """Test project creation with missing assignee"""
        client = JiraV3APIClient(
            server_url="https://test.atlassian.net",
            username="testuser",
            token="testtoken",
        )

        with pytest.raises(ValueError, match="Parameter 'assignee'"):
            client.create_project(key="TEST")

    @patch("src.mcp_server_jira.jira_v3_api.requests.request")
    def test_authentication_username_token(self, mock_request):
        """Test authentication with username and token"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"test": "data"}
        mock_request.return_value = mock_response

        client = JiraV3APIClient(
            server_url="https://test.atlassian.net",
            username="testuser",
            token="testtoken",
        )

        client._make_v3_api_request("GET", "/test")

        call_args = mock_request.call_args
        auth = call_args[1]["auth"]
        assert auth == ("testuser", "testtoken")

    @patch("src.mcp_server_jira.jira_v3_api.requests.request")
    def test_authentication_token_only(self, mock_request):
        """Test authentication with token only"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"test": "data"}
        mock_request.return_value = mock_response

        client = JiraV3APIClient(
            server_url="https://test.atlassian.net", token="testtoken"
        )

        client._make_v3_api_request("GET", "/test")

        call_args = mock_request.call_args
        headers = call_args[1]["headers"]
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer testtoken"

    @patch("src.mcp_server_jira.jira_v3_api.requests.request")
    def test_get_projects_success(self, mock_request):
        """Test successful get projects request"""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "startAt": 0,
            "maxResults": 50,
            "total": 2,
            "isLast": True,
            "values": [
                {
                    "id": "10000",
                    "key": "TEST",
                    "name": "Test Project",
                    "lead": {"displayName": "John Doe"}
                },
                {
                    "id": "10001",
                    "key": "DEMO", 
                    "name": "Demo Project",
                    "lead": {"displayName": "Jane Smith"}
                }
            ]
        }
        mock_request.return_value = mock_response

        client = JiraV3APIClient(
            server_url="https://test.atlassian.net",
            username="testuser",
            token="testtoken",
        )

        result = client.get_projects()

        assert result["total"] == 2
        assert len(result["values"]) == 2
        assert result["values"][0]["key"] == "TEST"
        assert result["values"][1]["key"] == "DEMO"
        mock_request.assert_called_once()

        # Verify the request was made to the correct endpoint
        call_args = mock_request.call_args
        assert call_args[1]["method"] == "GET"
        assert "/rest/api/3/project/search" in call_args[1]["url"]

    @patch("src.mcp_server_jira.jira_v3_api.requests.request")
    def test_get_projects_with_parameters(self, mock_request):
        """Test get projects with query parameters"""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "startAt": 10,
            "maxResults": 20,
            "total": 50,
            "isLast": False,
            "values": []
        }
        mock_request.return_value = mock_response

        client = JiraV3APIClient(
            server_url="https://test.atlassian.net",
            username="testuser",
            token="testtoken",
        )

        result = client.get_projects(
            start_at=10,
            max_results=20,
            order_by="name",
            query="test",
            keys=["PROJ1", "PROJ2"]
        )

        assert result["startAt"] == 10
        assert result["maxResults"] == 20
        mock_request.assert_called_once()

        # Verify the request URL includes query parameters
        call_args = mock_request.call_args
        url = call_args[1]["url"]
        assert "startAt=10" in url
        assert "maxResults=20" in url
        assert "orderBy=name" in url
        assert "query=test" in url
        assert "keys=PROJ1,PROJ2" in url

    @patch("src.mcp_server_jira.jira_v3_api.requests.request")
    def test_get_projects_error(self, mock_request):
        """Test get projects with error response"""
        # Setup mock error response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"errorMessages": ["Unauthorized"]}
        mock_request.return_value = mock_response

        client = JiraV3APIClient(
            server_url="https://test.atlassian.net",
            username="testuser",
            token="testtoken",
        )

        with pytest.raises(ValueError, match="HTTP 401"):
            client.get_projects()

    @patch("src.mcp_server_jira.jira_v3_api.httpx.AsyncClient")
    async def test_get_transitions_success(self, mock_async_client):
        """Test successful get transitions request"""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "transitions": [
                {
                    "id": "2",
                    "name": "Close Issue",
                    "to": {
                        "id": "10000",
                        "name": "Done",
                        "description": "Issue is done"
                    },
                    "hasScreen": False,
                    "isAvailable": True,
                    "isConditional": False,
                    "isGlobal": False,
                    "isInitial": False
                },
                {
                    "id": "711",
                    "name": "QA Review",
                    "to": {
                        "id": "5",
                        "name": "In Review",
                        "description": "Issue is under review"
                    },
                    "hasScreen": True,
                    "isAvailable": True,
                    "isConditional": False,
                    "isGlobal": False,
                    "isInitial": False
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        
        # Setup mock client
        mock_client_instance = Mock()
        mock_client_instance.request.return_value = mock_response
        mock_async_client.return_value = mock_client_instance

        client = JiraV3APIClient(
            server_url="https://test.atlassian.net",
            username="testuser",
            token="testtoken",
        )

        result = await client.get_transitions("PROJ-123")

        assert "transitions" in result
        assert len(result["transitions"]) == 2
        assert result["transitions"][0]["id"] == "2"
        assert result["transitions"][0]["name"] == "Close Issue"
        assert result["transitions"][1]["id"] == "711"
        assert result["transitions"][1]["name"] == "QA Review"
        
        # Verify the request was made with correct parameters
        mock_client_instance.request.assert_called_once()
        call_args = mock_client_instance.request.call_args
        assert call_args[1]["method"] == "GET"
        assert "/rest/api/3/issue/PROJ-123/transitions" in call_args[1]["url"]

    @patch("src.mcp_server_jira.jira_v3_api.httpx.AsyncClient")
    async def test_get_transitions_with_parameters(self, mock_async_client):
        """Test get transitions with query parameters"""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"transitions": []}
        mock_response.raise_for_status.return_value = None
        
        # Setup mock client
        mock_client_instance = Mock()
        mock_client_instance.request.return_value = mock_response
        mock_async_client.return_value = mock_client_instance

        client = JiraV3APIClient(
            server_url="https://test.atlassian.net",
            username="testuser",
            token="testtoken",
        )

        await client.get_transitions(
            issue_id_or_key="PROJ-123",
            expand="transitions.fields",
            transition_id="2",
            skip_remote_only_condition=True,
            include_unavailable_transitions=False,
            sort_by_ops_bar_and_status=True
        )

        # Verify the request was made with correct parameters
        mock_client_instance.request.assert_called_once()
        call_args = mock_client_instance.request.call_args
        assert call_args[1]["method"] == "GET"
        
        params = call_args[1]["params"]
        assert params["expand"] == "transitions.fields"
        assert params["transitionId"] == "2"
        assert params["skipRemoteOnlyCondition"] is True
        assert params["includeUnavailableTransitions"] is False
        assert params["sortByOpsBarAndStatus"] is True

    async def test_get_transitions_missing_issue_key(self):
        """Test get transitions with missing issue key"""
        client = JiraV3APIClient(
            server_url="https://test.atlassian.net",
            username="testuser",
            token="testtoken",
        )

        with pytest.raises(ValueError, match="issue_id_or_key is required"):
            await client.get_transitions("")
