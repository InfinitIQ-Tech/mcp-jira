import asyncio
import os

from .server import serve


def main() -> None:
    # Get configuration from environment variables
    server_url = os.environ.get("JIRA_SERVER_URL")
    auth_method = os.environ.get("JIRA_AUTH_METHOD")
    username = os.environ.get("JIRA_USERNAME")
    password = os.environ.get("JIRA_PASSWORD")
    token = os.environ.get("JIRA_TOKEN")

    asyncio.run(
        serve(
            server_url=server_url,
            auth_method=auth_method,
            username=username,
            password=password,
            token=token,
        )
    )


if __name__ == "__main__":
    main()
