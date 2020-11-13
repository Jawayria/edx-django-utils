"""
Middleware for code_owner custom attribute
"""
import logging

from django.urls import resolve

from ..transactions import get_current_transaction
from ..utils import set_custom_attribute
from .utils import _get_catch_all_code_owner, get_code_owner_from_module, is_code_owner_mappings_configured

log = logging.getLogger(__name__)


class CodeOwnerMonitoringMiddleware:
    """
    Django middleware object to set custom attributes for the owner of each view.

    For instructions on usage, see:
    https://github.com/edx/edx-django-utils/blob/master/edx_django_utils/monitoring/docs/how_tos/add_code_owner_custom_attribute_to_an_ida.rst

    Custom attributes set:
    - code_owner: The owning team mapped to the current view.
    - code_owner_module: The module found from the request or current transaction.
    - code_owner_path_error: The error mapping by path, if code_owner isn't found in other ways.
    - code_owner_transaction_error: The error mapping by transaction, if code_owner isn't found in other ways.
    - code_owner_transaction_name: The current transaction name used to try to map to code_owner.
        This can be used to find missing mappings.

    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        self._set_code_owner_attribute(request)
        return response

    def process_exception(self, request, exception):
        self._set_code_owner_attribute(request)

    def _set_code_owner_attribute(self, request):
        """
        Sets the code_owner custom attribute for the request.
        """
        module = self._get_module_from_request(request)
        if module:
            code_owner = get_code_owner_from_module(module)
            if code_owner:
                set_custom_attribute('code_owner', code_owner)
                return

        code_owner = _get_catch_all_code_owner()
        if code_owner:
            set_custom_attribute('code_owner', code_owner)

    def _get_module_from_request(self, request):
        """
        Get the module from the request path or the current transaction.

        Side-effects:
            Sets code_owner_module custom attribute, used to determine code_owner.
            If module was not found, may set code_owner_path_error and/or
                code_owner_transaction_error custom attributes if applicable.

        Returns:
            str: module name or None if not found

        """
        if not is_code_owner_mappings_configured():
            return None

        module, path_error = self._get_module_from_request_path(request)
        if module:
            set_custom_attribute('code_owner_module', module)
            return module

        module, transaction_error = self._get_module_from_current_transaction()
        if module:
            set_custom_attribute('code_owner_module', module)
            return module

        # monitor errors if module was not found
        if path_error:
            set_custom_attribute('code_owner_path_error', path_error)
        if transaction_error:
            set_custom_attribute('code_owner_transaction_error', transaction_error)
        return None

    def _get_module_from_request_path(self, request):
        """
        Uses the request path to get the view_func module.

        Returns:
            (str, str): (module, error_message), where at least one of these should be None

        """
        try:
            view_func, _, _ = resolve(request.path)
            module = view_func.__module__
            return module, None
        except Exception as e:  # pylint: disable=broad-except
            return None, str(e)

    def _get_module_from_current_transaction(self):
        """
        Uses the current transaction to get the module.

        Side-effects:
            Sets code_owner_transaction_name custom attribute, used to determine code_owner

        Returns:
            (str, str): (module, error_message), where at least one of these should be None

        """
        try:
            # Example: openedx.core.djangoapps.contentserver.middleware:StaticContentServer
            transaction_name = get_current_transaction().name
            if not transaction_name:
                return None, 'No current transaction name found.'
            module = transaction_name.split(':')[0]
            set_custom_attribute('code_owner_transaction_name', transaction_name)
            return module, None
        except Exception as e:  # pylint: disable=broad-except
            return None, str(e)
