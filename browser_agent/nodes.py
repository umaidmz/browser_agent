from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from typing_extensions import Literal
from langgraph.prebuilt import ToolNode
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from langgraph.graph import END
from dotenv import load_dotenv

import time
import base64


from .tools import click, to_google, type_text, scroll, wait, go_back
from .state import AgentState

_ = load_dotenv()

with open("static/mark_page.js") as f:
    mark_page_script = f.read()


model = ChatOpenAI(model='gpt-4o-mini',temperature=0)
tools = [click, to_google, type_text, scroll, wait, go_back]
model = model.bind_tools(tools)

tool_node = ToolNode(tools)

system_prompt = SystemMessage("""
Imagine you are a robot browsing the web, just like humans. Now you need to complete a task. In each iteration, you will
receive an image observation that includes a screenshot of a webpage and some texts. This screenshot will
feature Numerical Labels placed in the TOP LEFT corner of each Web Element. Carefully analyze the visual
information to identify the Numerical Label corresponding to the Web Element that requires interaction, then follow
the guidelines and only choose ONE of the tool calls actions. You will also be given the history of previous action, you should
choose your next actions based on the steps taken previously. When you give a task you must figure out how to complete it.
                              
If you find captcha, you must wait for it to be solved before proceeding.                              

Key Guidelines You MUST follow:

* Action guidelines *
1) Execute only one action per iteration.
2) When clicking or typing, ensure to select the correct bounding box.
3) Numeric labels lie in the top-left corner of their corresponding bounding boxes and are colored the same.

* Web Browsing Guidelines *
1) Don't interact with useless web elements like Login, Sign-in, donation that appear in Webpages
2) Select strategically to minimize time wasted.
                                                                              
                    
You MUST execute only one action per iteration. If you have everything you need to answer the task then just responsd.
If you run more than one tool call you will be terminated. I will give you extra 10000$ for following rule.

""")

def call_model(
    state: AgentState,
    config: RunnableConfig,
) -> Command[Literal["tools", END]]:   # type: ignore
    response = model.invoke([system_prompt] + state["messages"], config)

    if response.tool_calls:
        return Command(
            goto="tools",
            update={"messages": [response]},
        )
    else:
        return Command(
            goto=END,
            update={"messages": [response]},
        )

def route_tool_response(state: AgentState) -> Command[Literal["mark_page", "agent"]]:
    messages = state["messages"]
    last_message = messages[-1]
    if "error" in last_message.content.lower():
        return Command(
            goto="agent",
        )
    else:
        return Command(
            goto="mark_page",
        )

def capture_annotated_screen(state: AgentState):
    time.sleep(3)
    page = state["page"]
    page.evaluate(mark_page_script)
    for _ in range(10):
        try:
            bboxes = page.evaluate("markPage()")
            break
        except Exception as e:
            # May be loading...
            print(e)
            time.sleep(3)
    screenshot = page.screenshot()
    page.evaluate("unmarkPage()")

    labels = []
    for i, bbox in enumerate(bboxes):
        text = bbox.get("ariaLabel") or ""
        if not text.strip():
            text = bbox["text"]
        el_type = bbox.get("type")
        labels.append(f'{i} (<{el_type}/>): "{text}"')
    bbox_descriptions = "\nValid Bounding Boxes:\n" + "\n".join(labels)
    # bbox_descriptions can be passed to the text for more accuracy.
    message = HumanMessage(
        content=[
            {"type": "text", "text": f"{state['input']} \n {bbox_descriptions}"},
            {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"},
        },
        ]
    )

    return {
        "bboxes": bboxes,
        "messages": [message],
    }



