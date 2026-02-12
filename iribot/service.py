"""Main FastAPI application"""
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from .agent import agent
from .config import settings, update_settings
from .executor import tool_executor
from .models import (
    AppConfig,
    AppConfigUpdate,
    ChatRequest,
    MessageRecord,
    SessionCreate,
    SystemPromptGenerateRequest,
    SystemPromptGenerateResponse,
    ToolCallRecord,
)
from .prompt_generator import generate_system_prompt
from .session_manager import session_manager
from .tools.execute_command import stop_all_shell_sessions


@asynccontextmanager
async def lifespan(_app: FastAPI):
    tool_executor.register_shutdown_handler(stop_all_shell_sessions)
    yield
    tool_executor.run_shutdown_handlers()


def _sse_data(data: dict) -> str:
    """Create SSE data string with JSON serialization"""
    return f"data: {json.dumps(data, default=str)}\n\n"


# Initialize FastAPI app
app = FastAPI(
    title=settings.app_title,
    debug=settings.debug,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Prompt Generation Endpoints
@app.post("/api/prompt/generate")
def generate_prompt(request: SystemPromptGenerateRequest):
    """
    Generate a system prompt with current date/time, safety policies, and tool descriptions

    Args:
        request: GeneratePromptRequest with optional custom_instructions

    Returns:
        Generated system prompt with metadata
    """
    from .prompt_generator import get_current_datetime_info

    prompt = generate_system_prompt(
        custom_instructions=request.custom_instructions
    )

    return SystemPromptGenerateResponse(
        system_prompt=prompt,
        datetime_info=get_current_datetime_info()
    )


@app.get("/api/prompt/generate")
def generate_prompt_get(custom_instructions: str = ""):
    """
    Generate a system prompt (GET endpoint for convenience)

    Query Parameters:
        custom_instructions: Optional custom instructions

    Returns:
        Generated system prompt with metadata
    """
    from .prompt_generator import get_current_datetime_info

    prompt = generate_system_prompt(
        custom_instructions=custom_instructions
    )

    return SystemPromptGenerateResponse(
        system_prompt=prompt,
        datetime_info=get_current_datetime_info()
    )


@app.get("/api/prompt/text")
def generate_prompt_text(custom_instructions: str = ""):
    """
    Generate a system prompt and return as plain text

    Query Parameters:
        custom_instructions: Optional custom instructions

    Returns:
        Plain text system prompt
    """
    from fastapi.responses import PlainTextResponse

    prompt = generate_system_prompt(
        custom_instructions=custom_instructions
    )

    return PlainTextResponse(content=prompt)


@app.get("/api/prompt/current")
def get_current_prompt():
    """Get the current system prompt for viewing"""
    from fastapi.responses import PlainTextResponse

    prompt = generate_system_prompt()
    return PlainTextResponse(content=prompt)


@app.post("/api/sessions")
def create_session(request: SessionCreate):
    """Create a new chat session"""
    session = session_manager.create_session(title=request.title)
    return session.model_dump()


@app.get("/api/sessions")
def list_sessions():
    """List all chat sessions"""
    sessions = session_manager.list_sessions()
    return [s.model_dump() for s in sessions]


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    """Get a specific session with all records"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return session.model_dump()


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str):
    """Delete a session"""
    success = session_manager.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "success"}


@app.get("/api/tools/status")
def get_tools_status():
    """Get status of all tools"""
    return tool_executor.get_all_tool_statuses()


@app.get("/api/config")
def get_app_config():
    """Get runtime app configuration."""
    return AppConfig(**settings.model_dump()).model_dump()


@app.put("/api/config")
def update_app_config(request: AppConfigUpdate):
    """Update runtime app configuration."""
    updates = request.model_dump(exclude_none=True)
    updated = update_settings(updates)
    agent.reload_config()
    return AppConfig(**updated.model_dump()).model_dump()


# Streaming chat endpoint
@app.post("/api/chat/stream")
def chat_stream(request: ChatRequest):
    """Send a message and get AI response with streaming support"""

    def generate():
        # Get session
        session = session_manager.get_session(request.session_id)
        if not session:
            yield _sse_data({'type': 'error', 'content': 'Session not found'})
            return

        # Add user message record
        user_record = MessageRecord(
            role="user",
            content=request.message,
            binary_content=request.binary_content
        )
        session_manager.add_record(request.session_id, user_record.model_dump())

        # Send user record event
        yield _sse_data({'type': 'record', 'record': user_record.model_dump()})

        try:
            # Tool calling loop
            max_iterations = 50

            for iteration in range(max_iterations):
                # Re-fetch messages from session (with truncation applied each time)
                # This ensures older tool calls are truncated as more calls are made
                messages = session_manager.get_messages_for_llm(request.session_id)

                tool_calls = []

                # Generate fresh system prompt for each request to include latest skills
                fresh_system_prompt = generate_system_prompt()

                reasoning_content = None
                for chunk in agent.chat_stream(
                    messages=messages,
                    system_prompt=fresh_system_prompt,
                    images=(
                        [bc.get("data") for bc in (request.binary_content or []) if bc.get("data")]
                        if iteration == 0 else None
                    )
                ):
                    if chunk["type"] == "reasoning_start":
                        yield _sse_data({'type': 'reasoning_start'})
                    elif chunk["type"] == "reasoning":
                        yield _sse_data({'type': 'reasoning', 'content': chunk['content']})
                    elif chunk["type"] == "reasoning_end":
                        yield _sse_data({'type': 'reasoning_end'})
                    elif chunk["type"] == "content":
                        yield _sse_data({'type': 'content', 'content': chunk['content']})
                    elif chunk["type"] == "done":
                        tool_calls = chunk.get("tool_calls", [])
                        content = chunk["content"]
                        reasoning_content = chunk["reasoning_content"]

                if not tool_calls:
                    # No tool calls, save and finish
                    if content or reasoning_content:
                        assistant_record = MessageRecord(
                            role="assistant",
                            content=content,
                            reasoning_content=reasoning_content
                        )
                        session_manager.add_record(request.session_id, assistant_record.model_dump())
                        yield _sse_data({'type': 'record', 'record': assistant_record.model_dump()})

                    yield _sse_data({'type': 'done'})
                    return

                yield _sse_data({
                    'type': 'tool_calls_start',
                    'tool_calls': tool_calls,
                    'reasoning_content': reasoning_content
                })

                # Save the assistant message to session (tool_calls are stored separately)
                assistant_record = MessageRecord(
                    role="assistant",
                    content=content,
                    reasoning_content=reasoning_content
                )
                session_manager.add_record(request.session_id, assistant_record.model_dump())
                yield _sse_data({'type': 'record', 'record': assistant_record.model_dump()})

                # Execute tool calls
                for tool_call in tool_calls:
                    tool_name = tool_call["function"]["name"]
                    tool_args_str = tool_call["function"]["arguments"]
                    tool_id = tool_call["id"]

                    # Parse arguments
                    try:
                        tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
                    except json.JSONDecodeError:
                        tool_args = {"raw_arguments": tool_args_str}

                    # Signal tool execution starting
                    yield _sse_data({
                        'type': 'tool_start',
                        'tool_call_id': tool_id,
                        'tool_name': tool_name,
                        'arguments': tool_args,
                        'success': None
                    })

                    # Execute the tool
                    result = agent.process_tool_call(
                        tool_name,
                        tool_args_str,
                        context={"session_id": request.session_id}
                    )

                    # Create and save tool call record
                    if result.get("success"):
                        tool_result = result.get("result")
                    else:
                        tool_result = result.get("result") or result.get("error")
                    tool_record = ToolCallRecord(
                        tool_call_id=tool_id,
                        tool_name=tool_name,
                        arguments=tool_args,
                        result=tool_result,
                        success=result.get("success", False)
                    )
                    session_manager.add_record(request.session_id, tool_record.model_dump())

                    # Send tool result
                    yield _sse_data({'type': 'tool_result', 'record': tool_record.model_dump()})

            # Max iterations reached
            final_content = "Tool execution reached maximum iterations. Please try again with a simpler request."
            final_record = MessageRecord(role="assistant", content=final_content)
            session_manager.add_record(request.session_id, final_record.model_dump())
            yield _sse_data({'type': 'record', 'record': final_record.model_dump()})
            yield _sse_data({'type': 'done'})

        except Exception as e:
            error_content = f"Error: {e!s}"
            error_record = MessageRecord(role="assistant", content=error_content)
            session_manager.add_record(request.session_id, error_record.model_dump())
            yield _sse_data({'type': 'error', 'content': error_content})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# Health check
@app.get("/api/health")
def health_check():
    """Health check endpoint"""
    return {"status": "ok"}


# Serve frontend static files
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
