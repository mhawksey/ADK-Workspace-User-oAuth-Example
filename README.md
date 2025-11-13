# **Google Chat Agent with ADK (Journey 2) - User Authentication Example**

This project is the companion repository for the AppsScriptPulse article: [**"Mastering Workspace API Authentication in ADK Agents with a Reusable Pattern"**](https://pulse.appsscript.info/p/2025/11/mastering-workspace-api-authentication-in-adk-agents-with-a-reusable-pattern/).

It demonstrates how to build a sophisticated, multi-capability Google Chat agent using Google's Agent Development Kit (ADK). It specifically follows the "Journey 2" or "Crafted Tool" approach (as defined in the [official ADK authentication documentation](https://google.github.io/adk-docs/tools-custom/authentication/)), favouring custom tool implementation (FunctionTool) over auto-generation.

The core of this example is a reusable, robust authentication pattern in agent.py that manages the user-centric OAuth 2.0 flow for Google Workspace APIs. The agent can search Google Chat spaces and list messages within a space, handling authentication and pagination automatically.

This repository is designed as a high-fidelity local workbench, perfect for development, debugging, and rapid iteration.

## **Features**

* **Custom Tool Implementation ("Journey 2"):** Uses `FunctionTool` to wrap custom Python functions for fine-grained control.  
* **Reusable Authentication Pattern:** A centralised `get_credentials` function in agent.py manages the entire OAuth 2.0 lifecycle (caching, refresh, and user consent flow).  
* **Robust Tools:** The `search_all_chat_spaces` tool correctly handles API pagination, abstracting this complexity away from the LLM.  
* **Orchestrator/Worker Architecture:** Uses a fast, cost-effective model (`gemini-2.5-flash`) to orchestrate tasks and a more powerful model (`gemini-2.5-pro`) for specialised analysis.  
* **Local Test Harness:** A `cli.py` script provides a command-line interface for easy local testing and interaction with the agent.

## **Architectural Overview**

This agent uses a two-agent "Orchestrator/Worker" structure:

1. **Orchestrator Agent (orchestrator_agent):** The primary, user-facing agent. It uses `gemini-2.5-flash` to handle routing and simple tasks, like using the search_all_chat_spaces tool.  
2. **Worker Agent (message_analysis_agent):** A specialised agent using `gemini-2.5-pro`. When a user wants to analyse the *content* of a specific space, the orchestrator delegates the task to this agent, which uses the list_space_messages tool.

This separation of concerns optimises for both cost and performance.

## **Getting Started**

Follow these steps to run the agent on your local machine.

### **Prerequisites**

* Python 3.10+  
* A Google Cloud project.

### **1. Google Cloud Project Setup**

1. **Enable API:** In your Google Cloud project, [enable the "Google Chat API"](https://console.cloud.google.com/apis/library/chat.googleapis.com).  
2. **Configure OAuth Consent Screen:** Go to [APIs & Services > OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent).  
   * Select **External** and create the screen.  
   * Add the following required scopes:  
     * https://www.googleapis.com/auth/chat.spaces.readonly  
     * https://www.googleapis.com/auth/chat.messages.readonly  
   * Add your Google account as a **Test User**.  
3. **Create OAuth 2.0 Credentials:**  
   * Go to [APIs & Services > Credentials](https://console.cloud.google.com/apis/credentials).  
   * Click **Create Credentials** > **OAuth 2.0 Client ID**.  
   * Select **Web Application** for the application type.  
   * Under **Authorised redirect URIs**, add: http://localhost:8000/callback  
   * Click **Create**.  
   * Copy the **Client ID** and **Client Secret**. You will need these in step 4.

### **2. Clone the Repository**

```
git clone https://github.com/mhawksey/adk-workspace-user-oauth-example.git
cd adk-workspace-user-oauth-example
```

### **3. Create a Virtual Environment (Recommended)**

```
# For macOS/Linux  
python3 -m venv venv  
source venv/bin/activate

# For Windows  
python -m venv venv  
.\venv\Scripts\activate
```

### **4. Install Dependencies**

```
pip install -r requirements.txt
```

### **5. Set Environment Variables**

Create a file named .env in the root of the project directory. Add the Client ID and Client Secret you got from step 1:

```
GOOGLE_CLIENT_ID="your-google-client-id.apps.googleusercontent.com"  
GOOGLE_CLIENT_SECRET="your-google-client-secret"
```

## **Running the Agent**

Run the local command-line interface:

```
python cli.py
```

The agent will start. The first time you use a command that requires authentication (e.g., "search for a space named 'My Project'"), the agent will prompt you to authenticate.

**Authentication Flow:**

1. The agent will print a URL to the console.  
2. Open this URL in your browser.  
3. Sign in with the Google account you added as a "Test User".  
4. Grant the requested permissions (Chat spaces and messages).  
5. After authorising, your browser will be redirected to a localhost URL. **Copy the entire URL** from your browser's address bar.  
6. Paste the full URL back into the terminal and press Enter.

The agent will then complete your request. Your authentication token will be cached in memory for the duration of the session.

## **Authentication Pattern ("Journey 2")**

This project demonstrates the ADK's "Journey 2" authentication pattern, where the developer builds the authentication logic directly into the tool. This contrasts with "Journey 1", which relies on auto-generation from an OpenAPI spec.

The "Journey 2" approach provides maximum control. The core logic is in the get_credentials function in agent.py. When a tool is called:

1. **Check Cache:** It first checks tool_context.state for a valid, cached token.  
2. **Refresh Token:** If a token exists but is expired, it uses the refresh token to get a new one and updates the cache.  
3. **Check for Auth Response:** If no token is found, it checks if the user has just completed the OAuth consent flow (tool_context.get_auth_response()).  
4. **Request Credentials:** If all else fails, it formally requests credentials via tool_context.request_credential(). This pauses the agent and signals cli.py to initiate the interactive user flow described above.

This robust pattern is completely reusable. You can adapt it to any Google Workspace API by simply changing the SCOPES constant in agent.py.

For more details on ADK authentication, refer to the [official authentication documentation](https://google.github.io/adk-docs/tools-custom/authentication/).

## **Project Files**

* **agent.py**: Defines the agent's tools (`search_all_chat_spaces`, `list_space_messages`), the "Orchestrator/Worker" structure, and the core get_credentials authentication logic.  
* **cli.py**: Provides the local command-line interface for interacting with the agent. It also handles the *client-side* of the OAuth 2.0 flow (prompting the user and sending the response back to the agent).  
* **helpers.py**: Contains helper functions for the CLI to detect authentication requests from the agent.  
* **requirements.txt**: Lists the Python dependencies for the project.

## **Production Considerations**

This project is a development workbench. To move to a production environment, you would need to:

* **Use a Persistent Session Service:** Replace the InMemorySessionService with a persistent one like DatabaseSessionService (e.g., backed by PostgreSQL) or VertexAiSessionService to remember conversation history and OAuth tokens across sessions.  
* **Securely Store Credentials:** Implement a more robust solution for storing user OAuth tokens, such as encrypting them in the database or using a dedicated secret manager.  
* **Deploy as a Service:** Replace the `cli.py` with a web server framework (like FastAPI or Flask) to deploy the agent as a web application or integrate it into a production environment like Vertex AI Agent Engine.

## **License**

This project is licensed under the Apache 2.0 License. See the [LICENSE](LICENSE) file for details.

*Disclaimer: This is not an officially supported Google product.*
