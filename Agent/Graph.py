from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from Agent.Nodes import *
from Agent.States import AgentState
import base64
import uuid
def CivicIssueAgent():
    memory  = MemorySaver()
    Builder = StateGraph(AgentState)

    Builder.add_node("IssueClassify",        IssueClassify)
    Builder.add_node("ImageQuality",         ImageQuality)
    Builder.add_node("LowScoreEND",          LowScoreEND)
    Builder.add_node("DepartmentInfo",       DepartmentInfo)
    Builder.add_node("EmailGenerator",       EmailGenerator)
    Builder.add_node("HumanApproval",        HumanApproval)
    Builder.add_node("sendAndSaveEmailNode", sendAndSaveEmailNode)

    Builder.add_edge(START,            "IssueClassify")
    Builder.add_edge("IssueClassify",  "ImageQuality") 

    Builder.add_conditional_edges(
        "ImageQuality" ,ImageRouter,
        {"LowScoreEND":"LowScoreEND" ,"DepartmentInfo" :"DepartmentInfo"})

    Builder.add_edge("DepartmentInfo", "EmailGenerator")
    Builder.add_edge("EmailGenerator", "HumanApproval")

    Builder.add_conditional_edges(
        "HumanApproval", approvalRouter,
        {"sendAndSaveEmailNode": "sendAndSaveEmailNode", "EmailGenerator": "EmailGenerator"},
    )

    Builder.add_edge("sendAndSaveEmailNode", END)
    Builder.add_edge("LowScoreEND", END)

    graph = Builder.compile(
        checkpointer=memory,
        interrupt_before=["HumanApproval"]
    )
    return graph


