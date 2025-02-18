from pydantic import BaseModel, Field
from typing import Literal
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from typing_extensions import Annotated
import platform
import time
from playwright_stealth import stealth_sync

class ClickInput(BaseModel):
    bbox_id: int = Field(description="id to get the bounding box of the element to click")
    state : Annotated[dict, InjectedState]

class TypeTextInput(BaseModel):
    bbox_id: int = Field(description="id to get the bounding box of the element where we will type")
    text_content: str = Field(description="text content that we will type into the element")
    state : Annotated[dict, InjectedState]
    
class ScrollInput(BaseModel):
    direction: Literal["UP", "DOWN"] = Field(
        description="direction to scroll"
    )
    state : Annotated[dict, InjectedState]

    
@tool(args_schema = ClickInput)
def click(bbox_id: int, state: Annotated[dict, InjectedState]):
    "Click the bounding box of the element from id"

    page = state["page"]
    stealth_sync(page)


    try:
        bbox = state["bboxes"][bbox_id]
    except Exception:
        return f"Error: no bbox for : {bbox_id}"
    x, y = bbox["x"], bbox["y"]
    page.mouse.click(x, y)
    page.wait_for_load_state('networkidle')

    return f"Clicked {bbox_id}"

@tool(args_schema= ScrollInput)
def scroll(direction: str, state: Annotated[dict, InjectedState]):
    "Scroll window element up or down"
    page = state["page"]

    scroll_amount = 500
    scroll_direction = (
        -scroll_amount if direction.lower() == "up" else scroll_amount
    )
    page.evaluate(f"window.scrollBy(0, {scroll_direction})")
    stealth_sync(page)
    return f"Scrolled {direction} in Window"

@tool(args_schema = TypeTextInput)
def type_text(bbox_id: int, text_content: str, state: Annotated[dict, InjectedState]):
    "Type text into the element from id"
    page = state["page"]
    
 
    bbox = state["bboxes"][bbox_id]
    x, y = bbox["x"], bbox["y"]
    page.mouse.click(x, y)
    stealth_sync(page)
    # Check if MacOS
    select_all = "Meta+A" if platform.system() == "Darwin" else "Control+A"
    page.keyboard.press(select_all)
    page.keyboard.press("Backspace")
    page.keyboard.type(text_content)
    page.keyboard.press("Enter")
    stealth_sync(page)
    return f"Typed {text_content} and submitted"

@tool
def wait():
    "Wait for the page to load"
    
    sleep_time = 5
    time.sleep(sleep_time)
    return f"Waited for {sleep_time}s."

@tool
def go_back(state: Annotated[dict, InjectedState]):
    "Go back to the previous page if you are stuck"
    page = state["page"]
    page.go_back()
    stealth_sync(page)
    return f"Navigated back a page to {page.url}."

@tool
def to_google(state: Annotated[dict, InjectedState]):
    "Go to google.com to start over"
    page = state["page"]
    page.goto("https://www.google.com/")
    stealth_sync(page)
    return "Back at google"

