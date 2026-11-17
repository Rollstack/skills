"""The plugin as Dify's runtime loads it: the manifest, the provider, every tool file and every class."""

from __future__ import annotations

from dify_plugin import DifyPluginEnv
from dify_plugin.core.plugin_registration import PluginRegistration

from rollstack_client.operations import OPERATIONS


def test_the_runtime_loads_the_plugin(plugin_root):
    registration = PluginRegistration(DifyPluginEnv())

    (provider,) = registration.tools_configuration
    assert provider.identity.name == "rollstack"
    assert [credential.name for credential in provider.credentials_schema] == ["rollstack_api_key"]
    # An API key only: the plugin declares no OAuth client for an admin to set up
    assert provider.oauth_schema is None
    assert [tool.identity.name for tool in provider.tools] == list(OPERATIONS)

    assert registration.get_tool_provider_cls("rollstack").__name__ == "RollstackProvider"
    for operation in OPERATIONS:
        assert registration.get_tool_cls("rollstack", operation).__name__ == operation[0].upper() + operation[1:] + "Tool"


def test_the_plugin_asks_dify_for_no_permission(plugin_root):
    registration = PluginRegistration(DifyPluginEnv())

    # It calls no model, tool or app of the workspace, stores nothing and registers no endpoint
    assert registration.configuration.resource.permission is None
