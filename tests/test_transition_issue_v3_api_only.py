"""Test cases for transition_issue V3 API client only"""

import asyncio
from unittest.mock import Mock, patch, AsyncMock
import pytest

from src.mcp_server_jira.jira_v3_api import JiraV3APIClient


class TestTransitionIssueV3API:
    """Test suite for transition_issue V3 API client"""

    @pytest.mark.asyncio
    async def test_v3_api_transition_issue_success(self):
        """Test successful transition issue request with V3 API"""
        # Mock 204 No Content response (standard for successful transitions)
        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.json.return_value = {}
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

        result = await client.transition_issue(
            issue_id_or_key="PROJ-123",
            transition_id="5"
        )

        # Verify the request was made correctly
        mock_client.request.assert_called_once()
        call_args = mock_client.request.call_args

        assert call_args[1]["method"] == "POST"
        assert "/rest/api/3/issue/PROJ-123/transitions" in call_args[1]["url"]
        assert call_args[1]["json"]["transition"]["id"] == "5"
        assert result == {}

    @pytest.mark.asyncio
    async def test_v3_api_transition_issue_with_comment(self):
        """Test transition issue with comment"""
        # Mock 204 No Content response
        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.json.return_value = {}
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

        result = await client.transition_issue(
            issue_id_or_key="PROJ-123",
            transition_id="2",
            comment="Issue resolved successfully"
        )

        # Verify the request payload includes properly formatted comment
        call_args = mock_client.request.call_args
        payload = call_args[1]["json"]
        
        assert payload["transition"]["id"] == "2"
        assert "update" in payload
        assert "comment" in payload["update"]
        assert len(payload["update"]["comment"]) == 1
        
        comment_structure = payload["update"]["comment"][0]["add"]["body"]
        assert comment_structure["type"] == "doc"
        assert comment_structure["version"] == 1
        assert len(comment_structure["content"]) == 1
        assert comment_structure["content"][0]["type"] == "paragraph"
        assert comment_structure["content"][0]["content"][0]["text"] == "Issue resolved successfully"

    @pytest.mark.asyncio
    async def test_v3_api_transition_issue_with_fields(self):
        """Test transition issue with field updates"""
        # Mock 204 No Content response
        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.json.return_value = {}
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

        fields = {
            "assignee": {"name": "john.doe"},
            "resolution": {"name": "Fixed"}
        }

        result = await client.transition_issue(
            issue_id_or_key="PROJ-123",
            transition_id="3",
            fields=fields
        )

        # Verify the request payload includes fields
        call_args = mock_client.request.call_args
        payload = call_args[1]["json"]
        
        assert payload["transition"]["id"] == "3"
        assert payload["fields"] == fields

    @pytest.mark.asyncio
    async def test_v3_api_transition_issue_missing_issue_key(self):
        """Test transition issue with missing issue key"""
        client = JiraV3APIClient(
            server_url="https://test.atlassian.net",
            username="testuser",
            token="testtoken"
        )

        with pytest.raises(ValueError, match="issue_id_or_key is required"):
            await client.transition_issue("", "5")

    @pytest.mark.asyncio
    async def test_v3_api_transition_issue_missing_transition_id(self):
        """Test transition issue with missing transition id"""
        client = JiraV3APIClient(
            server_url="https://test.atlassian.net",
            username="testuser",
            token="testtoken"
        )

        with pytest.raises(ValueError, match="transition_id is required"):
            await client.transition_issue("PROJ-123", "")