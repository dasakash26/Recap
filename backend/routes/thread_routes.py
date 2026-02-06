import os
import json
import logging
import traceback
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from langgraph.graph.state import RunnableConfig
from prisma import Json
from prisma.enums import ROLE
from slowapi import Limiter

from agent.executor import agent_builder
from core.config import settings
from services.db_service import db
from tools.auth import get_current_user
from .models import ChatReq, CreateThreadReq, UpdateThreadReq

router = APIRouter()
limiter = Limiter(key_func=lambda request: request.client.host)

RATE_LIMITS = {
    "create_thread": "30/minute",
    "get_threads": "60/minute",
    "update_thread": "20/minute",
    "delete_thread": "20/minute",
    "chat": "20/minute",
}


def sse_event(data: dict) -> str:
    """Format data as a Server-Sent Event."""
    return f"data: {json.dumps(data)}\n\n"


def build_citation(doc) -> dict:
    """Build citation dict from a document."""
    metadata = doc.metadata
    
    title = metadata.get("filename") or metadata.get("source", "Unknown Source")
    if "/" in title or "\\" in title:
        title = os.path.basename(title)
    
    page = metadata.get("page")
    page_number = page + 1 if page is not None else metadata.get("page_number", 1)
    
    return {
        "id": metadata.get("document_id", "unknown"),
        "title": title,
        "page": page_number,
        "total_pages": metadata.get("page_count"),
        "file_size": metadata.get("file_size"),
        "content": doc.page_content,
    }


def extract_docs_from_output(output) -> list:
    """Extract document list from tool output."""
    if hasattr(output, "artifact"):
        return output.artifact
    if isinstance(output, tuple) and len(output) == 2:
        return output[1]
    return []


async def verify_thread_access(thread_id: str, user_id: str):
    """Verify user has access to thread. Returns thread or raises HTTPException."""
    thread = await db.thread.find_unique(
        where={"id": thread_id},
        include={"folder": {"include": {"users": True}}},
    )

    if not thread or not thread.folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found",
        )

    owners = thread.folder.users or []
    if not any(u.id == user_id for u in owners):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this thread",
        )

    return thread


async def verify_folder_access(folder_id: str, user_id: str):
    """Verify user has access to folder. Returns folder or raises HTTPException."""
    folder = await db.folder.find_first(
        where={
            "id": folder_id,
            "users": {"some": {"id": user_id}},
        }
    )

    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found or access denied",
        )

    return folder


class StreamContext:
    """Accumulates streaming state during agent execution."""

    def __init__(self):
        self.full_response = ""
        self.citations = []

    def append_content(self, content: str):
        self.full_response += content

    def set_citations(self, citations: list):
        self.citations = citations


def process_stream_event(event: dict, ctx: StreamContext) -> str | None:
    """Process a single stream event, return SSE string if there's output."""
    event_type = event["event"]

    if event_type == "on_chat_model_stream":
        content = event["data"]["chunk"].content
        if content:
            ctx.append_content(content)
            return sse_event({"type": "message", "content": content})

    elif event_type == "on_tool_end" and event["name"] == "retrieve":
        docs = extract_docs_from_output(event["data"].get("output"))
        if docs:
            citations = [build_citation(doc) for doc in docs]
            ctx.set_citations(citations)
            return sse_event({"type": "citation", "citations": citations})

    return None


async def save_ai_response(thread_id: str, ctx: StreamContext):
    """Save the accumulated AI response to database."""
    if not ctx.full_response:
        return

    msg_data = {
        "content": ctx.full_response,
        "role": ROLE.AI,
        "chat_id": thread_id,
    }
    if ctx.citations:
        msg_data["citations"] = Json(ctx.citations)

    await db.message.create(data=msg_data)
    logging.info(f"Saved AI message to database for thread {thread_id}")


@limiter.limit(RATE_LIMITS["create_thread"])
@router.post("/")
async def create_thread(
    request: Request,
    data: CreateThreadReq,
    user=Depends(get_current_user),
):
    user_id = user.id
    try:
        await verify_folder_access(data.folder_id, user_id)

        thread = await db.thread.create(
            data={
                "name": data.thread_name,
                "folder_id": data.folder_id,
            }
        )

        return {
            "id": thread.id,
            "name": thread.name,
            "folderId": thread.folder_id,
            "createdAt": thread.createdAt,
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error creating thread for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@limiter.limit(RATE_LIMITS["get_threads"])
@router.get("/all")
async def get_threads(
    request: Request,
    folder_id: str,
    user=Depends(get_current_user),
):
    user_id = user.id
    try:
        folder = await db.folder.find_first(
            include={"threads": True},
            where={
                "id": folder_id,
                "users": {"some": {"id": user_id}},
            },
        )

        if not folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Folder not found",
            )

        return {"threads": folder.threads}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching threads for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@limiter.limit(RATE_LIMITS["get_threads"])
@router.get("/{thread_id}")
async def get_thread(
    request: Request,
    thread_id: str,
    user=Depends(get_current_user),
):
    user_id = user.id
    try:
        thread = await db.thread.find_first(
            include={"messages": True},
            where={
                "id": thread_id,
                "folder": {"is": {"users": {"some": {"id": user_id}}}},
            },
        )

        if not thread:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found",
            )

        return {"thread": thread}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching thread {thread_id} for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@limiter.limit(RATE_LIMITS["update_thread"])
@router.put("/{thread_id}")
async def update_thread(
    request: Request,
    thread_id: str,
    data: UpdateThreadReq,
    user=Depends(get_current_user),
):
    user_id = user.id
    try:
        await verify_thread_access(thread_id, user_id)

        updated_thread = await db.thread.update(
            where={"id": thread_id},
            data={"name": data.new_name},
        )

        if not updated_thread:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update thread",
            )

        return {
            "id": updated_thread.id,
            "name": updated_thread.name,
            "folderId": updated_thread.folder_id,
            "updatedAt": updated_thread.updatedAt,
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error updating thread {thread_id} for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@limiter.limit(RATE_LIMITS["delete_thread"])
@router.delete("/{thread_id}")
async def delete_thread(
    request: Request,
    thread_id: str,
    user=Depends(get_current_user),
):
    user_id = user.id
    try:
        await verify_thread_access(thread_id, user_id)
        await db.thread.delete(where={"id": thread_id})
        return {"detail": "Thread deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error deleting thread {thread_id} for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@limiter.limit(RATE_LIMITS["chat"])
@router.post("/{thread_id}/chat")
async def chat_in_thread(
    request: Request,
    thread_id: str,
    data: ChatReq,
    user=Depends(get_current_user),
):
    user_id = user.id
    message = data.message

    try:
        thread = await verify_thread_access(thread_id, user_id)

        config = RunnableConfig(
            configurable={
                "thread_id": thread_id,
                "user_id": user_id,
                "folder_id": thread.folder.id,
            }
        )

        async def stream_response() -> AsyncGenerator[str, None]:
            ctx = StreamContext()
            try:
                await db.message.create(
                    data={
                        "content": message,
                        "role": ROLE.USER,
                        "chat_id": thread_id,
                    }
                )

                async with AsyncRedisSaver.from_conn_string(
                    settings.redis_url
                ) as checkpointer:
                    agent = agent_builder.compile(checkpointer=checkpointer)

                    async for event in agent.astream_events(
                        {"messages": [HumanMessage(content=message)]},
                        version="v2",
                        config=config,
                    ):
                        sse_output = process_stream_event(event, ctx)
                        if sse_output:
                            yield sse_output

                await save_ai_response(thread_id, ctx)
                yield sse_event({"type": "done"})

            except Exception as e:
                logging.error(f"Error in stream for thread {thread_id}: {e}")
                traceback.print_exc()
                yield sse_event({"type": "error", "message": str(e)})

        return StreamingResponse(
            stream_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in chat endpoint for thread {thread_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@limiter.limit(RATE_LIMITS["get_threads"])
@router.get("/recent/all")
async def get_recent_threads(
    request: Request,
    user=Depends(get_current_user),
):
    user_id = user.id
    try:
        threads = await db.thread.find_many(
            where={"folder": {"users": {"some": {"id": user_id}}}},
            order={"updatedAt": "desc"},
            take=10,
            include={"folder": True},
        )

        return {
            "threads": [
                {
                    "id": t.id,
                    "name": t.name,
                    "folderId": t.folder_id,
                    "updatedAt": t.updatedAt,
                    "folderName": t.folder.name if t.folder else "Unknown",
                }
                for t in threads
            ]
        }
    except Exception as e:
        logging.error(f"Error fetching recent threads for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
