from dotenv import load_dotenv
from openai import OpenAI

from aipolabs import Aipolabs, Function
from aipolabs.utils.logging import create_headline

load_dotenv()

# gets OPENAI_API_KEY from your environment variables
openai = OpenAI()
# gets AIPOLABS_API_KEY from your environment variables
aipolabs = Aipolabs()


def main() -> None:
    brave_search_function_definition = aipolabs.fetch_function_definition(
        Function.BRAVE_SEARCH__WEB_SEARCH
    )

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
    )
    content = response.choices[0].message.content
    tool_call = (
        response.choices[0].message.tool_calls[0]
        if response.choices[0].message.tool_calls
        else None
    )
    if content:
        print(create_headline("Response content"))
        print(content)
    if tool_call:
        print(create_headline("Tool call"))
        print(
            f"Function name: {tool_call.function.name}, arguments: {tool_call.function.arguments}"
        )
        result = aipolabs.execute_function(tool_call.function.name, tool_call.function.arguments)
        print(create_headline("Function execution result"))
        if result["success"]:
            print(result["data"])
        else:
            print(result["error"])


if __name__ == "__main__":
    main()