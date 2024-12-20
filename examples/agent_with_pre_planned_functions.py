import json

from dotenv import load_dotenv
from openai import OpenAI

from aipolabs import Aipolabs
from aipolabs.types.functions import Function
from aipolabs.utils._logging import create_headline

load_dotenv()

# gets OPENAI_API_KEY from your environment variables
openai = OpenAI()
# gets AIPOLABS_API_KEY from your environment variables
aipolabs = Aipolabs()


def main() -> None:
    brave_search_function_definition = aipolabs.functions.get(Function.BRAVE_SEARCH__WEB_SEARCH)

    print(create_headline("Brave search function definition"))
    print(brave_search_function_definition)

    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant with access to a variety of tools.",
            },
            {
                "role": "user",
                "content": "What is aipolabs?",
            },
        ],
        tools=[brave_search_function_definition],
        tool_choice="required",  # force the model to generate a tool call for demo purposes
    )
    tool_call = (
        response.choices[0].message.tool_calls[0]
        if response.choices[0].message.tool_calls
        else None
    )

    if tool_call:
        print(create_headline(f"Tool call: {tool_call.function.name}"))
        print(f"arguments: {tool_call.function.arguments}")
        # submit the selected function and its arguments to aipolabs backend for execution
        result = aipolabs.functions.execute(
            tool_call.function.name, json.loads(tool_call.function.arguments)
        )
        print(create_headline("Function execution result"))
        # result["success"] indicates whether the function execution (not the request itself) was successful
        if result.success:
            print(result.data)
        else:
            print(result.error)


if __name__ == "__main__":
    main()
