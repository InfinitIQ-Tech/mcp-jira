"""
Integration test for create_jira_issues V3 API conversion

This test verifies that the conversion from the legacy Jira Python SDK
to the v3 REST API is working correctly for bulk issue creation.

Run with: python -m pytest tests/test_create_issues_integration.py -v
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.mcp_server_jira.server import JiraServer


class TestCreateIssuesIntegration:
    """Integration tests for the create_issues v3 API conversion"""

    @pytest.mark.asyncio
    async def test_full_integration_with_v3_api(self):
        """Test the full integration from server method to v3 API client"""
        # Mock successful v3 API response
        mock_v3_response = {
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

        # Create mock v3 client
        mock_v3_client = AsyncMock()
        mock_v3_client.bulk_create_issues.return_value = mock_v3_response

        # Create server instance
        server = JiraServer(
            server_url="https://test.atlassian.net",
            username="testuser",
            password="testpass"
        )

        # Patch the v3 client creation
        with patch.object(server, '_get_v3_api_client', return_value=mock_v3_client):
            # Test data representing a typical bulk creation request
            field_list = [
                {
                    "project": "PROJ",
                    "summary": "Implement user login functionality",
                    "description": "Add OAuth2 login with Google and GitHub providers",
                    "issue_type": "story",
                    "labels": ["authentication", "oauth"],
                    "priority": {"name": "High"}
                },
                {
                    "project": "PROJ",
                    "summary": "Fix mobile navigation bug",
                    "description": "Navigation menu not displaying on mobile devices",
                    "issue_type": "bug",
                    "assignee": {"name": "john.doe"}
                }
            ]

            # Execute the method
            result = await server.create_jira_issues(field_list, prefetch=True)

            # Verify v3 client was called
            mock_v3_client.bulk_create_issues.assert_called_once()
            
            # Verify the payload transformation
            call_args = mock_v3_client.bulk_create_issues.call_args[0][0]
            assert len(call_args) == 2

            # Check first issue transformation
            issue1 = call_args[0]["fields"]
            assert issue1["project"]["key"] == "PROJ"
            assert issue1["summary"] == "Implement user login functionality"
            assert issue1["issuetype"]["name"] == "Story"  # Converted from "story"
            assert issue1["labels"] == ["authentication", "oauth"]
            assert issue1["priority"] == {"name": "High"}
            
            # Check ADF format for description
            assert issue1["description"]["type"] == "doc"
            assert "OAuth2 login" in str(issue1["description"])

            # Check second issue transformation
            issue2 = call_args[1]["fields"]
            assert issue2["project"]["key"] == "PROJ"
            assert issue2["summary"] == "Fix mobile navigation bug"
            assert issue2["issuetype"]["name"] == "Bug"  # Converted from "bug"
            assert issue2["assignee"] == {"name": "john.doe"}

            # Verify return format compatibility
            assert len(result) == 2
            assert result[0]["key"] == "PROJ-1"
            assert result[0]["id"] == "10000"
            assert result[0]["success"] is True
            assert result[1]["key"] == "PROJ-2"
            assert result[1]["success"] is True

    @pytest.mark.asyncio
    async def test_error_handling_integration(self):
        """Test error handling in the integrated flow"""
        # Mock v3 API response with partial errors
        mock_v3_response = {
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
                        "errorMessages": ["Invalid issue type 'InvalidType'"]
                    }
                }
            ]
        }

        # Create mock v3 client
        mock_v3_client = AsyncMock()
        mock_v3_client.bulk_create_issues.return_value = mock_v3_response

        # Create server instance
        server = JiraServer(
            server_url="https://test.atlassian.net",
            username="testuser",
            password="testpass"
        )

        # Patch the v3 client creation
        with patch.object(server, '_get_v3_api_client', return_value=mock_v3_client):
            field_list = [
                {
                    "project": "PROJ",
                    "summary": "Valid issue",
                    "description": "This should work",
                    "issue_type": "Bug"
                },
                {
                    "project": "PROJ",
                    "summary": "Invalid issue",
                    "description": "This should fail",
                    "issue_type": "InvalidType"
                }
            ]

            result = await server.create_jira_issues(field_list)

            # Should get both success and error results
            assert len(result) == 2
            
            # Find success and error entries
            success_results = [r for r in result if r.get("success")]
            error_results = [r for r in result if not r.get("success")]
            
            assert len(success_results) == 1
            assert len(error_results) == 1
            assert success_results[0]["key"] == "PROJ-1"
            assert "error" in error_results[0]

    @pytest.mark.asyncio
    async def test_backward_compatibility_with_legacy_format(self):
        """Test that the method maintains backward compatibility with existing usage"""
        mock_v3_response = {
            "issues": [
                {
                    "id": "10000",
                    "key": "PROJ-1",
                    "self": "https://test.atlassian.net/rest/api/3/issue/10000"
                }
            ],
            "errors": []
        }

        mock_v3_client = AsyncMock()
        mock_v3_client.bulk_create_issues.return_value = mock_v3_response

        server = JiraServer(
            server_url="https://test.atlassian.net",
            username="testuser",
            password="testpass"
        )

        with patch.object(server, '_get_v3_api_client', return_value=mock_v3_client):
            # Test with both new and legacy field formats
            field_list = [
                {
                    # Using 'issuetype' field (legacy format)
                    "project": {"key": "PROJ"},  # Object format
                    "summary": "Legacy format issue",
                    "description": "Using legacy field formats",
                    "issuetype": {"name": "Bug"}  # Object format
                }
            ]

            result = await server.create_jira_issues(field_list)

            # Should work with legacy formats
            assert len(result) == 1
            assert result[0]["success"] is True
            assert result[0]["key"] == "PROJ-1"

            # Verify the payload was transformed correctly
            call_args = mock_v3_client.bulk_create_issues.call_args[0][0]
            issue_fields = call_args[0]["fields"]
            
            # Legacy project object format should be preserved
            assert issue_fields["project"]["key"] == "PROJ"
            # Legacy issuetype object format should be preserved
            assert issue_fields["issuetype"]["name"] == "Bug"