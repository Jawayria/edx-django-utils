"""
Code to create Registry of django app plugins

Please remember to expose any new public methods in the `__init__.py` file.
"""
import six

from .plugin_manager import PluginManager


class DjangoAppRegistry(PluginManager):
    """
    DjangoAppRegistry is a registry of django app plugins.
    """


def get_plugin_app_configs(project_type):
    return six.itervalues(DjangoAppRegistry.get_available_plugins(project_type))
