# helpers.py

from google.adk.events import Event
from google.adk.auth import AuthConfig
from google.genai import types

def get_auth_request_function_call(event: Event) -> types.FunctionCall | None:
    """
    Get the special auth request function call from the event.
    This signals that the agent needs user authentication to proceed.
    """
    if not event.content or not event.content.parts:
        return None
    for part in event.content.parts:
        if (
            part
            and part.function_call
            and part.function_call.name == 'adk_request_credential'
            and event.long_running_tool_ids
            and part.function_call.id in event.long_running_tool_ids
        ):
            return part.function_call
    return None

def get_auth_config(auth_request_function_call: types.FunctionCall) -> AuthConfig:
    """
    Extracts the AuthConfig object from the arguments of the auth request function call.
    This object contains the necessary information to start the OAuth flow, like the auth_uri.
    """
    if not auth_request_function_call.args or not (
        auth_config_data := auth_request_function_call.args.get('authConfig')
    ):
        raise ValueError(
            f'Cannot get auth config from function call: {auth_request_function_call}'
        )
    if isinstance(auth_config_data, dict):
        return AuthConfig.model_validate(auth_config_data)
    elif not isinstance(auth_config_data, AuthConfig):
        raise ValueError(
            f'Auth config {auth_config_data} is not an instance of AuthConfig.'
        )
    return auth_config_data