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
    def test_get_jira_projects(self, mock_get_v3_api_client):
        """Test getting Jira projects using v3 API"""
        # Setup mock v3 client
        mock_v3_client = Mock()
        mock_v3_client.get_projects.return_value = {
            "startAt": 0,
            "maxResults": 50,
            "total": 1,
            "isLast": True,
            "values": [
                {
                    "id": "123",
                    "key": "TEST",
                    "name": "Test Project",
                    "lead": {
                        "displayName": "John Doe"
                    }
                }
            ]
        }
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
        assert len(projects) == 1
        assert isinstance(projects[0], JiraProjectResult)
        assert projects[0].key == "TEST"
        assert projects[0].name == "Test Project"
        assert projects[0].id == "123"
        assert projects[0].lead == "John Doe"

        # Verify v3 client was called correctly
        mock_v3_client.get_projects.assert_called_with(
            start_at=0,
            max_results=50
        )

    @patch.object(JiraServer, "_get_v3_api_client")
    def test_get_jira_projects_pagination(self, mock_get_v3_api_client):
        """Test getting Jira projects with pagination"""
        # Setup mock v3 client with pagination
        mock_v3_client = Mock()
        
        # First page response
        page1_response = {
            "startAt": 0,
            "maxResults": 2,
            "total": 3,
            "isLast": False,
            "values": [
                {"id": "10000", "key": "TEST1", "name": "Test Project 1"},
                {"id": "10001", "key": "TEST2", "name": "Test Project 2"}
            ]
        }
        
        # Second page response  
        page2_response = {
            "startAt": 2,
            "maxResults": 2,
            "total": 3,
            "isLast": True,
            "values": [
                {"id": "10002", "key": "TEST3", "name": "Test Project 3"}
            ]
        }
        
        # Configure mock to return different responses for each call
        mock_v3_client.get_projects.side_effect = [page1_response, page2_response]
        mock_get_v3_api_client.return_value = mock_v3_client

        server = JiraServer(
            server_url="https://test.atlassian.net",
            auth_method="token",
            username="testuser",
            token="testtoken",
        )

        # Call the method
        projects = server.get_jira_projects()

        # Should have called get_projects twice due to pagination
        assert mock_v3_client.get_projects.call_count == 2
        
        # Should have collected all 3 projects
        assert len(projects) == 3
        assert projects[0].key == "TEST1"
        assert projects[1].key == "TEST2"
        assert projects[2].key == "TEST3"
        
        # Verify correct pagination parameters
        calls = mock_v3_client.get_projects.call_args_list
        assert calls[0][1]["start_at"] == 0
        assert calls[1][1]["start_at"] == 2

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
