"""
Tests for the main server functionality.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.mcp_server_jira.server import JiraProjectResult, JiraServer


class TestJiraServer:
    """Test suite for JiraServer class"""

    def test_init_with_credentials(self):
        """Test JiraServer initialization with credentials"""
        server = JiraServer(
            server_url="https://test.atlassian.net",
            auth_method="token",
            username="testuser",
            token="testtoken",
        )

        assert server.server_url == "https://test.atlassian.net"
        assert server.auth_method == "token"
        assert server.username == "testuser"
        assert server.token == "testtoken"

    @patch.object(JiraServer, "_get_v3_api_client")
    def test_get_jira_projects_v3_api(self, mock_get_v3_api_client):
        """Test getting Jira projects using v3 API"""
        # Setup mock v3 client
        mock_v3_client = Mock()
        mock_v3_client.get_projects.return_value = [
            {
                "id": "10000",
                "key": "TEST",
                "name": "Test Project",
                "lead": {
                    "displayName": "John Doe",
                    "accountId": "john-account-id"
                }
            },
            {
                "id": "10001",
                "key": "DEMO", 
                "name": "Demo Project",
                "lead": {
                    "displayName": "Jane Smith",
                    "accountId": "jane-account-id"
                }
            }
        ]
        mock_get_v3_api_client.return_value = mock_v3_client

        server = JiraServer(
            server_url="https://test.atlassian.net",
            auth_method="token",
            username="testuser",
            token="testtoken",
        )

        # Call the method
        projects = server.get_jira_projects()

        # Verify results
        assert len(projects) == 2
        assert isinstance(projects[0], JiraProjectResult)
        assert projects[0].key == "TEST"
        assert projects[0].name == "Test Project"
        assert projects[0].id == "10000"
        assert projects[0].lead == "John Doe"
        
        assert projects[1].key == "DEMO"
        assert projects[1].name == "Demo Project"
        assert projects[1].id == "10001"
        assert projects[1].lead == "Jane Smith"

        # Verify v3 client was called correctly
        mock_v3_client.get_projects.assert_called_once_with(expand="lead")

    @patch.object(JiraServer, "_get_v3_api_client")
    def test_create_jira_project_v3_api(self, mock_get_v3_api_client):
        """Test project creation using v3 API"""
        # Setup mock v3 client
        mock_v3_client = Mock()
        mock_v3_client.create_project.return_value = {
            "self": "https://test.atlassian.net/rest/api/3/project/10000",
            "id": "10000",
            "key": "TEST",
            "name": "Test Project",
        }
        mock_get_v3_api_client.return_value = mock_v3_client

        server = JiraServer(
            server_url="https://test.atlassian.net",
            auth_method="token",
            username="testuser",
            token="testtoken",
        )

        # Call the method
        result = server.create_jira_project(
            key="TEST", name="Test Project", ptype="software"
        )

        # Verify results
        assert isinstance(result, JiraProjectResult)
        assert result.key == "TEST"
        assert result.name == "Test Project"

        # Verify v3 client was called correctly
        mock_v3_client.create_project.assert_called_once_with(
            key="TEST",
            name="Test Project",
            assignee=None,
            ptype="software",
            template_name=None,
            avatarId=None,
            issueSecurityScheme=None,
            permissionScheme=None,
            projectCategory=None,
            notificationScheme=None,
            categoryId=None,
            url="",
        )

    @patch.object(JiraServer, "_get_v3_api_client")
    def test_create_jira_project_with_template(self, mock_get_v3_api_client):
        """Test project creation with template using v3 API"""
        # Setup mock v3 client
        mock_v3_client = Mock()
        mock_v3_client.create_project.return_value = {
            "self": "https://test.atlassian.net/rest/api/3/project/10000",
            "id": "10000",
            "key": "TEMP",
            "name": "Template Project",
        }
        mock_get_v3_api_client.return_value = mock_v3_client

        server = JiraServer(
            server_url="https://test.atlassian.net",
            auth_method="token",
            username="testuser",
            token="testtoken",
        )

        # Call the method with template
        result = server.create_jira_project(
            key="TEMP",
            name="Template Project",
            ptype="business",
            template_name="com.atlassian.jira-core-project-templates:jira-core-project-management",
            assignee="user123",
        )

        # Verify results
        assert isinstance(result, JiraProjectResult)
        assert result.key == "TEMP"
        assert result.name == "Template Project"

        # Verify v3 client was called with template parameters
        mock_v3_client.create_project.assert_called_once_with(
            key="TEMP",
            name="Template Project",
            assignee="user123",
            ptype="business",
            template_name="com.atlassian.jira-core-project-templates:jira-core-project-management",
            avatarId=None,
            issueSecurityScheme=None,
            permissionScheme=None,
            projectCategory=None,
            notificationScheme=None,
            categoryId=None,
            url="",
        )

    def test_get_v3_api_client(self):
        """Test v3 client creation"""
        server = JiraServer(
            server_url="https://test.atlassian.net",
            auth_method="token",
            username="testuser",
            token="testtoken",
        )

        client = server._get_v3_api_client()

        assert client.server_url == "https://test.atlassian.net"
        assert client.username == "testuser"
        assert client.token == "testtoken"
        assert client.password is None

    def test_get_v3_api_client_with_password(self):
        """Test v3 client creation with password"""
        server = JiraServer(
            server_url="https://test.atlassian.net",
            auth_method="basic",
            username="testuser",
            password="testpass",
        )

        client = server._get_v3_api_client()

        assert client.server_url == "https://test.atlassian.net"
        assert client.username == "testuser"
        assert client.password == "testpass"
        assert client.token is None
