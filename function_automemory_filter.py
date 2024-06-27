"""
title: AutoMemory
author: Ricky Davis / spyci
author_url: https://github.com/ricky-davis/owui_functions
funding_url: https://github.com/ricky-davis/owui_functions
version: 1.2
"""

"""
This filter works by sending your message to the LLM with a special prompt to find and extract memories.
As such, use of this filter will increase inferencing costs.
"""

from pydantic import BaseModel
from typing import Optional

from apps.webui.models.users import Users
from apps.webui.routers.memories import add_memory, AddMemoryForm
from fastapi.requests import Request
from main import webui_app
from main import generate_chat_completions
import json


class Filter:
    def __init__(self):
        pass

    async def inlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        # Modify the request body or validate it before processing by the chat completion API.
        # This function is the pre-processor for the API where various checks on the input can be performed.
        # It can also modify the request before sending it to the API.
        # print(f"inlet:{__name__}")
        # print(f"inlet:body:{body}")
        # print(f"inlet:user:{user}")

        user = Users.get_user_by_id(__user__["id"])
        content = body["messages"][-1]["content"]

        try:
            formdata = {
                "model": body["model"],
                "stream": False,
                "messages": [
                    {
                        "role": "system",
                        "content": f"""
Parse the following content and extract personal information or significant details like names, ages, locations, preferences, desires, fears, medical history, appointments, or anything the user explicitly asks you to remember.
Be strict and only grab the most important memories.
Keep all memories short and simple, do not combine them, do not have long runon sentences.
Memories must *always* start with the word "User" or "User's".
It is preferrable to return nothing over returning garbage, useless memories. If anything is not specified, don't bother including it.
If user says "Your" or "You", they mean the Assistant.

Here are some examples of user messages and the memories they should create. Use these as a baseline for creating all memories:
"My name is Jeff" = "User's name is Jeff"
"Your name is now Bob" = "User has named Assistant 'Bob'"
"My favorite color is red" = "User's favorite color is red"
"I'm 28 years old" = "User's age is 28"
"I'm a sucker for a good sci-fi novel or an immersive RPG" = ["User loves sci-fi novels", "User loves immersive RPG's"]


Return a structured representation of the data in the schema below. Do not surround the JSON in codeblocks or ```
Content:
---
{content}
---
Answer in JSON using this schema:
{{
  // In format 'Users <property/detail> is <value>' like 'Users age is 30'
  memories: string[],
}}
JSON:
""",
                    }
                ],
            }

            result = await generate_chat_completions(formdata, user)
            if isinstance(result, dict):
                # print(f"{result=}")
                content = result["choices"][0]["message"]["content"]
            else:
                lines = []
                async for line in result.body_iterator:
                    print(f"{line=}")
                    lines.append(json.loads(line.decode("utf-8").strip()))
                # print(f"{lines=}")
                content = lines[0]["choices"][0]["message"]["content"]
            # print(f"{content=}")
            content = json.loads(content)
            # print(f"{content=}")

            memories = content["memories"]
            print(f"{memories=}")
            if len(memories):
                for memory in memories:
                    try:
                        memory_obj = await add_memory(
                            request=Request(scope={"type": "http", "app": webui_app}),
                            form_data=AddMemoryForm(content=memory),
                            user=user,
                        )
                        print(f"Memory Added: {memory_obj}")
                    except Exception as e:
                        print(f"Error adding memory {str(e)}")
            else:
                print("")

        except Exception as e:
            print(f"Error formatting memory {str(e)}")
            return body

        return body
