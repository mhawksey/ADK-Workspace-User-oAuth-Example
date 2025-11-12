# Google Chat Agent with ADK (Journey 2)

This project demonstrates how to build a sophisticated, multi-capability Google Chat agent using Google's Agent Development Kit (ADK). It follows the "Journey 2" or "Crafted Tool" approach, emphasizing custom tool implementation for greater control, robustness, and efficiency over auto-generated tools.

The agent can search Google Chat spaces and list messages within a space, handling authentication and pagination automatically. It uses an "Orchestrator/Worker" agent structure to optimize for cost and performance.

This project is designed as a high-fidelity local workbench, perfect for development, debugging, and rapid iteration.

## Features

*   **Custom Tool Implementation ("Journey 2"):** Uses `FunctionTool` to wrap custom Python functions, providing fine-grained control over the agent's capabilities.
*   **Reusable Authentication Pattern:** A centralized `get_credentials` function manages the entire OAuth 2.0 lifecycle, making it easily adaptable for other Google Workspace APIs.
*   **Robust and Efficient:** Handles API complexities like pagination internally, abstracting them from the LLM and preserving its context window.
*   **Orchestrator/Worker Architecture:** A fast, lightweight model (`gemini-2.5-flash`) orchestrates tasks, while a more powerful model (`gemini-2.5-pro`) handles specialized analysis.
*   **Local Test Harness:** A command-line interface (`cli.py`) allows for easy local testing and interaction with the agent.

## Architectural Overview

The agent is composed of two main parts:

*   **Orchestrator Agent (`orchestrator_agent`):** The primary, user-facing agent. It uses a fast, cost-effective model (`gemini-2.5-flash`) to handle initial user requests and route tasks. It is responsible for searching for chat spaces.
*   **Worker Agent (`message_analysis_agent`):** A specialized agent that uses a more powerful model (`gemini-2.5-pro`) for in-depth analysis. It is responsible for listing and analyzing messages within a specific chat space.

This separation of concerns allows for a more efficient and scalable agent architecture.

## Getting Started

### Prerequisites

*   Python 3.10+
*   A Google Cloud project with the Google Chat API enabled.
*   OAuth 2.0 Client ID and Client Secret. You can create these in the [Google Cloud Console](https://console.cloud.google.com/apis/credentials). When creating your OAuth 2.0 Client ID, you must add `http://localhost:8000/callback` as an authorized redirect URI.

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/your-repo-name.git
    cd your-repo-name
    ```

2.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up your environment variables:**
    Create a `.env` file in the project root and add your Google Cloud OAuth 2.0 credentials:
    ```
    GOOGLE_CLIENT_ID="your-google-client-id.apps.googleusercontent.com"
    GOOGLE_CLIENT_SECRET="your-google-client-secret"
    ```

## Running the Agent

Run the local command-line interface:

```bash
python cli.py
```

The first time you use a command that requires authentication (like searching for a chat space), the agent will prompt you to authenticate:

1.  It will print a URL. Open this URL in your browser.
2.  Sign in with your Google account and grant the requested permissions.
3.  After authorizing, you will be redirected to a `localhost` URL. Copy the **entire** URL from your browser's address bar.
4.  Paste the URL back into the terminal and press Enter.

The agent will then complete your request. Your authentication token will be cached for the duration of the session.

## Authentication Flow

When integrating APIs with the ADK, there are two main approaches to authentication:

*   **Journey 1: The "Auto-Toolify" Approach.** This involves using pre-built toolsets like `OpenAPIToolset` or the `GoogleApiToolSet`. The ADK handles authentication automatically based on an API specification. While fast for prototyping, this approach can be "noisy" as it often creates tools for every single API endpoint, many of which may not be necessary.
*   **Journey 2: The "Crafted Tool" Approach.** This involves writing your own Python functions and wrapping them in a `FunctionTool`. This gives you full control over the authentication logic within your tool.

This project uses the "Journey 2" approach for maximum control and robustness. The `get_credentials` function in `agent.py` implements this pattern, which is called by every tool that needs to access a protected resource.

The authentication flow follows these steps:

1.  **Check for Cached Token:** It first checks the `tool_context.state` for a valid, cached OAuth token.
2.  **Refresh Token:** If a token exists but is expired, it uses the refresh token to get a new one and updates the cache.
3.  **Check for Auth Response:** If no token is found, it checks if the user has just completed the OAuth consent flow using `tool_context.get_auth_response()`. If so, it creates the credentials and caches them.
4.  **Request Credentials:** If all else fails, it formally requests credentials via `tool_context.request_credential()`. This pauses the agent and signals the `cli.py` to initiate the interactive user authentication flow.

This robust pattern, recommended by the ADK documentation, ensures that the agent can reliably and securely access user data. For more details on the ADK's authentication patterns, see the [official authentication documentation](https://google.github.io/adk-docs/tools-custom/authentication/).

## Production Considerations

This project is a development workbench. To move to a production environment, you will need to:

*   **Use a Persistent Session Service:** Replace the `InMemorySessionService` with a persistent one like `DatabaseSessionService` to remember conversation history and OAuth tokens.
*   **Securely Store Credentials:** Implement a more robust solution for storing OAuth tokens, such as encrypting them in the database or using a secret manager like Google Cloud Secret Manager.
*   **Deploy as a Service:** Replace the `cli.py` with a web server framework (like FastAPI or Flask) to deploy the agent as a web application or service.

## Project Files

*   **`agent.py`**: Defines the agent's tools, the "Orchestrator/Worker" structure, and the core authentication logic.
*   **`cli.py`**: Provides a local command-line interface for interacting with the agent and handling the client-side of the OAuth 2.0 flow.
*   **`helpers.py`**: Contains helper functions for the CLI to detect authentication requests from the agent.
*   **`requirements.txt`**: Lists the Python dependencies for the project.
*   **`.env`**: (You create this) Stores your Google Cloud credentials.
*   **`Mastering Workspace API Authentication in Google's ADK_ A Journey 2 Deep Dive.md`**: A detailed article explaining the architecture and implementation choices of this project.
*   **`authentication.md`**: The official ADK documentation on authentication.
