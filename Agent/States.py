from pydantic import BaseModel , Field
from langgraph.graph import StateGraph ,START , END
from langgraph.checkpoint.memory import MemorySaver

from typing import TypedDict, Optional, Annotated
from operator import or_

class AgentState(TypedDict):
    issueimage:      str
    userEmail:       str
    location:        str
    issueClass:      Optional[str]
    issueScore:      Optional[float]
    errorMessage:    Optional[str]
    departmentEmail: Optional[str]
    departmentId:    Optional[str]
    emailDraft:      Optional[str]
    approval:        Optional[bool]
    editSuggestion:  Optional[str]
    emailSend:       Optional[bool]
    issueSaved:      Optional[bool]