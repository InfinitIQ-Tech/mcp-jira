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

    @patch("src.mcp_server_jira.server.JIRA")
    def test_get_jira_projects(self, mock_jira_class):
        """Test getting Jira projects"""
        # Setup mock
        mock_jira = Mock()
        mock_project = Mock()
        mock_project.key = "TEST"
        mock_project.name = "Test Project"
        mock_project.id = "123"
        mock_project.projectTypeKey = "software"

        # Mock the lead properly
        mock_lead = Mock()
        mock_lead.displayName = "John Doe"
        mock_project.lead = mock_lead

        mock_jira.projects.return_value = [mock_project]
        mock_jira_class.return_value = mock_jira

        server = JiraServer(
            server_url="https://test.atlassian.net",
            auth_method="token",
            username="testuser",
            token="testtoken",
        )

        # Call the method
        projects = server.get_jira_projects()

        # Verify results
        assert len(projects) == 1
        assert isinstance(projects[0], JiraProjectResult)
        assert projects[0].key == "TEST"
        assert projects[0].name == "Test Project"

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
