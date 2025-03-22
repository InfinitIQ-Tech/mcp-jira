#!/usr/bin/env python3
"""
Simple script to run the Jira MCP server with detailed logging
"""
import asyncio
import logging
import os
import sys

from src.mcp_server_jira.server import serve

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger()

async def main():
    logger.info("Starting Jira MCP server...")
    
    # Get configuration from environment variables
    server_url = os.environ.get("JIRA_SERVER_URL")
    auth_method = os.environ.get("JIRA_AUTH_METHOD")
    username = os.environ.get("JIRA_USERNAME")
    password = os.environ.get("JIRA_PASSWORD")
    token = os.environ.get("JIRA_TOKEN")
    
    logger.info(f"Server URL: {server_url or 'Not configured'}")
    logger.info(f"Auth Method: {auth_method or 'Not configured'}")
    
    try:
        await serve(
            server_url=server_url,
            auth_method=auth_method,
            username=username,
            password=password,
            token=token
        )
    except Exception as e:
        logger.error(f"Error running server: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())