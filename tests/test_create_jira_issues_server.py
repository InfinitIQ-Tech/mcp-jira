"""Test cases for create_jira_issues server method using V3 API"""

import asyncio
from unittest.mock import Mock, patch, AsyncMock
import pytest

from src.mcp_server_jira.server import JiraServer


class TestCreateJiraIssuesServer:
    """Test suite for create_jira_issues server method"""

    @pytest.mark.asyncio
    async def test_create_jira_issues_server_success(self):
        """Test successful create_jira_issues through server"""
        # Mock the v3 API client response
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

        # Mock the v3 client
        mock_v3_client = AsyncMock()
        mock_v3_client.bulk_create_issues.return_value = mock_v3_response

        # Create server instance
        server = JiraServer(
            server_url="https://test.atlassian.net",
            username="testuser",
            password="testpass"
        )

        # Mock the _get_v3_api_client method
        with patch.object(server, '_get_v3_api_client', return_value=mock_v3_client):
            # Test data
            field_list = [
                {
                    "project": "PROJ",
                    "summary": "First test issue",
                    "description": "Test description",
                    "issue_type": "Bug"
                },
                {
                    "project": "PROJ", 
                    "summary": "Second test issue",
                    "description": "Another test description",
                    "issue_type": "Task"
                }
            ]

            result = await server.create_jira_issues(field_list)

            # Verify the v3 client was called correctly
            mock_v3_client.bulk_create_issues.assert_called_once()
            call_args = mock_v3_client.bulk_create_issues.call_args[0][0]

            # Check the transformed data structure
            assert len(call_args) == 2
            assert call_args[0]["fields"]["project"]["key"] == "PROJ"
            assert call_args[0]["fields"]["summary"] == "First test issue"
            assert call_args[0]["fields"]["issuetype"]["name"] == "Bug"
            
            # Check ADF format for description
            assert call_args[0]["fields"]["description"]["type"] == "doc"
            assert call_args[0]["fields"]["description"]["version"] == 1
            assert "Test description" in str(call_args[0]["fields"]["description"])

            # Verify the return format matches the original interface
            assert len(result) == 2
            assert result[0]["key"] == "PROJ-1"
            assert result[0]["id"] == "10000"
            assert result[0]["success"] is True
            assert result[1]["key"] == "PROJ-2"
            assert result[1]["success"] is True

    @pytest.mark.asyncio
    async def test_create_jira_issues_missing_required_fields(self):
        """Test create_jira_issues with missing required fields"""
        server = JiraServer(
            server_url="https://test.atlassian.net",
            username="testuser", 
            password="testpass"
        )

        # Test missing project
        with pytest.raises(ValueError, match="Each issue must have a 'project' field"):
            await server.create_jira_issues([
                {
                    "summary": "Test issue",
                    "description": "Test description",
                    "issue_type": "Bug"
                }
            ])

        # Test missing summary
        with pytest.raises(ValueError, match="Each issue must have a 'summary' field"):
            await server.create_jira_issues([
                {
                    "project": "PROJ",
                    "description": "Test description", 
                    "issue_type": "Bug"
                }
            ])

        # Test missing issue type
        with pytest.raises(ValueError, match="Each issue must have an 'issuetype' or 'issue_type' field"):
            await server.create_jira_issues([
                {
                    "project": "PROJ",
                    "summary": "Test issue",
                    "description": "Test description"
                }
            ])

    @pytest.mark.asyncio
    async def test_create_jira_issues_issue_type_conversion(self):
        """Test issue type conversion for common types"""
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
            # Test lowercase issue type conversion
            field_list = [
                {
                    "project": "PROJ",
                    "summary": "Test issue",
                    "description": "Test description",
                    "issue_type": "bug"  # lowercase
                }
            ]

            await server.create_jira_issues(field_list)

            # Verify issue type was converted to proper case
            call_args = mock_v3_client.bulk_create_issues.call_args[0][0]
            assert call_args[0]["fields"]["issuetype"]["name"] == "Bug"

    @pytest.mark.asyncio
    async def test_create_jira_issues_description_adf_conversion(self):
        """Test that string descriptions are converted to ADF format"""
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
            field_list = [
                {
                    "project": "PROJ",
                    "summary": "Test issue",
                    "description": "Simple text description",
                    "issue_type": "Bug"
                }
            ]

            await server.create_jira_issues(field_list)

            # Verify description was converted to ADF format
            call_args = mock_v3_client.bulk_create_issues.call_args[0][0]
            description = call_args[0]["fields"]["description"]
            
            assert description["type"] == "doc"
            assert description["version"] == 1
            assert len(description["content"]) == 1
            assert description["content"][0]["type"] == "paragraph"
            assert description["content"][0]["content"][0]["text"] == "Simple text description"

    @pytest.mark.asyncio
    async def test_create_jira_issues_with_errors_in_response(self):
        """Test create_jira_issues handling of error responses"""
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
                        "errorMessages": ["Invalid issue type"]
                    }
                }
            ]
        }

        mock_v3_client = AsyncMock()
        mock_v3_client.bulk_create_issues.return_value = mock_v3_response

        server = JiraServer(
            server_url="https://test.atlassian.net",
            username="testuser",
            password="testpass"
        )

        with patch.object(server, '_get_v3_api_client', return_value=mock_v3_client):
            field_list = [
                {
                    "project": "PROJ",
                    "summary": "Valid issue",
                    "description": "Valid description",
                    "issue_type": "Bug"
                },
                {
                    "project": "PROJ",
                    "summary": "Invalid issue",
                    "description": "Invalid description", 
                    "issue_type": "InvalidType"
                }
            ]

            result = await server.create_jira_issues(field_list)

            # Should have one success and one error
            assert len(result) == 2
            
            # Find success and error results
            success_results = [r for r in result if r.get("success")]
            error_results = [r for r in result if not r.get("success")]
            
            assert len(success_results) == 1
            assert len(error_results) == 1
            assert success_results[0]["key"] == "PROJ-1"
            assert "error" in error_results[0]