import httpx
import respx

from aipolabs import Aipolabs
from aipolabs.meta_functions import (
    AipolabsExecuteFunction,
    AipolabsGetFunctionDefinition,
    AipolabsSearchApps,
    AipolabsSearchFunctions,
)

from .utils import MOCK_BASE_URL, MOCK_LINKED_ACCOUNT_OWNER_ID


@respx.mock
def test_handle_function_call_search_apps(client: Aipolabs) -> None:
    mock_response = [{"name": "Test App", "description": "Test Description"}]

    route = respx.get(f"{MOCK_BASE_URL}apps/search").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    response = client.handle_function_call(
        AipolabsSearchApps.NAME,
        {"intent": "search apps"},
        linked_account_owner_id=MOCK_LINKED_ACCOUNT_OWNER_ID,
    )
    assert response == mock_response
    assert route.call_count == 1, "should not retry"


@respx.mock
def test_handle_function_call_search_functions(client: Aipolabs) -> None:
    mock_response = [{"name": "Test Function", "description": "Test Description"}]

    route = respx.get(f"{MOCK_BASE_URL}functions/search").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    response = client.handle_function_call(
        AipolabsSearchFunctions.NAME,
        {"app_names": ["TEST"], "intent": "search functions"},
        linked_account_owner_id=MOCK_LINKED_ACCOUNT_OWNER_ID,
    )
    assert response == mock_response
    assert route.call_count == 1, "should not retry"


@respx.mock
def test_handle_function_call_get_function_definition(client: Aipolabs) -> None:
    function_parameters = {"function_name": "TEST_FUNCTION"}
    mock_response = {"function": {"name": "Test Function"}}
    # note: the functio name for mock route here should be function_name in the function_parameters
    route = respx.get(
        f"{MOCK_BASE_URL}functions/{function_parameters['function_name']}/definition"
    ).mock(return_value=httpx.Response(200, json=mock_response))

    response = client.handle_function_call(
        AipolabsGetFunctionDefinition.NAME,
        function_parameters,
        linked_account_owner_id=MOCK_LINKED_ACCOUNT_OWNER_ID,
    )
    assert isinstance(response, dict)
    assert response == mock_response
    assert route.call_count == 1, "should not retry"


@respx.mock
def test_handle_function_call_meta_function_execution(client: Aipolabs) -> None:
    function_parameters = {
        "function_name": "BRAVE_SEARCH__WEB_SEARCH",
        "function_parameters": {"param1": "value1"},
    }
    mock_response = {"success": True, "data": "string"}
    # note: the functio name for mock route here should be function_name in the function_parameters
    route = respx.post(
        f"{MOCK_BASE_URL}functions/{function_parameters['function_name']}/execute"
    ).mock(return_value=httpx.Response(200, json=mock_response))

    response = client.handle_function_call(
        AipolabsExecuteFunction.NAME,
        function_parameters,
        linked_account_owner_id=MOCK_LINKED_ACCOUNT_OWNER_ID,
    )
    assert response == mock_response
    assert route.call_count == 1, "should not retry"


@respx.mock
def test_handle_function_call_direct_indexed_function_execution(client: Aipolabs) -> None:
    function_name = "BRAVE_SEARCH__WEB_SEARCH"
    function_parameters = {"query": "test"}
    mock_response = {
        "success": True,
        "data": {"results": [{"title": "Test Result"}], "metadata": None},
    }

    route = respx.post(f"{MOCK_BASE_URL}functions/{function_name}/execute").mock(
        return_value=httpx.Response(200, json=mock_response)
    )
    response = client.handle_function_call(
        function_name,
        function_parameters,
        linked_account_owner_id=MOCK_LINKED_ACCOUNT_OWNER_ID,
    )

    assert response == mock_response
    assert route.call_count == 1, "should not retry"
