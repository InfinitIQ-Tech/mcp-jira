"""Test cases for add_comment V3 API client only"""

import asyncio
from unittest.mock import Mock, patch, AsyncMock
import pytest

from src.mcp_server_jira.jira_v3_api import JiraV3APIClient


class TestAddCommentV3API:
    """Test suite for add_comment V3 API client"""

    @pytest.mark.asyncio
    async def test_v3_api_add_comment_success(self):
        """Test successful add comment request with V3 API"""
        # Mock successful response
        mock_response_data = {
            "id": "10000",
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": "This is a test comment"
                            }
                        ]
                    }
                ]
            },
            "author": {
                "accountId": "5b10a2844c20165700ede21g",
                "displayName": "Test User",
                "active": True
            },
            "created": "2021-01-17T12:34:00.000+0000",
            "updated": "2021-01-17T12:34:00.000+0000",
            "self": "https://test.atlassian.net/rest/api/3/issue/10010/comment/10000"
        }

        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = mock_response_data
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

        result = await client.add_comment(
            issue_id_or_key="PROJ-123",
            comment="This is a test comment"
        )

        # Verify the request was made correctly
        call_args = mock_client.request.call_args
        assert call_args[1]["method"] == "POST"
        assert "https://test.atlassian.net/rest/api/3/issue/PROJ-123/comment" in call_args[1]["url"]
        
        # Verify the request payload
        payload = call_args[1]["json"]
        assert payload["body"]["type"] == "doc"
        assert payload["body"]["version"] == 1
        assert len(payload["body"]["content"]) == 1
        assert payload["body"]["content"][0]["type"] == "paragraph"
        assert payload["body"]["content"][0]["content"][0]["text"] == "This is a test comment"

        # Verify the response
        assert result == mock_response_data

    @pytest.mark.asyncio
    async def test_v3_api_add_comment_with_visibility(self):
        """Test add comment with visibility settings"""
        # Mock successful response
        mock_response_data = {
            "id": "10001",
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph", 
                        "content": [
                            {
                                "type": "text",
                                "text": "Internal comment"
                            }
                        ]
                    }
                ]
            },
            "visibility": {
                "type": "role",
                "value": "Administrators"
            }
        }

        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = mock_response_data
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

        visibility = {"type": "role", "value": "Administrators"}
        result = await client.add_comment(
            issue_id_or_key="PROJ-456",
            comment="Internal comment",
            visibility=visibility
        )

        # Verify the request payload includes visibility
        call_args = mock_client.request.call_args
        payload = call_args[1]["json"]
        
        assert "visibility" in payload
        assert payload["visibility"]["type"] == "role"
        assert payload["visibility"]["value"] == "Administrators"
        
        # Verify the response
        assert result == mock_response_data

    @pytest.mark.asyncio
    async def test_v3_api_add_comment_missing_issue_key(self):
        """Test add comment with missing issue key"""
        client = JiraV3APIClient(
            server_url="https://test.atlassian.net",
            username="testuser",
            token="testtoken"
        )

        with pytest.raises(ValueError, match="issue_id_or_key is required"):
            await client.add_comment(
                issue_id_or_key="",
                comment="Test comment"
            )

    @pytest.mark.asyncio
    async def test_v3_api_add_comment_missing_comment(self):
        """Test add comment with missing comment text"""
        client = JiraV3APIClient(
            server_url="https://test.atlassian.net",
            username="testuser",
            token="testtoken"
        )

        with pytest.raises(ValueError, match="comment is required"):
            await client.add_comment(
                issue_id_or_key="PROJ-123",
                comment=""
            )

    @pytest.mark.asyncio
    async def test_v3_api_add_comment_with_properties(self):
        """Test add comment with properties"""
        # Mock successful response
        mock_response_data = {
            "id": "10002",
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": "Comment with properties"
                            }
                        ]
                    }
                ]
            },
            "properties": [
                {
                    "key": "custom-property",
                    "value": "custom-value"
                }
            ]
        }

        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = mock_response_data
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

        properties = [{"key": "custom-property", "value": "custom-value"}]
        result = await client.add_comment(
            issue_id_or_key="PROJ-789",
            comment="Comment with properties",
            properties=properties
        )

        # Verify the request payload includes properties
        call_args = mock_client.request.call_args
        payload = call_args[1]["json"]
        
        assert "properties" in payload
        assert len(payload["properties"]) == 1
        assert payload["properties"][0]["key"] == "custom-property"
        assert payload["properties"][0]["value"] == "custom-value"
        
        # Verify the response
        assert result == mock_response_data