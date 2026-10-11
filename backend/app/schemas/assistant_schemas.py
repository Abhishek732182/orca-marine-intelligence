"""Pydantic schemas for ORCA Agent 6: AI Workspace Assistant."""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
from pydantic import BaseModel, Field


class ToolCallRecord(BaseModel):
    """Record of a tool call executed or pending approval by the assistant."""

    call_id: str = Field(default_factory=lambda: str(uuid4()))
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"  # "pending", "executing", "completed", "failed", "denied", "waiting_approval"
    output: Any = None
    error: str | None = None
    duration_ms: float | None = None
    requires_approval: bool = False
    diff: str | None = None


class ExecutionPlanStep(BaseModel):
    """Individual step in the assistant's structured execution plan."""

    step_id: int
    description: str
    tool_name: str | None = None
    status: str = "pending"  # "pending", "in_progress", "completed", "failed", "skipped"
    result_summary: str | None = None


class ChatMessage(BaseModel):
    """Chat message in the conversational workspace."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    plan: list[ExecutionPlanStep] | None = None
    tool_calls: list[ToolCallRecord] | None = None
    agent_results: dict[str, Any] | None = None
    evidence_summary: dict[str, Any] | None = None
    limitations: list[str] | None = None


class AssistantChatRequest(BaseModel):
    """User input to the AI Workspace Assistant."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Natural-language task or prompt",
    )
    conversation_id: str | None = Field(
        default=None,
        description="Conversation session ID (creates a new session if omitted)",
    )
    client_context: dict[str, Any] | None = Field(
        default=None,
        description="Optional client state or coordinates context",
    )


class AssistantChatResponse(BaseModel):
    """Structured response from the AI Workspace Assistant."""

    conversation_id: str
    response_message: ChatMessage
    plan: list[ExecutionPlanStep] = Field(default_factory=list)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    agent_results: dict[str, Any] = Field(default_factory=dict)
    evidence_summary: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    status: str = "completed"  # "completed", "waiting_approval", "error"
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class AssistantApproveRequest(BaseModel):
    """Approval or denial decision for a controlled tool call."""

    conversation_id: str
    call_id: str
    decision: str = Field(
        ...,
        description="'approve' to permit execution, 'deny' to cancel the tool call",
    )


class AssistantApproveResponse(BaseModel):
    """Result of an approved or denied tool call."""

    conversation_id: str
    call_id: str
    status: str  # "completed", "denied", "failed"
    result: Any = None
    error: str | None = None
    updated_message: ChatMessage | None = None


class ConversationHistoryResponse(BaseModel):
    """Conversation history retrieved for a session."""

    conversation_id: str
    title: str
    created_at: str
    updated_at: str
    messages: list[ChatMessage] = Field(default_factory=list)
    tool_history: list[ToolCallRecord] = Field(default_factory=list)
