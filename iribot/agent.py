"""Core Agent logic for handling LLM interactions"""

import json
import logging
import time
from collections.abc import Generator
from typing import Any

import requests
from openai import OpenAI

from .config import settings, update_settings
from .executor import tool_executor
from .openai_codex_auth import refresh_openai_codex_token

logger = logging.getLogger(__name__)
DEFAULT_CODEX_BASE_URL = "https://chatgpt.com/backend-api"


class Agent:
    """Agent for handling LLM interactions"""

    def __init__(self):
        self._rebuild_client()

    def _rebuild_client(self) -> None:
        client_params: dict[str, Any] = {}
        if settings.openai_auth_mode == "codex":
            access_token = self._ensure_codex_access_token()
            if not access_token:
                raise RuntimeError(
                    "Codex auth mode is enabled but no valid Codex token is available. "
                    "Please login from Config dialog."
                )
            client_params["api_key"] = access_token
            if settings.codex_account_id:
                client_params["default_headers"] = {
                    "chatgpt-account-id": settings.codex_account_id
                }
        else:
            client_params["api_key"] = settings.openai_api_key

        if settings.openai_base_url:
            client_params["base_url"] = settings.openai_base_url
        self.client = OpenAI(**client_params)
        self.model = settings.openai_model

    def _ensure_codex_access_token(self) -> str:
        now_ms = int(time.time() * 1000)
        if settings.codex_access_token and settings.codex_expires_at > now_ms + 60_000:
            return settings.codex_access_token

        if not settings.codex_refresh_token:
            return settings.codex_access_token

        refreshed = refresh_openai_codex_token(settings.codex_refresh_token)
        expires_at = now_ms + int(refreshed["expires_in"]) * 1000
        update_settings(
            {
                "codex_access_token": refreshed["access"],
                "codex_refresh_token": refreshed["refresh"],
                "codex_account_id": refreshed["account_id"],
                "codex_expires_at": expires_at,
            }
        )
        return refreshed["access"]

    def reload_config(self) -> None:
        """Reload client/model from the latest settings."""
        self._rebuild_client()

    def chat_stream(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str,
        images: list[str] | None = None,
        extra_body: dict[str, Any] | None = None,
    ) -> Generator[dict[str, Any]]:
        """
        Send a message to the LLM and stream the response

        Yields:
            Chunks of response data
        """
        use_codex_auth = settings.openai_auth_mode == "codex"
        if use_codex_auth:
            yield from self._stream_codex_responses(
                messages=messages,
                system_prompt=system_prompt,
                images=images,
                extra_body=extra_body,
            )
            return

        formatted_messages = [{"role": "system", "content": system_prompt}]

        # Add image to the last user message if provided
        if images and messages and messages[-1]["role"] == "user":
            last_msg = messages[-1].copy()
            content = [{"type": "text", "text": last_msg.get("content", "")}]

            for image_base64 in images:
                content.extend([
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        },
                    }
                ])

            last_msg["content"] = content
            formatted_messages.extend(messages[:-1])
            formatted_messages.append(last_msg)
        else:
            formatted_messages.extend(messages)

        # Get available tools
        tools = tool_executor.get_all_tools()

        log_messages = []
        for message in formatted_messages:
            if message.get("role") == "system":
                log_messages.append({
                    **message,
                    "content": "__system_prompt__",
                })
            else:
                log_messages.append(message)

        # Build API call parameters
        api_params: dict[str, Any] = {
            "model": self.model,
            "messages": formatted_messages,
            "tools": tools,
            "stream": True,
        }

        merged_extra_body: dict[str, Any] = {}
        if settings.enable_thinking:
            merged_extra_body["enable_thinking"] = True
        if extra_body:
            merged_extra_body.update(extra_body)
        if merged_extra_body:
            api_params["extra_body"] = merged_extra_body

        log_payload = {
            "model": self.model,
            "messages": log_messages,
            "tools": tools,
            "stream": True,
        }
        logger.info(
            "OpenAI request: %s",
            json.dumps(log_payload, ensure_ascii=False, default=str),
        )

        # Call OpenAI API with streaming
        response = self.client.chat.completions.create(**api_params)

        content = ""
        reasoning_content = ""
        tool_calls_data = {}
        finish_reason = None

        content_started = False  # Whether content field has started streaming
        reasoning_started = False
        reasoning_ended = True

        for chunk in response:
            delta = chunk.choices[0].delta if chunk.choices else None

            if delta:
                # For moonshot: stream reasoning_content before content
                if hasattr(delta, "reasoning_content"):
                    rc = delta.reasoning_content
                    if rc:
                        reasoning_content += rc
                        if not reasoning_started:
                            # First reasoning content, send start
                            yield {"type": "reasoning_start"}
                            reasoning_ended = False
                            reasoning_started = True
                        # Stream reasoning_content as it appears
                        yield {"type": "reasoning", "content": rc}

                # Stream content as normal
                if delta.content:
                    if not content_started:
                        # When content starts, reasoning_content is finished; insert a separator
                        if reasoning_started:
                            yield {"type": "reasoning_end"}
                            reasoning_ended = True
                        content_started = True
                    content += delta.content
                    yield {"type": "content", "content": delta.content}

                # Handle tool calls as usual
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_data:
                            tool_calls_data[idx] = {
                                "id": tc.id or "",
                                "type": "function",
                                "function": {"name": "", "arguments": ""},
                            }
                        if tc.id:
                            tool_calls_data[idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                tool_calls_data[idx]["function"]["name"] = tc.function.name
                            if tc.function.arguments:
                                tool_calls_data[idx]["function"]["arguments"] += tc.function.arguments

            if chunk.choices and chunk.choices[0].finish_reason:
                finish_reason = chunk.choices[0].finish_reason

        if not reasoning_ended:
            yield {"type": "reasoning_end"}

        # Collect tool calls for the final result
        tool_calls = (
            [tool_calls_data[i] for i in sorted(tool_calls_data.keys())]
            if tool_calls_data else []
        )

        # Final result
        result = {
            "type": "done",
            "content": content.strip(),
            "tool_calls": tool_calls,
            "reasoning_content": reasoning_content.strip() if reasoning_content else "",
            "finish_reason": finish_reason,
        }

        logger.info(
            "OpenAI response: %s",
            json.dumps(result, ensure_ascii=False, default=str),
        )

        yield result

    def _resolve_codex_url(self) -> str:
        raw = DEFAULT_CODEX_BASE_URL
        if settings.openai_base_url and "chatgpt.com/backend-api" in settings.openai_base_url:
            raw = settings.openai_base_url
        normalized = raw.rstrip("/")
        if normalized.endswith("/codex/responses"):
            return normalized
        if normalized.endswith("/codex"):
            return f"{normalized}/responses"
        return f"{normalized}/codex/responses"

    @staticmethod
    def _convert_tools_for_codex(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        converted = []
        for tool in tools:
            if tool.get("type") != "function":
                continue
            function = tool.get("function", {})
            name = function.get("name")
            if not name:
                continue
            converted.append(
                {
                    "type": "function",
                    "name": name,
                    "description": function.get("description", ""),
                    "parameters": function.get("parameters", {"type": "object", "properties": {}}),
                }
            )
        return converted

    @staticmethod
    def _convert_messages_for_codex(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        converted: list[dict[str, Any]] = []
        for msg in messages:
            role = msg.get("role")
            if role == "system":
                continue
            if role == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    converted.append(
                        {
                            "role": "user",
                            "content": [{"type": "input_text", "text": content}],
                        }
                    )
                elif isinstance(content, list):
                    parts = []
                    for item in content:
                        if item.get("type") == "text":
                            parts.append({"type": "input_text", "text": item.get("text", "")})
                        elif item.get("type") == "image_url":
                            image_url = item.get("image_url", {})
                            parts.append(
                                {
                                    "type": "input_image",
                                    "detail": "auto",
                                    "image_url": image_url.get("url", ""),
                                }
                            )
                    if parts:
                        converted.append({"role": "user", "content": parts})
            elif role == "assistant":
                tool_calls = msg.get("tool_calls") or []
                for tool_call in tool_calls:
                    function = tool_call.get("function", {})
                    converted.append(
                        {
                            "type": "function_call",
                            "call_id": tool_call.get("id", ""),
                            "name": function.get("name", ""),
                            "arguments": function.get("arguments", "{}"),
                        }
                    )

                content = msg.get("content", "")
                if isinstance(content, str) and content.strip():
                    converted.append(
                        {
                            "type": "message",
                            "role": "assistant",
                            "content": [{"type": "output_text", "text": content}],
                            "status": "completed",
                        }
                    )
            elif role == "tool":
                converted.append(
                    {
                        "type": "function_call_output",
                        "call_id": msg.get("tool_call_id", ""),
                        "output": str(msg.get("content", "")),
                    }
                )
        return converted

    def _stream_codex_responses(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str,
        images: list[str] | None = None,
        extra_body: dict[str, Any] | None = None,
    ) -> Generator[dict[str, Any]]:
        tools = tool_executor.get_all_tools()
        formatted_messages = list(messages)

        if images and messages and messages[-1]["role"] == "user":
            last_msg = messages[-1].copy()
            content = [{"type": "text", "text": last_msg.get("content", "")}]
            for image_base64 in images:
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
                    }
                )
            last_msg["content"] = content
            formatted_messages = messages[:-1] + [last_msg]

        body: dict[str, Any] = {
            "model": self.model,
            "store": False,
            "stream": True,
            "instructions": system_prompt,
            "input": self._convert_messages_for_codex(formatted_messages),
            "text": {"verbosity": "medium"},
            "include": ["reasoning.encrypted_content"],
            "tool_choice": "auto",
            "parallel_tool_calls": True,
        }

        codex_tools = self._convert_tools_for_codex(tools)
        if codex_tools:
            body["tools"] = codex_tools
        if extra_body:
            body.update(extra_body)

        headers = {
            "Authorization": f"Bearer {self._ensure_codex_access_token()}",
            "OpenAI-Beta": "responses=experimental",
            "originator": "pi",
            "accept": "text/event-stream",
            "content-type": "application/json",
        }
        if settings.codex_account_id:
            headers["chatgpt-account-id"] = settings.codex_account_id

        safe_log = {
            "model": body["model"],
            "instructions": "__system_prompt__",
            "input_count": len(body.get("input", [])),
            "tools_count": len(codex_tools),
            "url": self._resolve_codex_url(),
        }
        logger.info("Codex request: %s", json.dumps(safe_log, ensure_ascii=False))

        response = requests.post(
            self._resolve_codex_url(),
            headers=headers,
            json=body,
            stream=True,
            timeout=300,
        )
        response.raise_for_status()

        content = ""
        reasoning_content = ""
        finish_reason = "stop"
        tool_calls_data: dict[str, dict[str, Any]] = {}

        event_lines: list[str] = []
        for raw_line in response.iter_lines(decode_unicode=True):
            if raw_line is None:
                continue
            if isinstance(raw_line, bytes):
                line = raw_line.decode("utf-8", errors="replace").strip()
            else:
                line = raw_line.strip()
            if not line:
                if event_lines:
                    data = "\n".join(event_lines).strip()
                    event_lines = []
                    if data and data != "[DONE]":
                        event = json.loads(data)
                        event_type = event.get("type")

                        if event_type == "response.output_text.delta":
                            delta = event.get("delta", "")
                            if delta:
                                content += delta
                                yield {"type": "content", "content": delta}
                        elif event_type == "response.reasoning_summary_text.delta":
                            delta = event.get("delta", "")
                            if delta:
                                if not reasoning_content:
                                    yield {"type": "reasoning_start"}
                                reasoning_content += delta
                                yield {"type": "reasoning", "content": delta}
                        elif event_type == "response.output_item.added":
                            item = event.get("item", {})
                            if item.get("type") == "function_call":
                                call_id = item.get("call_id", "")
                                tool_calls_data[call_id] = {
                                    "id": call_id,
                                    "item_id": item.get("id", ""),
                                    "type": "function",
                                    "function": {
                                        "name": item.get("name", ""),
                                        "arguments": item.get("arguments", "") or "",
                                    },
                                }
                        elif event_type == "response.function_call_arguments.delta":
                            item_id = event.get("item_id")
                            for call in tool_calls_data.values():
                                if call.get("item_id") == item_id or call["id"] == event.get("call_id"):
                                    call["function"]["arguments"] += event.get("delta", "")
                                    break
                        elif event_type == "response.function_call_arguments.done":
                            item_id = event.get("item_id")
                            for call in tool_calls_data.values():
                                if call.get("item_id") == item_id or call["id"] == event.get("call_id"):
                                    call["function"]["arguments"] = event.get("arguments", call["function"]["arguments"])
                                    break
                        elif event_type in {"response.done", "response.completed"}:
                            status = ((event.get("response") or {}).get("status") or "").lower()
                            if status in {"failed", "cancelled"}:
                                finish_reason = "error"
                            elif status == "incomplete":
                                finish_reason = "length"
                            else:
                                finish_reason = "stop"
                        elif event_type in {"error", "response.failed"}:
                            error_message = event.get("message") or json.dumps(event, ensure_ascii=False)
                            raise RuntimeError(error_message)
            elif line.startswith("data:"):
                event_lines.append(line[5:].strip())

        if reasoning_content:
            yield {"type": "reasoning_end"}

        tool_calls = []
        for call in tool_calls_data.values():
            tool_calls.append(
                {
                    "id": call["id"],
                    "type": call["type"],
                    "function": call["function"],
                }
            )
        if tool_calls and finish_reason == "stop":
            finish_reason = "tool_calls"

        result = {
            "type": "done",
            "content": content.strip(),
            "tool_calls": tool_calls,
            "reasoning_content": reasoning_content.strip(),
            "finish_reason": finish_reason,
        }
        logger.info("Codex response: %s", json.dumps(result, ensure_ascii=False, default=str))
        yield result

    def process_tool_call(
        self,
        tool_name: str,
        arguments: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Process a tool call from the LLM

        Args:
            tool_name: Name of the tool to call
            arguments: JSON string of tool arguments

        Returns:
            Result of tool execution
        """
        try:
            args = json.loads(arguments) if arguments else {}
            if tool_name.startswith("shell_") and context and "session_id" not in args and context.get("session_id"):
                args["session_id"] = context["session_id"]
            result = tool_executor.execute_tool(tool_name, **args)
            return {"success": True, "result": result}
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": f"Invalid JSON arguments: {arguments}",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# Global agent instance
agent = Agent()
