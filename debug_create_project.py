#!/usr/bin/env python3
"""
Debug script to call Jira create project and dump detailed error.
"""
import os
import sys
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

# Read credentials
SERVER_URL = os.getenv("JIRA_SERVER_URL")
USERNAME = os.getenv("JIRA_USERNAME")
TOKEN = os.getenv("JIRA_API_TOKEN")

if not SERVER_URL or not TOKEN:
    print("Error: Please set JIRA_SERVER_URL and JIRA_API_TOKEN in environment or .env file.")
    sys.exit(1)

from src.mcp_server_jira.server import JiraServer

# Initialize server with token auth
server = JiraServer(
    server_url=SERVER_URL,
    auth_method="token",
    username=USERNAME,
    token=TOKEN,
)

# Attempt project creation
try:
    result = server.create_jira_project(
        key="ADHDIST",
        name="ADHDist",
        ptype="software",
        template_name="com.pyxis.greenhopper.jira:gh-kanban-template",
    )
    print("Success! Project created:", result)
except Exception as e:
    print("Exception caught during project creation:")
    print(str(e))
    # If exception contains payload/response details, it will be shown
