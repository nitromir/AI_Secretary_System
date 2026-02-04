"""Chat completions endpoint."""

import asyncio
import logging
import time
import uuid
from typing import Any, AsyncIterator

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from ...config import get_settings
from ...models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    Choice,
    ChoiceMessage,
    Usage,
    create_chunk,
    create_error,
    create_response,
    create_tool_call_chunks,
)
from ...providers import get_provider_for_model
from ...utils import (
    apply_summary_to_messages,
    count_message_tokens,
    count_tokens,
    generate_summary,
    get_cache,
    get_messages_to_summarize,
    get_metrics,
    get_request_queue,
    get_session_manager,
    needs_summarization,
    parse_tool_calls,
    prepare_messages_for_cli,
    retry_async,
)


router = APIRouter()
logger = logging.getLogger(__name__)


def convert_tools_and_choice(
    tools: list | None,
    tool_choice: str | dict | None,
) -> tuple[list[dict] | None, Any]:
    """Convert tool objects to dicts for the tools utility.

    Args:
        tools: List of tool definitions (may be Pydantic models)
        tool_choice: Tool choice setting (may be Pydantic model)

    Returns:
        Tuple of (tools_dicts, tool_choice_dict)
    """
    tools_dicts = None
    if tools:
        tools_dicts = [t.model_dump() if hasattr(t, "model_dump") else t for t in tools]

    tool_choice_dict = None
    if tool_choice:
        if hasattr(tool_choice, "model_dump"):
            tool_choice_dict = tool_choice.model_dump()
        else:
            tool_choice_dict = tool_choice

    return tools_dicts, tool_choice_dict


def extract_tool_names(tools: list | None) -> set[str] | None:
    """Extract valid tool names from tool definitions.

    Args:
        tools: List of tool definitions (Pydantic models or dicts)

    Returns:
        Set of valid tool names, or None if no tools provided
    """
    if not tools:
        return None

    names = set()
    for tool in tools:
        tool_dict = tool.model_dump() if hasattr(tool, "model_dump") else tool
        if tool_dict.get("type") == "function":
            func = tool_dict.get("function", {})
            name = func.get("name")
            if name:
                names.add(name)
    return names if names else None


def get_permission_level(provider_name: str, settings) -> str:
    """Get permission level for a provider."""
    levels = {
        "claude": settings.claude_permission_level,
        "gemini": settings.gemini_permission_level,
        "gpt": settings.gpt_permission_level,
    }
    return levels.get(provider_name, "full").lower()


# Atomic mode instruction for chat mode
ATOMIC_MODE_INSTRUCTION = """
IMPORTANT: Work in ATOMIC MODE - perform only ONE action at a time.
- Make only ONE tool call per response
- Wait for the result before proceeding to the next action
- Never batch multiple tool calls in a single response
- Think step by step, one action at a time
"""


def add_atomic_mode_instruction(messages: list[dict], provider_name: str, settings) -> list[dict]:
    """Add atomic mode instruction when in chat mode.

    In chat mode, we want the AI to work one action at a time for better
    control and reliability with external tool execution.
    """
    if get_permission_level(provider_name, settings) != "chat":
        return messages

    if not messages:
        return [{"role": "system", "content": ATOMIC_MODE_INSTRUCTION.strip()}]

    # Add to existing system message or prepend new one
    messages = messages.copy()
    if messages[0].get("role") == "system":
        messages[0] = {
            **messages[0],
            "content": messages[0].get("content", "") + "\n\n" + ATOMIC_MODE_INSTRUCTION.strip(),
        }
    else:
        messages.insert(0, {"role": "system", "content": ATOMIC_MODE_INSTRUCTION.strip()})

    return messages


async def stream_generator(
    request: ChatCompletionRequest,
    conversation_id: str,
    cli_session_id: str | None = None,
) -> AsyncIterator[str]:
    """Generate SSE stream from provider with queue-based concurrency control."""
    provider = get_provider_for_model(request.model)
    metrics = get_metrics()
    settings = get_settings()
    get_session_manager()  # ensure initialized
    request_queue = get_request_queue()
    start_time = time.time()

    if provider is None:
        error = create_error(
            f"Model '{request.model}' not found",
            error_type="not_found_error",
        )
        yield error.model_dump_json()
        return

    # Count prompt tokens
    messages = [m.model_dump() for m in request.messages]

    # Prepare messages with tools and format tool results
    tools_dicts, tool_choice_dict = convert_tools_and_choice(request.tools, request.tool_choice)
    messages = prepare_messages_for_cli(messages, tools_dicts, tool_choice_dict)

    # Add atomic mode instruction in chat mode (one action at a time)
    messages = add_atomic_mode_instruction(messages, provider.name, settings)

    prompt_tokens = count_message_tokens(messages, request.model)

    # Acquire streaming slot if queue is enabled
    if settings.queue_enabled:
        try:
            async with request_queue.acquire_stream_slot(provider.name):
                async for chunk in _do_stream(
                    provider,
                    messages,
                    request,
                    cli_session_id,
                    metrics,
                    settings,
                    start_time,
                    prompt_tokens,
                ):
                    yield chunk
        except asyncio.QueueFull:
            error = create_error(
                "Server busy, streaming queue full. Please retry later.",
                error_type="rate_limit_error",
            )
            yield error.model_dump_json()
            if settings.metrics_enabled:
                metrics.record_request(
                    provider=provider.name,
                    model=request.model,
                    stream=True,
                    duration=time.time() - start_time,
                    success=False,
                    error="queue_full",
                )
    else:
        # Direct streaming without queue
        async for chunk in _do_stream(
            provider,
            messages,
            request,
            cli_session_id,
            metrics,
            settings,
            start_time,
            prompt_tokens,
        ):
            yield chunk


async def _do_stream(
    provider,
    messages: list,
    request: ChatCompletionRequest,
    cli_session_id: str | None,
    metrics,
    settings,
    start_time: float,
    prompt_tokens: int,
) -> AsyncIterator[str]:
    """Internal streaming implementation."""
    completion_text = ""
    chunk_id = None
    has_tools = bool(request.tools)
    valid_tool_names = extract_tool_names(request.tools)

    try:
        stream_gen = await provider.complete(
            messages=messages,
            model=request.model,
            stream=True,
            thinking=request.thinking.model_dump() if request.thinking else None,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            session_id=cli_session_id,
        )
        async for chunk_data in stream_gen:
            if chunk_id is None:
                chunk_id = f"chatcmpl-{id(request):x}"

            content = chunk_data.get("content")
            if content:
                completion_text += content

            is_done = chunk_data.get("done")

            # When tools are provided, buffer content and emit at end
            # This prevents raw ```tool_call``` blocks from appearing in output
            if has_tools:
                # Don't emit content during streaming - we'll emit cleaned content at end
                pass
            else:
                chunk = create_chunk(
                    content=content,
                    model=request.model,
                    provider=provider.name,
                    thinking=chunk_data.get("thinking"),
                    finish_reason="stop" if is_done else None,
                    chunk_id=chunk_id,
                )
                yield chunk.model_dump_json()

        # Process buffered content when tools were provided
        if has_tools:
            tool_calls = []
            remaining_content = completion_text

            if completion_text:
                tool_calls, remaining_content = parse_tool_calls(completion_text, valid_tool_names)

            # Emit cleaned content (without tool_call blocks)
            if remaining_content:
                chunk = create_chunk(
                    content=remaining_content,
                    model=request.model,
                    provider=provider.name,
                    finish_reason=None,
                    chunk_id=chunk_id,
                )
                yield chunk.model_dump_json()

            if tool_calls:
                logger.debug(f"Streaming: parsed {len(tool_calls)} tool calls")
                # Emit tool call chunks
                tc_chunks = create_tool_call_chunks(
                    tool_calls,
                    model=request.model,
                    provider=provider.name,
                    chunk_id=chunk_id,
                )
                for tc_chunk in tc_chunks:
                    yield tc_chunk.model_dump_json()

                # Emit final chunk with finish_reason
                final_chunk = create_chunk(
                    model=request.model,
                    provider=provider.name,
                    finish_reason="tool_calls",
                    chunk_id=chunk_id,
                )
                yield final_chunk.model_dump_json()
            else:
                # No tool calls found - emit stop finish_reason
                final_chunk = create_chunk(
                    model=request.model,
                    provider=provider.name,
                    finish_reason="stop",
                    chunk_id=chunk_id,
                )
                yield final_chunk.model_dump_json()

        yield "[DONE]"

        completion_tokens = count_tokens(completion_text, request.model)

        if settings.metrics_enabled:
            duration = time.time() - start_time
            metrics.record_request(
                provider=provider.name,
                model=request.model,
                stream=True,
                duration=duration,
                success=True,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )

    except asyncio.TimeoutError:
        error = create_error("Request timed out", error_type="timeout_error")
        yield error.model_dump_json()

        if settings.metrics_enabled:
            metrics.record_request(
                provider=provider.name,
                model=request.model,
                stream=True,
                duration=time.time() - start_time,
                success=False,
                error="timeout",
            )

    except Exception as e:
        error = create_error(str(e), error_type="server_error")
        yield error.model_dump_json()

        if settings.metrics_enabled:
            metrics.record_request(
                provider=provider.name,
                model=request.model,
                stream=True,
                duration=time.time() - start_time,
                success=False,
                error=str(e),
            )


@router.post("/v1/chat/completions", response_model=None)
async def create_chat_completion(
    request: ChatCompletionRequest,
):
    """Create a chat completion."""
    settings = get_settings()
    metrics = get_metrics()
    cache = get_cache()

    if request.stream:
        # Session management for streaming
        session_manager = get_session_manager()
        provider = get_provider_for_model(request.model)

        conversation_id = request.conversation_id
        cli_session_id = None

        if conversation_id:
            session = session_manager.get_session(conversation_id)
            if session:
                cli_session_id = session.cli_session_id
                logger.debug(f"Resuming stream session: {conversation_id} -> CLI {cli_session_id}")
            else:
                conversation_id = f"conv-{uuid.uuid4().hex[:12]}"
                if provider:
                    session_manager.create_session(
                        session_id=conversation_id,
                        provider=provider.name,
                        model=request.model,
                    )
        else:
            conversation_id = f"conv-{uuid.uuid4().hex[:12]}"
            if provider:
                session_manager.create_session(
                    session_id=conversation_id,
                    provider=provider.name,
                    model=request.model,
                )
            logger.debug(f"Created new stream session: {conversation_id}")

        return EventSourceResponse(
            stream_generator(request, conversation_id, cli_session_id),
            media_type="text/event-stream",
        )

    # Non-streaming request
    provider = get_provider_for_model(request.model)
    session_manager = get_session_manager()

    if provider is None:
        raise HTTPException(
            status_code=404,
            detail=create_error(
                f"Model '{request.model}' not found",
                error_type="not_found_error",
            ).model_dump(),
        )

    start_time = time.time()
    messages = [m.model_dump() for m in request.messages]

    # Prepare messages with tools and format tool results
    tools_dicts, tool_choice_dict = convert_tools_and_choice(request.tools, request.tool_choice)
    messages = prepare_messages_for_cli(messages, tools_dicts, tool_choice_dict)

    # Add atomic mode instruction in chat mode (one action at a time)
    messages = add_atomic_mode_instruction(messages, provider.name, settings)

    # Count prompt tokens
    prompt_tokens = count_message_tokens(messages, request.model)

    # Session management: lookup or create conversation
    conversation_id = request.conversation_id
    cli_session_id = None

    session = None
    if conversation_id:
        # Continuing existing conversation
        session = session_manager.get_session(conversation_id)
        if session:
            cli_session_id = session.cli_session_id
            # Note: We don't prepend stored history because OpenAI clients send full
            # conversation in request.messages. For Claude, CLI maintains context via --resume.
            # For Gemini/GPT, client's messages contain the full history already.
            logger.debug(f"Resuming session: {conversation_id} -> CLI {cli_session_id}")
        else:
            # Session expired or not found, start fresh
            logger.debug(f"Session {conversation_id} not found, starting new")
            conversation_id = f"conv-{uuid.uuid4().hex[:12]}"
            session = session_manager.create_session(
                session_id=conversation_id,
                provider=provider.name,
                model=request.model,
            )
    else:
        # New conversation
        conversation_id = f"conv-{uuid.uuid4().hex[:12]}"
        session = session_manager.create_session(
            session_id=conversation_id,
            provider=provider.name,
            model=request.model,
        )
        logger.debug(f"Created new session: {conversation_id}")

    # Apply conversation summarization for providers without native sessions
    # Claude has --resume, so we skip summarization for it
    if (
        settings.summarize_enabled
        and provider.name != "claude"
        and session
        and needs_summarization(
            messages,
            settings.summarize_threshold,
            session.summary_up_to_index,
        )
    ):
        try:
            # Get the provider for summarization ("auto" = same provider as request)
            if settings.summarize_provider == "auto":
                summarize_provider = provider
                summarize_model = request.model
            else:
                summarize_provider = get_provider_for_model(settings.summarize_provider)
                summarize_model = settings.summarize_provider

            if summarize_provider:
                # Get messages to summarize (excluding system and recent)
                to_summarize = get_messages_to_summarize(
                    messages,
                    settings.summarize_keep_recent,
                    session.summary_up_to_index,
                )

                if to_summarize:
                    # Combine existing summary with new messages to summarize
                    if session.summary:
                        to_summarize = [
                            {"role": "system", "content": f"[Previous summary]: {session.summary}"}
                        ] + to_summarize

                    # Generate summary
                    new_summary = await generate_summary(
                        to_summarize,
                        summarize_provider,
                        model=summarize_model,
                    )

                    # Store summary in session
                    new_index = len(messages) - settings.summarize_keep_recent
                    session.set_summary(new_summary, new_index)
                    logger.info(
                        f"Summarized conversation: {len(messages)} messages -> "
                        f"summary + {settings.summarize_keep_recent} recent"
                    )

            # Apply summary to messages
            if session.summary:
                messages = apply_summary_to_messages(
                    messages,
                    session.summary,
                    settings.summarize_keep_recent,
                )
        except Exception as e:
            logger.error(f"Summarization failed, using full messages: {e}")
            # Continue with original messages if summarization fails

    # Check cache first
    if settings.cache_enabled:
        cached = cache.get(
            messages=messages,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        if cached:
            logger.debug(f"Cache hit for model {request.model}")
            return ChatCompletionResponse(**cached)

    try:
        # Execute with retry logic through request queue
        async def do_complete():
            return await provider.complete(
                messages=messages,
                model=request.model,
                stream=False,
                thinking=request.thinking.model_dump() if request.thinking else None,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                session_id=cli_session_id,  # Pass CLI session ID for multi-turn
            )

        # Queue the request to manage concurrency per provider (if enabled)
        if settings.queue_enabled:
            request_queue = get_request_queue()
            result = await request_queue.execute(
                provider.name,
                retry_async,
                do_complete,
            )
        else:
            # Direct execution without queue
            result = await retry_async(do_complete)

        # Update session with CLI session ID from response
        new_cli_session_id = result.get("session_id")
        if new_cli_session_id and conversation_id:
            session_manager.update_cli_session_id(conversation_id, new_cli_session_id)

        # Note: We don't store messages in session because OpenAI clients send full
        # conversation history in each request. Storing would cause duplication.

        # Count completion tokens
        content = result.get("content", "")
        completion_tokens = count_tokens(content, request.model)

        # Get cost info if available
        estimated_cost_usd = result.get("cost_usd")

        # Parse tool calls from response if tools were provided
        tool_calls = None
        finish_reason = "stop"
        if request.tools:
            valid_tool_names = extract_tool_names(request.tools)
            parsed_calls, remaining_content = parse_tool_calls(content, valid_tool_names)
            if parsed_calls:
                tool_calls = parsed_calls
                content = remaining_content if remaining_content else None
                finish_reason = "tool_calls"
                logger.debug(f"Parsed {len(tool_calls)} tool calls from response")

        # Create response with tool calls if present
        if tool_calls:
            response = ChatCompletionResponse(
                model=request.model,
                provider=provider.name,
                conversation_id=conversation_id,
                estimated_cost_usd=estimated_cost_usd,
                choices=[
                    Choice(
                        message=ChoiceMessage(
                            content=content,
                            tool_calls=tool_calls,
                            thinking=result.get("thinking"),
                        ),
                        finish_reason=finish_reason,
                    )
                ],
                usage=Usage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                ),
            )
        else:
            response = create_response(
                content=content,
                model=request.model,
                provider=provider.name,
                thinking=result.get("thinking"),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                conversation_id=conversation_id,
                estimated_cost_usd=estimated_cost_usd,
            )

        duration = time.time() - start_time

        # Cache the response
        if settings.cache_enabled:
            cache.set(
                messages=messages,
                model=request.model,
                response=response.model_dump(),
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )

        # Record metrics
        if settings.metrics_enabled:
            metrics.record_request(
                provider=provider.name,
                model=request.model,
                stream=False,
                duration=duration,
                success=True,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost_usd=estimated_cost_usd or 0.0,
            )

        return response

    except asyncio.QueueFull:
        if settings.metrics_enabled:
            metrics.record_request(
                provider=provider.name,
                model=request.model,
                stream=False,
                duration=time.time() - start_time,
                success=False,
                error="queue_full",
            )
        raise HTTPException(
            status_code=503,
            detail=create_error(
                "Server busy, request queue full. Please retry later.",
                error_type="rate_limit_error",
            ).model_dump(),
        )

    except asyncio.TimeoutError:
        if settings.metrics_enabled:
            metrics.record_request(
                provider=provider.name,
                model=request.model,
                stream=False,
                duration=time.time() - start_time,
                success=False,
                error="timeout",
            )
        raise HTTPException(
            status_code=504,
            detail=create_error("Request timed out", error_type="timeout_error").model_dump(),
        )

    except Exception as e:
        if settings.metrics_enabled:
            metrics.record_request(
                provider=provider.name,
                model=request.model,
                stream=False,
                duration=time.time() - start_time,
                success=False,
                error=str(e),
            )
        raise HTTPException(
            status_code=500,
            detail=create_error(str(e), error_type="server_error").model_dump(),
        )
