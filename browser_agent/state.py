
from typing_extensions import Annotated, TypedDict,Sequence
from langchain_core.messages import BaseMessage
from typing import List
from langgraph.graph.message import add_messages
from playwright.sync_api import Page

class BBox(TypedDict):
    x: float
    y: float
    text: str
    type: str
    ariaLabel: str


class AgentState(TypedDict):
    input: str
    messages: Annotated[Sequence[BaseMessage], add_messages]
    bboxes : List[BBox]
    page: Page