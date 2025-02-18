from dotenv import load_dotenv
from gevent import monkey
monkey.patch_all()
from langgraph.graph import StateGraph, END
from langchain_core.runnables.graph import CurveStyle, MermaidDrawMethod, NodeStyles
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage

from playwright.sync_api import sync_playwright, Page
from playwright_stealth import stealth_sync

import time
import base64

from browser_agent.nodes import call_model, capture_annotated_screen, route_tool_response, tool_node, mark_page_script
from browser_agent.state import AgentState

_ = load_dotenv()


# Define a new graph
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)
workflow.add_node("mark_page", capture_annotated_screen)
workflow.add_node("route_tool_response", route_tool_response)

workflow.set_entry_point("agent")

workflow.add_edge("tools", "route_tool_response")
workflow.add_edge("mark_page", "agent")

# Now we can compile and visualize our graph
graph = workflow.compile()
graph.get_graph().draw_mermaid_png(
            draw_method=MermaidDrawMethod.API,
            output_file_path="static/graph.png",
        )
# Helper function for formatting the stream nicely
def print_stream(stream):
    for s in stream:
        message = s["messages"][-1]
        if isinstance(message, HumanMessage):
            print("------------Human Message------------")
            print(message.content[0]['text'])
        if isinstance(message, SystemMessage):
            print("------------System Message------------")
            print(message.content)
        elif isinstance(message, ToolMessage):
            print("------------Tool Message------------")
            print(message.content)
        elif isinstance(message, AIMessage):
            print("------------AI Message------------")
            if message.tool_calls:
                print(f"Calling tool: {message.tool_calls[0]['name']}")
            else:
                print(message.content)
            

def annotate(page: Page):
    page.evaluate(mark_page_script)
    for _ in range(10):
        try:
            bboxes = page.evaluate("markPage()")
            break
        except Exception:
            # May be loading...
            time.sleep(3)
    screenshot = page.screenshot()
    try:
        page.evaluate("unmarkPage()")
    except Exception:
        page.evaluate(mark_page_script)
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

    return bboxes, base64.b64encode(screenshot).decode(), bbox_descriptions

if __name__ == "__main__":
    browser = sync_playwright().start()
    browser = browser.chromium.launch(headless=False, args=["--start-maximized"])
    context = browser.new_context(no_viewport=True)
    page =  context.new_page()
    _ =  page.goto("https://www.google.com")
    stealth_sync(page)
    while True:    
        input_str = input("Enter a query: ")
        
        
        bboxes, img, bbox_descriptions = annotate(page)
        
        message = HumanMessage(
            content=[
                {"type": "text", "text": f"{input_str} \n {bbox_descriptions}"},
                {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img}"},
            },
            ]
        )

        inputs = {"messages": [message], "page": page, "input": input_str, "bboxes": bboxes}
        
        print_stream(graph.stream(inputs, stream_mode="values",  config={"recursion_limit": 50}))

        _ =  page.goto("https://www.google.com")
        stealth_sync(page)
        break_input = input("Do you want to continue? (y/n): ")
        if break_input == "n":
            break
    