# cli.py
import asyncio
from urllib.parse import urlencode
from dotenv import load_dotenv
import os

# Load environment variables BEFORE importing agent.py
load_dotenv()

# Import the final agent we want to run
from agent import orchestrator_agent
# Import the base Runner and InMemorySessionService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService, Session
from google.genai import types
from helpers import get_auth_request_function_call, get_auth_config

REDIRECT_URI = "http://localhost:8000/callback"

async def get_user_input(prompt: str) -> str:
    """Asynchronously gets input from the console."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, input, prompt)

async def handle_agent_run(runner: Runner, session: Session, user_query: str):
    """Handles a single turn of conversation, including the full auth flow if needed."""
    initial_message = types.Content(parts=[types.Part(text=user_query)])
    print("\nAgent > ", end="", flush=True)

    events_async = runner.run_async(
        session_id=session.id, user_id=session.user_id, new_message=initial_message
    )

    auth_request_function_call = None
    async for event in events_async:
        if text := (event.content.parts[0].text if event.content and event.content.parts else None):
            print(text, end="", flush=True)
        if auth_req := get_auth_request_function_call(event):
            auth_request_function_call = auth_req
            break
    
    if auth_request_function_call:
        auth_config = get_auth_config(auth_request_function_call)
        base_auth_uri = auth_config.exchanged_auth_credential.oauth2.auth_uri
        params = {'redirect_uri': REDIRECT_URI}
        auth_request_uri = f"{base_auth_uri}&{urlencode(params)}"

        print("\n\n--- AUTHENTICATION REQUIRED ---")
        print(f"\n1. Open this URL in your browser:\n\n   {auth_request_uri}\n")
        print("2. Sign in and grant permissions.")
        print("3. Copy the ENTIRE URL from your browser's address bar after redirection.")
        auth_response_uri = await get_user_input("\n4. Paste the full callback URL here and press Enter:\n> ")

        if not auth_response_uri.strip():
            print("Authentication cancelled.")
            return

        auth_config.exchanged_auth_credential.oauth2.auth_response_uri = auth_response_uri.strip()
        auth_config.exchanged_auth_credential.oauth2.redirect_uri = REDIRECT_URI

        auth_content = types.Content(
            role="user",
            parts=[
                types.Part(
                    function_response=types.FunctionResponse(
                        id=auth_request_function_call.id,
                        name=auth_request_function_call.name,
                        response=auth_config.model_dump(),
                    )
                )
            ],
        )

        print("\nAgent > ", end="", flush=True)
        events_async_after_auth = runner.run_async(
            session_id=session.id, user_id=session.user_id, new_message=auth_content
        )
        async for event in events_async_after_auth:
            if text := (event.content.parts[0].text if event.content and event.content.parts else None):
                print(text, end="", flush=True)
    
    print()

async def main():
    """Sets up the runner and manages the conversational loop."""
    if not os.getenv("GOOGLE_CLIENT_ID") or not os.getenv("GOOGLE_CLIENT_SECRET"):
        print("ERROR: Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your .env file or environment.")
        return

    app_name = "chat-agent-cli"
    session_service = InMemorySessionService()
    
    # --- THIS IS THE FIX ---
    # The base Runner constructor requires BOTH `app_name` and `agent`.
    runner = Runner(
        app_name=app_name,
        agent=orchestrator_agent,
        session_service=session_service
    )
    
    session = await session_service.create_session(app_name=app_name, user_id="cli-user")

    print("--- Google Chat Agent Initialized (Local CLI) ---")
    print("Type 'exit' or 'quit' to end.")

    while True:
        user_query = await get_user_input("\nYou > ")
        if user_query.lower() in ["exit", "quit"]:
            print("Ending session. Goodbye!")
            break
        
        await handle_agent_run(runner, session, user_query)

if __name__ == "__main__":
    asyncio.run(main())