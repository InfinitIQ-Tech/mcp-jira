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
        assert isinstance(result, list)
        assert len(result) == 1
        issue = result[0]
        assert isinstance(issue, dict)
        assert issue["key"] == "TEST-1"
        assert issue["fields"]["summary"] == "Test Summary"
        assert issue["fields"]["description"] == "Test Description"
        assert issue["fields"]["status"]["name"] == "Open"
        assert issue["fields"]["assignee"]["displayName"] == "Test User"
        assert issue["fields"]["reporter"]["displayName"] == "Reporter User"
        assert issue["fields"]["created"] == "2023-01-01T00:00:00.000+0000"
        assert issue["fields"]["updated"] == "2023-01-02T00:00:00.000+0000"

        # Verify V3 client was called correctly
        mock_v3_client.search_issues.assert_called_once_with(
            jql="project = TEST", start_at=0, max_results=10
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
        assert isinstance(result, list)
        assert len(result) == 1
        issue = result[0]
        assert isinstance(issue, dict)
        assert issue["key"] == "TEST-2"
        assert issue["fields"]["summary"] == "Basic Summary"
        # Missing description, status, assignee, reporter should be absent or None
        assert issue["fields"].get("description") is None
        assert issue["fields"].get("status") is None
        assert issue["fields"].get("assignee") is None
        assert issue["fields"].get("reporter") is None

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

    @pytest.mark.asyncio
    async def test_server_search_issues_pagination(self):
        """Test JiraServer search_issues method handles pagination correctly"""
        # Mock V3 API responses for pagination
        # First page response
        page1_response = {
            "issues": [
                {
                    "key": "TEST-1",
                    "fields": {
                        "summary": "First Issue",
                        "description": "First Description",
                        "status": {"name": "Open"},
                        "assignee": {"displayName": "User 1"},
                        "reporter": {"displayName": "Reporter 1"},
                        "created": "2023-01-01T00:00:00.000+0000",
                        "updated": "2023-01-01T00:00:00.000+0000"
                    }
                },
                {
                    "key": "TEST-2",
                    "fields": {
                        "summary": "Second Issue",
                        "description": "Second Description",
                        "status": {"name": "In Progress"},
                        "assignee": {"displayName": "User 2"},
                        "reporter": {"displayName": "Reporter 2"},
                        "created": "2023-01-02T00:00:00.000+0000",
                        "updated": "2023-01-02T00:00:00.000+0000"
                    }
                }
            ],
            "startAt": 0,
            "maxResults": 2,
            "total": 5,
            "isLast": False
        }

        # Second page response
        page2_response = {
            "issues": [
                {
                    "key": "TEST-3",
                    "fields": {
                        "summary": "Third Issue",
                        "description": "Third Description",
                        "status": {"name": "Done"},
                        "assignee": {"displayName": "User 3"},
                        "reporter": {"displayName": "Reporter 3"},
                        "created": "2023-01-03T00:00:00.000+0000",
                        "updated": "2023-01-03T00:00:00.000+0000"
                    }
                },
                {
                    "key": "TEST-4",
                    "fields": {
                        "summary": "Fourth Issue",
                        "description": "Fourth Description",
                        "status": {"name": "Closed"},
                        "assignee": None,
                        "reporter": {"displayName": "Reporter 4"},
                        "created": "2023-01-04T00:00:00.000+0000",
                        "updated": "2023-01-04T00:00:00.000+0000"
                    }
                }
            ],
            "startAt": 2,
            "maxResults": 2,
            "total": 5,
            "isLast": False
        }

        # Third page response
        page3_response = {
            "issues": [
                {
                    "key": "TEST-5",
                    "fields": {
                        "summary": "Fifth Issue",
                        "description": "Fifth Description",
                        "status": {"name": "Open"},
                        "assignee": {"displayName": "User 5"},
                        "reporter": {"displayName": "Reporter 5"},
                        "created": "2023-01-05T00:00:00.000+0000",
                        "updated": "2023-01-05T00:00:00.000+0000"
                    }
                }
            ],
            "startAt": 4,
            "maxResults": 2,
            "total": 5,
            "isLast": True
        }

        # Mock V3 API client with side_effect to return different pages
        mock_v3_client = AsyncMock()
        mock_v3_client.search_issues.side_effect = [page1_response, page2_response, page3_response]

        # Create JiraServer instance and mock the V3 client
        server = JiraServer()
        server.server_url = "https://test.atlassian.net"
        server.username = "testuser"
        server.token = "testtoken"
        
        with patch.object(server, '_get_v3_api_client', return_value=mock_v3_client):
            result = await server.search_jira_issues("project = TEST", max_results=10)

        # Verify all issues from all pages were retrieved
        assert isinstance(result, list)
        assert len(result) == 5
        
        # Check each issue dict
        assert isinstance(result[0], dict)
        assert result[0]["key"] == "TEST-1"
        assert result[0]["fields"]["summary"] == "First Issue"
        assert result[0]["fields"]["status"]["name"] == "Open"
        
        assert result[1]["key"] == "TEST-2"
        assert result[1]["fields"]["summary"] == "Second Issue"
        assert result[1]["fields"]["status"]["name"] == "In Progress"
        
        assert result[2]["key"] == "TEST-3"
        assert result[2]["fields"]["summary"] == "Third Issue"
        assert result[2]["fields"]["status"]["name"] == "Done"
        
        assert result[3]["key"] == "TEST-4"
        assert result[3]["fields"]["summary"] == "Fourth Issue"
        assert result[3]["fields"]["status"]["name"] == "Closed"
        # None handling
        assert result[3]["fields"].get("assignee") is None
        
        assert result[4]["key"] == "TEST-5"
        assert result[4]["fields"]["summary"] == "Fifth Issue"
        assert result[4]["fields"]["status"]["name"] == "Open"

        # Verify V3 client was called the correct number of times with correct parameters
        assert mock_v3_client.search_issues.call_count == 3
        
        # Check first call
        first_call = mock_v3_client.search_issues.call_args_list[0]
        assert first_call[1]["jql"] == "project = TEST"
        assert first_call[1]["start_at"] == 0
        assert first_call[1]["max_results"] == 10
        
        # Check second call
        second_call = mock_v3_client.search_issues.call_args_list[1]
        assert second_call[1]["jql"] == "project = TEST"
        assert second_call[1]["start_at"] == 2  # After first 2 issues
        assert second_call[1]["max_results"] == 8  # Remaining needed: 10 - 2 = 8, min(8, 100) = 8
        
        # Check third call
        third_call = mock_v3_client.search_issues.call_args_list[2]
        assert third_call[1]["jql"] == "project = TEST"
        assert third_call[1]["start_at"] == 4  # After first 4 issues
        assert third_call[1]["max_results"] == 6  # Remaining needed: 10 - 4 = 6, min(6, 100) = 6

    @pytest.mark.asyncio
    async def test_server_search_issues_pagination_with_limit(self):
        """Test JiraServer search_issues method respects max_results when paginating"""
        # Mock V3 API responses for multiple pages, but we'll limit results
        page1_response = {
            "issues": [
                {"key": "TEST-1", "fields": {"summary": "First Issue"}},
                {"key": "TEST-2", "fields": {"summary": "Second Issue"}},
                {"key": "TEST-3", "fields": {"summary": "Third Issue"}}
            ],
            "startAt": 0,
            "maxResults": 3,
            "total": 10,
            "isLast": False
        }

        page2_response = {
            "issues": [
                {"key": "TEST-4", "fields": {"summary": "Fourth Issue"}},
                {"key": "TEST-5", "fields": {"summary": "Fifth Issue"}}
            ],
            "startAt": 3,
            "maxResults": 2,  # Only 2 more to reach our limit of 5
            "total": 10,
            "isLast": False
        }

        # Mock V3 API client
        mock_v3_client = AsyncMock()
        mock_v3_client.search_issues.side_effect = [page1_response, page2_response]

        # Create JiraServer instance and mock the V3 client
        server = JiraServer()
        server.server_url = "https://test.atlassian.net"
        server.username = "testuser"
        server.token = "testtoken"
        
        with patch.object(server, '_get_v3_api_client', return_value=mock_v3_client):
            # Request only 5 results max
            result = await server.search_jira_issues("project = TEST", max_results=5)

        # Verify exactly 5 issues were returned (respecting max_results)
        assert isinstance(result, list)
        assert len(result) == 5
        assert result[0]["key"] == "TEST-1"
        assert result[1]["key"] == "TEST-2"
        assert result[2]["key"] == "TEST-3"
        assert result[3]["key"] == "TEST-4"
        assert result[4]["key"] == "TEST-5"

        # Verify pagination stopped at the right point
        assert mock_v3_client.search_issues.call_count == 2