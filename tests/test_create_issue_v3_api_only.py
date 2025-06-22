"""Test cases for create_issue V3 API client only"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.mcp_server_jira.jira_v3_api import JiraV3APIClient


class TestCreateIssueV3API:
    """Test suite for create_issue V3 API client"""

    @pytest.mark.asyncio
    async def test_v3_api_create_issue_success(self):
        """Test successful create issue request with V3 API"""
        # Mock 201 Created response (standard for successful creation)
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "10000",
            "key": "PROJ-123",
            "self": "https://test.atlassian.net/rest/api/3/issue/10000",
        }
        mock_response.text = '{"id":"10000","key":"PROJ-123","self":"https://test.atlassian.net/rest/api/3/issue/10000"}'
        mock_response.raise_for_status.return_value = None

        # Mock httpx client
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response

        client = JiraV3APIClient(
            server_url="https://test.atlassian.net",
            username="testuser",
            token="testtoken",
        )

        # Replace the client instance
        client.client = mock_client

        fields = {
            "project": {"key": "PROJ"},
            "summary": "Test issue",
            "description": "Test description",
            "issuetype": {"name": "Bug"},
        }

        result = await client.create_issue(fields=fields)

        # Verify the response
        assert result["id"] == "10000"
        assert result["key"] == "PROJ-123"
        assert result["self"] == "https://test.atlassian.net/rest/api/3/issue/10000"

        # Verify the request was made with correct parameters
        mock_client.request.assert_called_once()
        call_args = mock_client.request.call_args
        assert call_args[1]["method"] == "POST"
        assert "/rest/api/3/issue" in call_args[1]["url"]

        # Verify the payload
        payload = call_args[1]["json"]
        assert payload["fields"] == fields

    @pytest.mark.asyncio
    async def test_v3_api_create_issue_with_optional_params(self):
        """Test create issue with optional parameters"""
        # Mock 201 Created response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "10001",
            "key": "PROJ-124",
            "self": "https://test.atlassian.net/rest/api/3/issue/10001",
        }
        mock_response.text = '{"id":"10001","key":"PROJ-124","self":"https://test.atlassian.net/rest/api/3/issue/10001"}'
        mock_response.raise_for_status.return_value = None

        # Mock httpx client
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response

        client = JiraV3APIClient(
            server_url="https://test.atlassian.net",
            username="testuser",
            token="testtoken",
        )

        # Replace the client instance
        client.client = mock_client

        fields = {
            "project": {"key": "PROJ"},
            "summary": "Test issue with update",
            "description": "Test description",
            "issuetype": {"name": "Task"},
        }

        update = {"labels": [{"add": "urgent"}]}

        properties = [{"key": "test-property", "value": "test-value"}]

        result = await client.create_issue(
            fields=fields, update=update, properties=properties
        )

        # Verify the response
        assert result["id"] == "10001"
        assert result["key"] == "PROJ-124"

        # Verify the request was made with correct parameters
        mock_client.request.assert_called_once()
        call_args = mock_client.request.call_args

        # Verify the payload contains all optional parameters
        payload = call_args[1]["json"]
        assert payload["fields"] == fields
        assert payload["update"] == update
        assert payload["properties"] == properties

    @pytest.mark.asyncio
    async def test_v3_api_create_issue_missing_fields(self):
        """Test create issue with missing fields"""
        client = JiraV3APIClient(
            server_url="https://test.atlassian.net",
            username="testuser",
            token="testtoken",
        )

        with pytest.raises(ValueError, match="fields is required"):
            await client.create_issue(fields=None)

    @pytest.mark.asyncio
    async def test_v3_api_create_issue_empty_fields(self):
        """Test create issue with empty fields dict"""
        client = JiraV3APIClient(
            server_url="https://test.atlassian.net",
            username="testuser",
            token="testtoken",
        )

        with pytest.raises(ValueError, match="fields is required"):
            await client.create_issue(fields={})
