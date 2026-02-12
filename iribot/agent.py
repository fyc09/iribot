"""Core Agent logic for handling LLM interactions"""

import json
import logging
from collections.abc import Generator
from typing import Any

from openai import OpenAI

from .config import settings
from .executor import tool_executor

logger = logging.getLogger(__name__)


class Agent:
    """Agent for handling LLM interactions"""

    def __init__(self):
        self._rebuild_client()

    def _rebuild_client(self) -> None:
        client_params = {"api_key": settings.openai_api_key}
        if settings.openai_base_url:
            client_params["base_url"] = settings.openai_base_url
        self.client = OpenAI(**client_params)
        self.model = settings.openai_model

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
        # Build messages with system prompt
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

        logger.info(
            "OpenAI request: %s",
            json.dumps(
                {
                    "model": self.model,
                    "messages": log_messages,
                    "tools": tools,
                    "stream": True,
                },
                ensure_ascii=False,
                default=str,
            ),
        )

        # Build API call parameters
        api_params = {
            "model": self.model,
            "messages": formatted_messages,
            "tools": tools,
            "stream": True,
        }
        if extra_body:
            api_params["extra_body"] = extra_body
        elif settings.enable_thinking:
            api_params["extra_body"] = {"enable_thinking": True}

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
