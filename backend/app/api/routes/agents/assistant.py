"""FastAPI routes for ORCA Agent 6: AI Workspace Assistant."""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.agents.assistant_agent import AssistantAgent
from app.schemas.assistant_schemas import (
    AssistantApproveRequest,
    AssistantApproveResponse,
    AssistantChatRequest,
    AssistantChatResponse,
    ConversationHistoryResponse,
)

router = APIRouter(prefix="/agents/assistant", tags=["AI Workspace Assistant"])
assistant = AssistantAgent()


@router.post(
    "/chat",
    response_model=AssistantChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Interactive AI Workspace Chat",
    description="Conversational AI Workspace Assistant executing natural-language tasks with structured plans and real tool calls.",
)
async def chat_assistant(request: AssistantChatRequest) -> AssistantChatResponse:
    try:
        response = await assistant.chat(request)
        return response
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Assistant workspace error: {type(exc).__name__}: {str(exc)}",
        ) from exc


@router.post(
    "/chat/stream",
    summary="Streaming AI Workspace Chat (SSE)",
    description="Streams task planning, tool execution events, and final synthesis via Server-Sent Events.",
)
async def stream_assistant(request: AssistantChatRequest):
    return StreamingResponse(
        assistant.stream_chat(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/approve",
    response_model=AssistantApproveResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve or Deny Controlled Tool Execution",
    description="Explicit user authorization for high-impact tools (code changes, test execution, command running).",
)
async def approve_tool(request: AssistantApproveRequest) -> AssistantApproveResponse:
    try:
        response = await assistant.approve_tool_call(request)
        return response
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Approval execution error: {type(exc).__name__}: {str(exc)}",
        ) from exc


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Conversation History",
    description="Retrieve ordered message and tool execution history for a conversation session.",
)
async def get_conversation(conversation_id: str) -> ConversationHistoryResponse:
    history = assistant.get_history(conversation_id)
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found.",
        )
    return history


@router.get(
    "/tools",
    status_code=status.HTTP_200_OK,
    summary="List Registered Tools",
    description="Inspect available specialist and workspace tools with approval requirements.",
)
async def list_tools():
    return {"tools": assistant.tools.list_tools()}
