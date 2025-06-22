"""Test cases for bulk_create_issues V3 API client only"""

import asyncio
from unittest.mock import Mock, patch, AsyncMock
import pytest

from src.mcp_server_jira.jira_v3_api import JiraV3APIClient


class TestBulkCreateIssuesV3API:
    """Test suite for bulk_create_issues V3 API client"""

    @pytest.mark.asyncio
    async def test_v3_api_bulk_create_issues_success(self):
        """Test successful bulk create issues request with V3 API"""
        # Mock 201 Created response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "issues": [
                {
                    "id": "10000",
                    "key": "PROJ-1",
                    "self": "https://test.atlassian.net/rest/api/3/issue/10000"
                },
                {
                    "id": "10001", 
                    "key": "PROJ-2",
                    "self": "https://test.atlassian.net/rest/api/3/issue/10001"
                }
            ],
            "errors": []
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

        # Test data
        issue_updates = [
            {
                "fields": {
                    "project": {"key": "PROJ"},
                    "summary": "First test issue",
                    "description": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "Test description"}]
                            }
                        ]
                    },
                    "issuetype": {"name": "Bug"}
                }
            },
            {
                "fields": {
                    "project": {"key": "PROJ"},
                    "summary": "Second test issue",
                    "description": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "Another test description"}]
                            }
                        ]
                    },
                    "issuetype": {"name": "Task"}
                }
            }
        ]

        result = await client.bulk_create_issues(issue_updates)

        # Verify the request was made correctly
        mock_client.request.assert_called_once()
        call_args = mock_client.request.call_args

        assert call_args[1]["method"] == "POST"
        assert "/rest/api/3/issue/bulk" in call_args[1]["url"]
        assert call_args[1]["json"]["issueUpdates"] == issue_updates
        
        # Verify the response
        assert "issues" in result
        assert "errors" in result
        assert len(result["issues"]) == 2
        assert result["issues"][0]["key"] == "PROJ-1"
        assert result["issues"][1]["key"] == "PROJ-2"

    @pytest.mark.asyncio
    async def test_v3_api_bulk_create_issues_empty_list(self):
        """Test bulk create issues with empty list"""
        client = JiraV3APIClient(
            server_url="https://test.atlassian.net",
            username="testuser",
            token="testtoken"
        )

        with pytest.raises(ValueError, match="issue_updates list cannot be empty"):
            await client.bulk_create_issues([])

    @pytest.mark.asyncio
    async def test_v3_api_bulk_create_issues_too_many(self):
        """Test bulk create issues with too many issues"""
        client = JiraV3APIClient(
            server_url="https://test.atlassian.net",
            username="testuser",
            token="testtoken"
        )

        # Create more than 50 issues
        issue_updates = [{"fields": {"project": {"key": "PROJ"}}}] * 51

        with pytest.raises(ValueError, match="Cannot create more than 50 issues"):
            await client.bulk_create_issues(issue_updates)

    @pytest.mark.asyncio
    async def test_v3_api_bulk_create_issues_with_errors(self):
        """Test bulk create issues response with some errors"""
        # Mock response with partial success
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "issues": [
                {
                    "id": "10000",
                    "key": "PROJ-1",
                    "self": "https://test.atlassian.net/rest/api/3/issue/10000"
                }
            ],
            "errors": [
                {
                    "failedElementNumber": 1,
                    "elementErrors": {
                        "errorMessages": ["Issue type 'InvalidType' does not exist."]
                    }
                }
            ]
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

        # Test data
        issue_updates = [
            {
                "fields": {
                    "project": {"key": "PROJ"},
                    "summary": "Valid issue",
                    "issuetype": {"name": "Bug"}
                }
            },
            {
                "fields": {
                    "project": {"key": "PROJ"},
                    "summary": "Invalid issue", 
                    "issuetype": {"name": "InvalidType"}
                }
            }
        ]

        result = await client.bulk_create_issues(issue_updates)

        # Verify we get both success and error results
        assert len(result["issues"]) == 1
        assert len(result["errors"]) == 1
        assert result["issues"][0]["key"] == "PROJ-1"
        assert "errorMessages" in result["errors"][0]["elementErrors"]