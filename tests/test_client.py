import httpx
import pytest
import respx

from aipolabs import Aipolabs
from aipolabs._constants import DEFAULT_AIPOLABS_BASE_URL, DEFAULT_MAX_RETRIES
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

API_KEY = "test_api_key"
BASE_URL = "https://api.aipolabs.xyz/v1/"


def create_test_client() -> Aipolabs:
    """Helper function to create a test client instance."""
    return Aipolabs(api_key=API_KEY, base_url=BASE_URL)


def test_client_initialization() -> None:
    client = create_test_client()
    assert client.api_key == API_KEY
    assert client.base_url == httpx.URL(BASE_URL)
    assert client.headers["x-api-key"] == API_KEY


def test_client_initialization_without_api_key() -> None:
    with pytest.raises(APIKeyNotFound):
        Aipolabs(api_key=None, base_url=BASE_URL)


def test_client_initialization_without_base_url() -> None:
    client = Aipolabs(api_key=API_KEY, base_url=None)
    assert client.base_url == httpx.URL(DEFAULT_AIPOLABS_BASE_URL)


@respx.mock
def test_search_apps_success() -> None:
    client = create_test_client()
    params = AipolabsSearchApps.SearchAppsParams.model_validate(
        {"intent": "test", "limit": 10, "offset": 0}
    )
    mock_response = [{"name": "Test App", "description": "Test Description"}]

    route = respx.get(f"{BASE_URL}apps/search").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    apps = client.search_apps(params)
    assert [app.model_dump() for app in apps] == mock_response
    assert route.call_count == 1, "should not retry"


@respx.mock
def test_search_functions_success() -> None:
    client = create_test_client()
    params = AipolabsSearchFunctions.SearchFunctionsParams.model_validate(
        {"intent": "test_intent", "limit": 10, "offset": 0}
    )
    mock_response = [{"name": "string", "description": "string"}]

    route = respx.get(f"{BASE_URL}functions/search").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    functions = client.search_functions(params)
    assert [function.model_dump() for function in functions] == mock_response
    assert route.call_count == 1, "should not retry"


@respx.mock
def test_get_function_definition_success() -> None:
    client = create_test_client()
    function_name = "TEST_FUNCTION"
    mock_response = {
        "type": "function",
        "function": {
            "name": "string",
            "strict": True,
            "description": "string",
            "parameters": {},
        },
    }
    route = respx.get(f"{BASE_URL}functions/{function_name}").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    response = client.get_function_definition(function_name)
    assert response == mock_response
    assert route.call_count == 1, "should not retry"


@respx.mock
def test_execute_function_success() -> None:
    client = create_test_client()
    function_name = "TEST_FUNCTION"
    function_parameters = {"param1": "value1"}
    mock_response = {"success": True, "data": "string"}
    route = respx.post(f"{BASE_URL}functions/{function_name}/execute").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    response = client.execute_function(function_name, function_parameters)
    assert response.model_dump(exclude_none=True) == mock_response
    assert route.call_count == 1, "should not retry"


# Test error handling for 401 Unauthorized
@respx.mock
def test_get_function_definition_unauthorized() -> None:
    client = create_test_client()
    function_name = "TEST_FUNCTION"

    route = respx.get(f"{BASE_URL}functions/{function_name}").mock(
        return_value=httpx.Response(401, json={"message": "Unauthorized"})
    )

    with pytest.raises(AuthenticationError) as exc_info:
        client.get_function_definition(function_name)

    assert "Unauthorized" in str(exc_info.value)
    assert route.call_count == 1, "should not retry"


# Test error handling for 403 Forbidden
@respx.mock
def test_get_function_definition_forbidden() -> None:
    client = create_test_client()
    function_name = "TEST_FUNCTION"

    route = respx.get(f"{BASE_URL}functions/{function_name}").mock(
        return_value=httpx.Response(403, json={"message": "Forbidden"})
    )

    with pytest.raises(PermissionError) as exc_info:
        client.get_function_definition(function_name)

    assert "Forbidden" in str(exc_info.value)
    assert route.call_count == 1, "should not retry"


# Test error handling for 404 Not Found
@respx.mock
def test_get_function_definition_not_found() -> None:
    client = create_test_client()
    function_name = "TEST_FUNCTION"

    route = respx.get(f"{BASE_URL}functions/{function_name}").mock(
        return_value=httpx.Response(404, json={"message": "Function not found"})
    )

    with pytest.raises(NotFoundError) as exc_info:
        client.get_function_definition(function_name)

    assert "Function not found" in str(exc_info.value)
    assert route.call_count == 1, "should not retry"


# Test error handling for 400 Bad Request
@respx.mock
def test_execute_function_bad_request() -> None:
    client = create_test_client()
    function_name = "TEST_FUNCTION"
    function_parameters = {"param1": "value1"}

    route = respx.post(f"{BASE_URL}functions/{function_name}/execute").mock(
        return_value=httpx.Response(400, json={"message": "Bad request"})
    )

    with pytest.raises(ValidationError) as exc_info:
        client.execute_function(function_name, function_parameters)

    assert "Bad request" in str(exc_info.value)
    assert route.call_count == 1, "should not retry"


# Test error handling for 429 Too Many Requests
@respx.mock
def test_execute_function_rate_limit_exceeded() -> None:
    client = create_test_client()
    function_name = "TEST_FUNCTION"
    function_parameters = {"param1": "value1"}

    route = respx.post(f"{BASE_URL}functions/{function_name}/execute").mock(
        return_value=httpx.Response(429, json={"message": "Rate limit exceeded"})
    )

    with pytest.raises(RateLimitError) as exc_info:
        client.execute_function(function_name, function_parameters)

    assert "Rate limit exceeded" in str(exc_info.value)
    assert route.call_count == DEFAULT_MAX_RETRIES, "should retry"


# Test error handling for 500 Internal Server Error
@respx.mock
def test_execute_function_server_error() -> None:
    client = create_test_client()
    function_name = "TEST_FUNCTION"
    function_parameters = {"param1": "value1"}

    route = respx.post(f"{BASE_URL}functions/{function_name}/execute").mock(
        return_value=httpx.Response(500, json={"message": "Internal server error"})
    )

    with pytest.raises(ServerError) as exc_info:
        client.execute_function(function_name, function_parameters)

    assert route.call_count == DEFAULT_MAX_RETRIES, "should retry"
    assert "Internal server error" in str(exc_info.value)


# Test error handling for unknown errors
@respx.mock
def test_execute_function_unknown_error() -> None:
    client = create_test_client()
    function_name = "TEST_FUNCTION"
    function_parameters = {"param1": "value1"}

    route = respx.post(f"{BASE_URL}functions/{function_name}/execute").mock(
        return_value=httpx.Response(418, json={"message": "I'm a teapot"})
    )

    with pytest.raises(UnknownError) as exc_info:
        client.execute_function(function_name, function_parameters)

    assert "Unexpected error occurred" in str(exc_info.value)
    assert "Status code: 418" in str(exc_info.value)
    assert route.call_count == DEFAULT_MAX_RETRIES, "should retry"


# Test handling of httpx.TimeoutException
@respx.mock
def test_execute_function_timeout_exception() -> None:
    client = create_test_client()
    function_name = "TEST_FUNCTION"
    function_parameters = {"param1": "value1"}

    route = respx.post(f"{BASE_URL}functions/{function_name}/execute").mock(
        side_effect=httpx.TimeoutException("Request timed out")
    )

    with pytest.raises(httpx.TimeoutException) as exc_info:
        client.execute_function(function_name, function_parameters)

    assert "Request timed out" in str(exc_info.value)
    assert route.call_count == DEFAULT_MAX_RETRIES, "should retry"


# Test handling of httpx.NetworkError
@respx.mock
def test_execute_function_network_error() -> None:
    client = create_test_client()
    function_name = "TEST_FUNCTION"
    function_parameters = {"param1": "value1"}

    route = respx.post(f"{BASE_URL}functions/{function_name}/execute").mock(
        side_effect=httpx.NetworkError("Network error")
    )

    with pytest.raises(httpx.NetworkError) as exc_info:
        client.execute_function(function_name, function_parameters)

    assert "Network error" in str(exc_info.value)
    assert route.call_count == DEFAULT_MAX_RETRIES, "should retry"


# Test retry logic for server errors (e.g., 500 Internal Server Error)
@respx.mock
def test_execute_function_retry_on_server_error() -> None:
    client = create_test_client()
    function_name = "test_function"
    function_parameters = {"param1": "value1"}
    mock_success_response = {"success": True, "data": "string"}

    # Simulate two server errors followed by a successful response
    route = respx.post(f"{BASE_URL}functions/{function_name}/execute").mock(
        side_effect=[
            httpx.Response(500, json={"message": "Internal server error"}),
            httpx.Response(500, json={"message": "Internal server error"}),
            httpx.Response(200, json=mock_success_response),
        ]
    )

    response = client.execute_function(function_name, function_parameters)
    assert route.call_count == DEFAULT_MAX_RETRIES, "should retry"
    assert response.model_dump(exclude_none=True) == mock_success_response


# Test that retries stop after the maximum number of attempts
@respx.mock
def test_execute_function_retry_exhausted() -> None:
    client = create_test_client()
    function_name = "TEST_FUNCTION"
    function_parameters = {"param1": "value1"}

    # Simulate server errors exceeding the retry limit
    route = respx.post(f"{BASE_URL}functions/{function_name}/execute").mock(
        side_effect=[
            httpx.Response(500, json={"message": "Internal server error"}),
            httpx.Response(500, json={"message": "Internal server error"}),
            httpx.Response(500, json={"message": "Internal server error"}),
            httpx.Response(500, json={"message": "Internal server error"}),
            httpx.Response(500, json={"message": "Internal server error"}),
        ]
    )

    with pytest.raises(ServerError) as exc_info:
        client.execute_function(function_name, function_parameters)

    assert route.call_count == DEFAULT_MAX_RETRIES, "should retry"
    assert "Internal server error" in str(exc_info.value)


@respx.mock
def test_handle_function_call_search_apps() -> None:
    client = create_test_client()
    function_name = AipolabsSearchApps.NAME
    function_parameters = {"query": "test"}
    mock_response = [{"name": "Test App", "description": "Test Description"}]

    route = respx.get(f"{BASE_URL}apps/search").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    response = client.handle_function_call(function_name, function_parameters)
    assert isinstance(response, list)
    assert len(response) == 1
    assert isinstance(response[0], AipolabsSearchApps.App)
    assert response[0].model_dump() == mock_response[0]
    assert route.call_count == 1, "should not retry"


@respx.mock
def test_handle_function_call_search_functions() -> None:
    client = create_test_client()
    function_name = AipolabsSearchFunctions.NAME
    function_parameters = {"query": "test"}
    mock_response = [{"name": "Test Function", "description": "Test Description"}]

    route = respx.get(f"{BASE_URL}functions/search").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    response = client.handle_function_call(function_name, function_parameters)
    assert isinstance(response, list)
    assert len(response) == 1
    assert isinstance(response[0], AipolabsSearchFunctions.Function)
    assert response[0].model_dump() == mock_response[0]
    assert route.call_count == 1, "should not retry"


@respx.mock
def test_handle_function_call_get_function_definition() -> None:
    client = create_test_client()
    function_name = AipolabsGetFunctionDefinition.NAME
    function_parameters = {"function_name": "TEST_FUNCTION"}
    mock_response = {"function": {"name": "Test Function"}}
    # note: the functio name for mock route here should be function_name in the function_parameters
    route = respx.get(f"{BASE_URL}functions/{function_parameters['function_name']}").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    response = client.handle_function_call(function_name, function_parameters)
    assert isinstance(response, dict)
    assert response == mock_response
    assert route.call_count == 1, "should not retry"


@respx.mock
def test_handle_function_call_execute_function() -> None:
    client = create_test_client()
    function_name = AipolabsExecuteFunction.NAME
    function_parameters = {"function_name": "TEST_FUNCTION", "function_input": {"param1": "value1"}}
    mock_response = {"success": True, "data": "string"}
    # note: the functio name for mock route here should be function_name in the function_parameters
    route = respx.post(f"{BASE_URL}functions/{function_parameters['function_name']}/execute").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    response = client.handle_function_call(function_name, function_parameters)
    assert isinstance(response, AipolabsExecuteFunction.FunctionExecutionResult)
    assert response.model_dump(exclude_none=True) == mock_response
    assert route.call_count == 1, "should not retry"


@respx.mock
def test_handle_function_call_execute_indexed_execution() -> None:
    client = create_test_client()
    function_name = "BRAVE_SEARCH__WEB_SEARCH"
    function_parameters = {"query": "test"}
    mock_response = {"success": True, "data": "string"}

    route = respx.post(f"{BASE_URL}functions/{function_name}/execute").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    response = client.handle_function_call(function_name, function_parameters)
    assert isinstance(response, AipolabsExecuteFunction.FunctionExecutionResult)
    assert response.model_dump(exclude_none=True) == mock_response
    assert route.call_count == 1, "should not retry"
