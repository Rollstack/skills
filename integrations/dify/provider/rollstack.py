from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

from rollstack_client.mcp import RollstackClient, RollstackError
from rollstack_client.tooling import CREDENTIAL_NAME


class RollstackProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        """Check the API key the way Rollstack says to: `GET /me` answers who a working key acts as."""
        try:
            with RollstackClient(credentials.get(CREDENTIAL_NAME)) as client:
                client.get_me()
        except RollstackError as error:
            raise ToolProviderCredentialValidationError(str(error)) from error
