from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx
from tenacity import (
    after_log,
    before_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from aipolabs._constants import (
    DEFAULT_AIPOLABS_BASE_URL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_MAX_WAIT,
    DEFAULT_RETRY_MIN_WAIT,
    DEFAULT_RETRY_MULTIPLIER,
)
from aipolabs._exceptions import (
    APIKeyNotFound,
    AuthenticationError,
    NotFoundError,
    PermissionError,
    RateLimitError,
    ServerError,
    UnknownError,
    ValidationError,
)
from aipolabs.meta_functions import (
    AipolabsExecuteFunction,
    AipolabsGetFunctionDefinition,
    AipolabsSearchApps,
    AipolabsSearchFunctions,
)
from aipolabs.utils._logging import SensitiveHeadersFilter

logger: logging.Logger = logging.getLogger(__name__)
logger.addFilter(SensitiveHeadersFilter())


retry_config = {
    "stop": stop_after_attempt(DEFAULT_MAX_RETRIES),
    "wait": wait_exponential(
        multiplier=DEFAULT_RETRY_MULTIPLIER,
        min=DEFAULT_RETRY_MIN_WAIT,
        max=DEFAULT_RETRY_MAX_WAIT,
    ),
    "retry": retry_if_exception_type(
        (
            ServerError,
            RateLimitError,
            UnknownError,
            httpx.TimeoutException,
            httpx.NetworkError,
        )
    ),
    "before": before_log(logger, logging.DEBUG),
    "after": after_log(logger, logging.DEBUG),
    "reraise": True,
}


class Aipolabs:

    def __init__(
        self, *, api_key: str | None = None, base_url: str | httpx.URL | None = None
    ) -> None:
        """Create and initialize a new Aipolabs client.

        Args:
            api_key: The API key to use for authentication.
            base_url: The base URL to use for the API requests.
            If values are not provided it will try to read from the corresponding environment variables.
            If no value found for api_key, it will raise APIKeyNotFound.
            If no value found for base_url, it will use the default value.
        """
        if api_key is None:
            api_key = os.environ.get("AIPOLABS_API_KEY")
        if api_key is None:
            raise APIKeyNotFound("The API key is not found.")
        self.api_key = api_key

        if base_url is None:
            base_url = os.environ.get("AIPOLABS_BASE_URL", DEFAULT_AIPOLABS_BASE_URL)
        self.base_url = self._enforce_trailing_slash(httpx.URL(base_url))
        # TODO: currently only openai is supported
        self.inference_provider = "openai"
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
        }
        self.client = httpx.Client(base_url=self.base_url, headers=self.headers)

    def handle_function_call(self, function_name: str, function_parameters: dict) -> Any:
        """Handle a function call.

        Args:
            function_name: The name of the function to call.
            function_parameters: The parameters of the function to call.

        Returns:
            The result of the function call.
        """
        logger.info(
            f"Handling function call with name: {function_name} and params: {function_parameters}"
        )
        if function_name == AipolabsSearchApps.NAME:
            search_apps_parameters = AipolabsSearchApps.validate_params(function_parameters)
            return self.search_apps(search_apps_parameters)
        elif function_name == AipolabsSearchFunctions.NAME:
            search_functions_parameters = AipolabsSearchFunctions.validate_params(
                function_parameters
            )
            return self.search_functions(search_functions_parameters)
        elif function_name == AipolabsGetFunctionDefinition.NAME:
            get_function_definition_parameters = AipolabsGetFunctionDefinition.validate_params(
                function_parameters
            )
            return self.get_function_definition(get_function_definition_parameters.function_name)
        elif function_name == AipolabsExecuteFunction.NAME:
            execute_function_parameters = AipolabsExecuteFunction.validate_params(
                function_parameters
            )
            return self.execute_function(
                execute_function_parameters.function_name,
                execute_function_parameters.function_parameters,
            )
        else:
            # TODO: check function exist if not return AipolabsFunctionCallType.UNKNOWN
            return self.execute_function(function_name, function_parameters)

    @retry(**retry_config)
    def search_apps(self, params: AipolabsSearchApps.AppSearchParams) -> Any:
        # TODO: exclude_unset
        logger.info(f"Searching apps with params: {params.model_dump(exclude_unset=True)}")
        response = self.client.get(
            "apps/search",
            params=params.model_dump(exclude_unset=True),
        )

        return self._handle_response(response)

    @retry(**retry_config)
    def search_functions(self, params: AipolabsSearchFunctions.FunctionSearchParams) -> Any:
        logger.info(f"Searching functions with params: {params.model_dump(exclude_unset=True)}")
        response = self.client.get(
            "functions/search",
            params=params.model_dump(exclude_unset=True),
        )

        return self._handle_response(response)

    @retry(**retry_config)
    def get_function_definition(self, function_name: str) -> Any:
        logger.info(f"Getting function definition of {function_name}")
        response = self.client.get(
            f"functions/{function_name}",
            params={"inference_provider": self.inference_provider},
        )

        return self._handle_response(response)

    @retry(**retry_config)
    def execute_function(self, function_name: str, function_parameters: dict) -> Any:
        logger.info(
            f"Executing function with name: {function_name} and params: {function_parameters}"
        )
        request_body = {
            "function_input": function_parameters,
        }
        response = self.client.post(
            f"functions/{function_name}/execute",
            json=request_body,
        )

        return self._handle_response(response)

    def _enforce_trailing_slash(self, url: httpx.URL) -> httpx.URL:
        if url.raw_path.endswith(b"/"):
            return url
        return url.copy_with(raw_path=url.raw_path + b"/")

    def _handle_response(self, response: httpx.Response) -> Any:
        """Handle the API response and raise appropriate exceptions if needed."""
        try:
            response_json = response.json() if response.content else None
        except json.JSONDecodeError:
            response_json = None

        error_message: str
        if isinstance(response_json, dict):
            error_message = str(
                response_json.get("message") or response_json.get("error") or response.text
            )
        else:
            error_message = response.text

        if response.status_code == 200:
            return response_json
        # TODO: cross-check with backend
        if response.status_code == 401:
            raise AuthenticationError(error_message, response.status_code, response.text)
        elif response.status_code == 403:
            raise PermissionError(error_message, response.status_code, response.text)
        elif response.status_code == 404:
            raise NotFoundError(error_message, response.status_code, response.text)
        elif response.status_code == 400:
            raise ValidationError(error_message, response.status_code, response.text)
        elif response.status_code == 429:
            raise RateLimitError(error_message, response.status_code, response.text)
        elif 500 <= response.status_code < 600:
            raise ServerError(error_message, response.status_code, response.text)
        else:
            raise UnknownError(
                f"Unexpected error occurred. Status code: {response.status_code}",
                response.status_code,
                response.text,
            )
