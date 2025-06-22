"""Test cases for get_transitions V3 API conversion"""

import asyncio
from unittest.mock import Mock, patch, AsyncMock
import pytest

from src.mcp_server_jira.jira_v3_api import JiraV3APIClient
from src.mcp_server_jira.server import JiraServer, JiraTransitionResult


class TestGetTransitionsV3APIConversion:
    """Test suite for get_transitions V3 API conversion"""

    @pytest.mark.asyncio
    async def test_v3_api_get_transitions_success(self):
        """Test successful get transitions request with V3 API"""
        # Mock response data matching Jira V3 API format
        mock_response_data = {
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
                    "isAvailable": True
                },
                {
                    "id": "711",
                    "name": "QA Review",
                    "to": {
                        "id": "5",
                        "name": "In Review"
                    },
                    "hasScreen": True,
                    "isAvailable": True
                }
            ]
        }

        # Mock httpx response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.text = str(mock_response_data)
        mock_response.raise_for_status.return_value = None

        client = JiraV3APIClient(
            server_url="https://test.atlassian.net",
            username="testuser",
            token="testtoken"
        )

        with patch.object(client.client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.get_transitions("PROJ-123")

            # Verify the result structure
            assert "transitions" in result
            assert len(result["transitions"]) == 2
            assert result["transitions"][0]["id"] == "2"
            assert result["transitions"][0]["name"] == "Close Issue"
            assert result["transitions"][1]["id"] == "711"
            assert result["transitions"][1]["name"] == "QA Review"

            # Verify the API call
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[1]["method"] == "GET"
            assert "/rest/api/3/issue/PROJ-123/transitions" in call_args[1]["url"]

    @pytest.mark.asyncio
    async def test_v3_api_get_transitions_with_parameters(self):
        """Test get transitions with query parameters"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"transitions": []}
        mock_response.text = "{\"transitions\": []}"
        mock_response.raise_for_status.return_value = None

        client = JiraV3APIClient(
            server_url="https://test.atlassian.net",
            username="testuser",
            token="testtoken"
        )

        with patch.object(client.client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            await client.get_transitions(
                issue_id_or_key="PROJ-123",
                expand="transitions.fields",
                transition_id="2",
                skip_remote_only_condition=True
            )

            # Verify the request parameters
            call_args = mock_request.call_args
            params = call_args[1]["params"]
            assert params["expand"] == "transitions.fields"
            assert params["transitionId"] == "2"
            assert params["skipRemoteOnlyCondition"] is True

    @pytest.mark.asyncio
    async def test_v3_api_get_transitions_missing_issue_key(self):
        """Test get transitions with missing issue key"""
        client = JiraV3APIClient(
            server_url="https://test.atlassian.net",
            username="testuser",
            token="testtoken"
        )

        with pytest.raises(ValueError, match="issue_id_or_key is required"):
            await client.get_transitions("")

    @pytest.mark.asyncio
    async def test_jira_server_get_transitions_success(self):
        """Test JiraServer get_jira_transitions method"""
        mock_api_response = {
            "transitions": [
                {"id": "2", "name": "Close Issue"},
                {"id": "711", "name": "QA Review"},
                {"id": "31", "name": "Reopen Issue"}
            ]
        }

        server = JiraServer(
            server_url="https://test.atlassian.net",
            username="testuser",
            token="testtoken"
        )

        with patch.object(server._v3_api_client, 'get_transitions', new_callable=AsyncMock) as mock_get_transitions:
            mock_get_transitions.return_value = mock_api_response

            result = await server.get_jira_transitions("PROJ-123")

            # Verify the result type and structure
            assert isinstance(result, list)
            assert len(result) == 3
            assert all(isinstance(t, JiraTransitionResult) for t in result)

            # Check specific transition details
            assert result[0].id == "2"
            assert result[0].name == "Close Issue"
            assert result[1].id == "711"
            assert result[1].name == "QA Review"
            assert result[2].id == "31"
            assert result[2].name == "Reopen Issue"

            # Verify the V3 API was called correctly
            mock_get_transitions.assert_called_once_with(issue_id_or_key="PROJ-123")

    @pytest.mark.asyncio
    async def test_jira_server_get_transitions_error_handling(self):
        """Test error handling in get_jira_transitions"""
        server = JiraServer(
            server_url="https://test.atlassian.net",
            username="testuser",
            token="testtoken"
        )

        with patch.object(server._v3_api_client, 'get_transitions', new_callable=AsyncMock) as mock_get_transitions:
            mock_get_transitions.side_effect = Exception("API Error")

            with pytest.raises(ValueError) as exc_info:
                await server.get_jira_transitions("PROJ-123")

            assert "Failed to get transitions for PROJ-123" in str(exc_info.value)
            assert "API Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_jira_server_backward_compatibility(self):
        """Test that the new implementation maintains backward compatibility"""
        mock_api_response = {
            "transitions": [
                {"id": "2", "name": "Close Issue"},
                {"id": "711", "name": "QA Review"}
            ]
        }

        server = JiraServer(
            server_url="https://test.atlassian.net",
            username="testuser",
            token="testtoken"
        )

        with patch.object(server._v3_api_client, 'get_transitions', new_callable=AsyncMock) as mock_get_transitions:
            mock_get_transitions.return_value = mock_api_response

            result = await server.get_jira_transitions("PROJ-123")

            # Verify the return type matches the original interface
            assert isinstance(result, list)
            assert all(isinstance(t, JiraTransitionResult) for t in result)
            assert all(hasattr(t, 'id') and hasattr(t, 'name') for t in result)

            # Verify specific field types
            assert isinstance(result[0].id, str)
            assert isinstance(result[0].name, str)

    @pytest.mark.asyncio
    async def test_jira_server_method_is_async(self):
        """Test that get_jira_transitions is properly converted to async"""
        server = JiraServer(
            server_url="https://test.atlassian.net",
            username="testuser",
            token="testtoken"
        )

        import inspect
        assert inspect.iscoroutinefunction(server.get_jira_transitions), \
            "get_jira_transitions should be an async method"