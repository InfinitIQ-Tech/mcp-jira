"""Test cases for search_issues V3 API client and server integration"""

import asyncio
from unittest.mock import Mock, patch, AsyncMock
import pytest

from src.mcp_server_jira.jira_v3_api import JiraV3APIClient
from src.mcp_server_jira.server import JiraServer, JiraIssueResult


class TestSearchIssuesV3API:
    """Test suite for search_issues V3 API client"""

    @pytest.mark.asyncio
    async def test_v3_api_search_issues_success(self):
        """Test successful search issues request with V3 API"""
        # Mock successful search response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "issues": [
                {
                    "key": "PROJ-123",
                    "fields": {
                        "summary": "Test issue summary",
                        "description": "Test issue description",
                        "status": {"name": "Open"},
                        "assignee": {"displayName": "John Doe"},
                        "reporter": {"displayName": "Jane Smith"},
                        "created": "2023-01-01T00:00:00.000+0000",
                        "updated": "2023-01-02T00:00:00.000+0000"
                    }
                },
                {
                    "key": "PROJ-124",
                    "fields": {
                        "summary": "Another test issue",
                        "description": "Another description",
                        "status": {"name": "In Progress"},
                        "assignee": None,
                        "reporter": {"displayName": "Bob Wilson"},
                        "created": "2023-01-03T00:00:00.000+0000",
                        "updated": "2023-01-04T00:00:00.000+0000"
                    }
                }
            ],
            "startAt": 0,
            "maxResults": 50,
            "total": 2,
            "isLast": True
        }
        mock_response.text = ""
        mock_response.raise_for_status.return_value = None

        # Mock httpx client
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response

        client = JiraV3APIClient(
            server_url="https://test.atlassian.net",
            username="testuser",
            token="testtoken"
        )
        
        # Replace the client instance
        client.client = mock_client

        result = await client.search_issues(
            jql="project = PROJ",
            max_results=10
        )

        # Verify the request was made correctly
        mock_client.request.assert_called_once()
        call_args = mock_client.request.call_args
        
        assert call_args[1]["method"] == "GET"
        assert call_args[1]["url"] == "https://test.atlassian.net/rest/api/3/search/jql"
        assert call_args[1]["params"]["jql"] == "project = PROJ"
        assert call_args[1]["params"]["maxResults"] == 10

        # Verify response
        assert result["total"] == 2
        assert len(result["issues"]) == 2
        assert result["issues"][0]["key"] == "PROJ-123"

    @pytest.mark.asyncio
    async def test_v3_api_search_issues_with_parameters(self):
        """Test search issues with optional parameters"""
        # Mock successful search response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "issues": [],
            "startAt": 0,
            "maxResults": 25,
            "total": 0,
            "isLast": True
        }
        mock_response.text = ""
        mock_response.raise_for_status.return_value = None

        # Mock httpx client
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response

        client = JiraV3APIClient(
            server_url="https://test.atlassian.net",
            username="testuser",
            token="testtoken"
        )
        
        # Replace the client instance
        client.client = mock_client

        result = await client.search_issues(
            jql="project = PROJ AND status = Open",
            start_at=10,
            max_results=25,
            fields="summary,status,assignee",
            expand="changelog"
        )

        # Verify the request was made correctly
        mock_client.request.assert_called_once()
        call_args = mock_client.request.call_args
        
        assert call_args[1]["method"] == "GET"
        assert call_args[1]["url"] == "https://test.atlassian.net/rest/api/3/search/jql"
        params = call_args[1]["params"]
        assert params["jql"] == "project = PROJ AND status = Open"
        assert params["startAt"] == 10
        assert params["maxResults"] == 25
        assert params["fields"] == "summary,status,assignee"
        assert params["expand"] == "changelog"

    @pytest.mark.asyncio
    async def test_v3_api_search_issues_missing_jql(self):
        """Test search issues with missing JQL parameter"""
        client = JiraV3APIClient(
            server_url="https://test.atlassian.net",
            username="testuser",
            token="testtoken"
        )

        with pytest.raises(ValueError, match="jql parameter is required"):
            await client.search_issues("")

    @pytest.mark.asyncio
    async def test_v3_api_search_issues_api_error(self):
        """Test search issues with API error response"""
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.reason_phrase = "Bad Request"
        mock_response.json.return_value = {"errorMessages": ["Invalid JQL"]}
        
        from httpx import HTTPStatusError, Request, Response
        mock_request = Mock(spec=Request)
        mock_request.url = "https://test.atlassian.net/rest/api/3/search/jql"
        
        # Mock httpx client
        mock_client = AsyncMock()
        mock_client.request.side_effect = HTTPStatusError(
            "400 Bad Request", request=mock_request, response=mock_response
        )

        client = JiraV3APIClient(
            server_url="https://test.atlassian.net",
            username="testuser", 
            token="testtoken"
        )
        
        # Replace the client instance
        client.client = mock_client

        with pytest.raises(ValueError, match="Jira API returned an error: 400"):
            await client.search_issues(jql="invalid jql syntax")


class TestSearchIssuesJiraServer:
    """Test suite for search_issues in JiraServer class"""

    @pytest.mark.asyncio
    async def test_server_search_issues_success(self):
        """Test JiraServer search_issues method with successful V3 API response"""
        # Mock V3 API response
        mock_v3_response = {
            "issues": [
                {
                    "key": "TEST-1",
                    "fields": {
                        "summary": "Test Summary",
                        "description": "Test Description",
                        "status": {"name": "Open"},
                        "assignee": {"displayName": "Test User"},
                        "reporter": {"displayName": "Reporter User"},
                        "created": "2023-01-01T00:00:00.000+0000",
                        "updated": "2023-01-02T00:00:00.000+0000"
                    }
                }
            ]
        }

        # Mock V3 API client
        mock_v3_client = AsyncMock()
        mock_v3_client.search_issues.return_value = mock_v3_response

        # Create JiraServer instance and mock the V3 client
        server = JiraServer()
        server.server_url = "https://test.atlassian.net"
        server.username = "testuser"
        server.token = "testtoken"
        
        with patch.object(server, '_get_v3_api_client', return_value=mock_v3_client):
            result = await server.search_jira_issues("project = TEST", max_results=10)

        # Verify the result
        assert len(result) == 1
        assert isinstance(result[0], JiraIssueResult)
        assert result[0].key == "TEST-1"
        assert result[0].summary == "Test Summary"
        assert result[0].description == "Test Description"
        assert result[0].status == "Open"
        assert result[0].assignee == "Test User"
        assert result[0].reporter == "Reporter User"
        assert result[0].created == "2023-01-01T00:00:00.000+0000"
        assert result[0].updated == "2023-01-02T00:00:00.000+0000"

        # Verify V3 client was called correctly
        mock_v3_client.search_issues.assert_called_once_with(
            jql="project = TEST", max_results=10
        )

    @pytest.mark.asyncio
    async def test_server_search_issues_handles_missing_fields(self):
        """Test JiraServer search_issues method handles missing optional fields gracefully"""
        # Mock V3 API response with minimal data
        mock_v3_response = {
            "issues": [
                {
                    "key": "TEST-2",
                    "fields": {
                        "summary": "Basic Summary",
                        # Missing description, status, assignee, reporter, etc.
                    }
                }
            ]
        }

        # Mock V3 API client
        mock_v3_client = AsyncMock()
        mock_v3_client.search_issues.return_value = mock_v3_response

        # Create JiraServer instance and mock the V3 client
        server = JiraServer()
        server.server_url = "https://test.atlassian.net"
        server.username = "testuser"
        server.token = "testtoken"
        
        with patch.object(server, '_get_v3_api_client', return_value=mock_v3_client):
            result = await server.search_jira_issues("project = TEST")

        # Verify the result handles missing fields gracefully
        assert len(result) == 1
        assert result[0].key == "TEST-2"
        assert result[0].summary == "Basic Summary"
        assert result[0].description == ""  # Should default to empty string for missing description
        assert result[0].status is None      # Should be None for missing status
        assert result[0].assignee is None    # Should be None for missing assignee
        assert result[0].reporter is None    # Should be None for missing reporter

    @pytest.mark.asyncio
    async def test_server_search_issues_api_error(self):
        """Test JiraServer search_issues method with API error"""
        # Mock V3 API client that raises an error
        mock_v3_client = AsyncMock()
        mock_v3_client.search_issues.side_effect = ValueError("API connection failed")

        # Create JiraServer instance and mock the V3 client
        server = JiraServer()
        server.server_url = "https://test.atlassian.net"
        server.username = "testuser"
        server.token = "testtoken"
        
        with patch.object(server, '_get_v3_api_client', return_value=mock_v3_client):
            with pytest.raises(ValueError, match="Failed to search issues"):
                await server.search_jira_issues("project = TEST")