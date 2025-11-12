# agent.py
import os
import json
from datetime import date
from typing import Optional

# ADK Imports for agent and tool definition
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool, ToolContext, AgentTool
from google.adk.auth import AuthConfig, AuthCredential, AuthCredentialTypes, OAuth2Auth
from fastapi.openapi import models as openapi_models

# Google API Client Imports
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- Configuration ---
# These are loaded from the environment where this module is imported (e.g., by cli.py)
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
TOKEN_CACHE_KEY = "google_chat_user_tokens"
SCOPES = [
    "https://www.googleapis.com/auth/chat.spaces.readonly",
    "https://www.googleapis.com/auth/chat.messages.readonly",
]

# --- Shared Authentication Objects ---
# These are needed by the get_credentials helper
auth_scheme = openapi_models.OAuth2(
    flows=openapi_models.OAuthFlows(
        authorizationCode=openapi_models.OAuthFlowAuthorizationCode(
            authorizationUrl="https://accounts.google.com/o/oauth2/auth",
            tokenUrl="https://oauth2.googleapis.com/token",
            scopes={scope: "" for scope in SCOPES},
        )
    )
)
auth_credential = AuthCredential(
    auth_type=AuthCredentialTypes.OAUTH2,
    oauth2=OAuth2Auth(client_id=GOOGLE_CLIENT_ID, client_secret=GOOGLE_CLIENT_SECRET),
)

# --- Centralized Authentication Helper ---
def get_credentials(tool_context: ToolContext) -> Optional[Credentials]:
    """
    Centralized function to get valid Google credentials.
    It handles caching, refreshing, and initiating the interactive auth flow.
    """
    creds = None
    if cached_token_info := tool_context.state.get(TOKEN_CACHE_KEY):
        try:
            creds = Credentials.from_authorized_user_info(cached_token_info, SCOPES)
        except Exception as e:
            print(f"Error loading cached credentials: {e}. Clearing cache.")
            tool_context.state.pop(TOKEN_CACHE_KEY, None)

    if creds and not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                tool_context.state[TOKEN_CACHE_KEY] = json.loads(creds.to_json())
            except Exception as e:
                print(f"Token refresh failed: {e}. Requesting new auth.")
                creds = None
        else:
            creds = None

    if not creds:
        if exchanged_credential := tool_context.get_auth_response(
            AuthConfig(auth_scheme=auth_scheme, raw_auth_credential=auth_credential)
        ):
            creds = Credentials(
                token=exchanged_credential.oauth2.access_token,
                refresh_token=exchanged_credential.oauth2.refresh_token,
                token_uri=auth_scheme.flows.authorizationCode.tokenUrl,
                client_id=auth_credential.oauth2.client_id,
                client_secret=auth_credential.oauth2.client_secret,
                scopes=SCOPES,
            )
            tool_context.state[TOKEN_CACHE_KEY] = json.loads(creds.to_json())

    if not creds:
        tool_context.request_credential(
            AuthConfig(auth_scheme=auth_scheme, raw_auth_credential=auth_credential)
        )
        return None
    
    return creds

# --- Robust Tool Functions ---
def search_all_chat_spaces(display_name_query: str, tool_context: ToolContext) -> dict:
    """
    Searches through ALL of a user's Google Chat spaces and filters them by a display name query.
    This tool handles authentication and pagination automatically.
    """
    if not (creds := get_credentials(tool_context)):
        return {"status": "pending", "message": "Awaiting user authentication."}
    try:
        service = build("chat", "v1", credentials=creds)
        all_spaces, page_token = [], None
        while True:
            response = service.spaces().list(pageSize=1000, pageToken=page_token).execute()
            all_spaces.extend(response.get("spaces", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                break
        
        filtered_spaces = [
            {"displayName": space.get("displayName"), "name": space.get("name")}
            for space in all_spaces
            if display_name_query.lower() in space.get("displayName", "").lower()
        ]

        if not filtered_spaces:
            return {"status": "success", "message": "No chat spaces found matching your query."}

        return {"status": "success", "found_spaces": filtered_spaces}
    except HttpError as e:
        return {"status": "error", "message": f"An API error occurred: {e.reason}"}

def list_space_messages(parent: str, tool_context: ToolContext, filter: Optional[str] = None) -> dict:
    """
    Lists messages in a given Google Chat space, handling pagination.
    'parent' is the resource name of the space, e.g., 'spaces/AAAAAAAAAAA'.
    'filter' can be used to search messages, e.g., 'from:me "important"'.
    """
    if not (creds := get_credentials(tool_context)):
        return {"status": "pending", "message": "Awaiting user authentication."}
    try:
        service = build("chat", "v1", credentials=creds)
        all_messages, page_token = [], None
        while len(all_messages) < 500: # Limit to 500 messages to protect context window
            page_size = min(500 - len(all_messages), 1000)
            request_args = {
                'parent': parent, 'pageSize': page_size,
                'orderBy': "createTime DESC", 'pageToken': page_token
            }
            if filter:
                request_args['filter'] = filter
            response = service.spaces().messages().list(**request_args).execute()
            messages = response.get('messages', [])
            for msg in messages:
                all_messages.append({
                    "author": msg.get("sender", {}).get("displayName"),
                    "text": msg.get("text"),
                    "createTime": msg.get("createTime")
                })
            page_token = response.get('nextPageToken')
            if not page_token:
                break
        return {"messages": all_messages}
    except HttpError as e:
        return {"status": "error", "message": f"An API error occurred: {e.reason}"}

# --- Agent Definitions (Orchestrator/Worker Pattern) ---

# 1. The "Worker" Agent for complex analysis
message_analysis_agent = LlmAgent(
    model="gemini-2.5-pro",
    name="message_analysis_agent",
    instruction=(
        "You are a specialist in analyzing Google Chat messages. "
        "Use the `list_space_messages` tool to retrieve messages and then "
        "answer the user's question based on their content. "
        "Provide concise and relevant answers."
    ),
    tools=[FunctionTool(func=list_space_messages)],
)

# 2. The "Orchestrator" Agent for routing and simple tasks
orchestrator_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="orchestrator_agent",
    instruction=(
        f"The current date is {date.today().isoformat()}.\n"
        "You are the primary assistant for Google Chat. Your job is to orchestrate tasks.\n"
        "1. First, use the `search_all_chat_spaces` tool to find a chat space if the user asks.\n"
        "2. Once a space is identified, if the user wants to ask questions about the *content* of that space "
        "(e.g., 'summarize', 'what was said about X', 'find messages from yesterday'), "
        "you MUST delegate the task by calling the `message_analysis_agent` tool. "
        "Pass the user's full query and the space ID (`parent` parameter) to the analysis agent."
    ),
    tools=[
        FunctionTool(func=search_all_chat_spaces),
        AgentTool(agent=message_analysis_agent)
    ],
)