import traceback
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union
from uuid import UUID

from autoblocks._impl.tracer import AutoblocksTracer

try:
    from langchain.callbacks.base import BaseCallbackHandler
except ImportError:
    raise ImportError("You must have langchain installed in order to use AutoblocksCallbackHandler.")


class AutoblocksCallbackHandler(BaseCallbackHandler):
    def __init__(
        self,
        ingestion_key: str,
        trace_id: Optional[str] = None,
    ) -> None:
        super().__init__()
        self._trace_id = trace_id
        self._run_names: Dict[UUID, str] = {}
        self._ab = AutoblocksTracer(ingestion_key)

    def _send_event(self, message: str, properties: Dict) -> None:
        self._ab.send_event(
            message,
            trace_id=self._trace_id,
            properties=properties,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def _convert_message_to_dict(message: Any) -> Optional[Dict]:  # message=BaseMessage
        if message.type == "human":
            return {"role": "user", "content": message.content}
        elif message.type == "ai":
            return {"role": "assistant", "content": message.content}
        elif message.type == "system":
            return {"role": "system", "content": message.content}
        elif message.type == "function":
            return {"role": "function", "content": message.content, "name": message.name}
        elif message.type == "chat":
            return {"role": message.role, "content": message.content}
        return None

    @staticmethod
    def _make_name_from_parts(parts: List[str]) -> str:
        return ".".join(parts)

    def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[Any]],  # List[List[BaseMessage]]
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        name = self._make_name_from_parts(serialized["id"])

        self._run_names[run_id] = name

        if not self._trace_id:
            self._trace_id = str(run_id)

        message_dicts = []
        for group in messages:
            message_group_dicts = []
            for message in group:
                message_dict = self._convert_message_to_dict(message)
                if message_dict:
                    message_group_dicts.append(message_dict)
            message_dicts.append(message_group_dicts)

        self._send_event(
            f"{name}.start",
            properties=dict(
                run_id=str(run_id),
                parent_run_id=str(parent_run_id) if parent_run_id else None,
                tags=tags,
                messages=message_dicts,
                params=kwargs.get("invocation_params"),
            ),
        )

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        name = self._make_name_from_parts(serialized["id"])

        self._run_names[run_id] = name

        if not self._trace_id:
            self._trace_id = str(run_id)

        self._send_event(
            f"{name}.start",
            properties=dict(
                run_id=str(run_id),
                parent_run_id=str(parent_run_id) if parent_run_id else None,
                tags=tags,
                prompts=prompts,
                params=kwargs.get("invocation_params"),
            ),
        )

    def on_llm_new_token(self, *args, **kwargs) -> None:
        pass

    def on_llm_end(
        self,
        response: Any,  # LLMResult
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        name = self._run_names.pop(run_id, None)
        if not name:
            return

        generations = []
        for llm_result in response.flatten():
            g = llm_result.generations[0][0]
            if not g:
                continue
            generations.append(
                dict(
                    text=g.text,
                    info=g.generation_info,
                )
            )

        self._send_event(
            f"{name}.end",
            properties=dict(
                run_id=str(run_id),
                parent_run_id=str(parent_run_id) if parent_run_id else None,
                tags=tags,
                generations=generations,
            ),
        )

        # Unset the trace id if this trace has ended
        if self._trace_id == str(run_id):
            self._trace_id = None

    def on_llm_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        name = self._run_names.pop(run_id, None)
        if not name:
            return

        self._send_event(
            f"{name}.error",
            properties=dict(
                run_id=str(run_id),
                parent_run_id=str(parent_run_id) if parent_run_id else None,
                tags=tags,
                error=dict(message=str(error), stacktrace=traceback.format_exc()),
            ),
        )

        # Unset the trace id if this trace has ended
        if self._trace_id == str(run_id):
            self._trace_id = None

    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        name = self._make_name_from_parts(serialized["id"])

        self._run_names[run_id] = name

        if not self._trace_id:
            self._trace_id = str(run_id)

        self._send_event(
            f"{name}.start",
            properties=dict(
                run_id=str(run_id),
                parent_run_id=str(parent_run_id) if parent_run_id else None,
                tags=tags,
                inputs=inputs,
            ),
        )

    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        name = self._run_names.pop(run_id, None)
        if not name:
            return

        self._send_event(
            f"{name}.end",
            properties=dict(
                run_id=str(run_id),
                parent_run_id=str(parent_run_id) if parent_run_id else None,
                tags=tags,
                outputs=outputs,
            ),
        )

        # Unset the trace id if this trace has ended
        if self._trace_id == str(run_id):
            self._trace_id = None

    def on_chain_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        name = self._run_names.pop(run_id, None)
        if not name:
            return

        self._send_event(
            f"{name}.error",
            properties=dict(
                run_id=str(run_id),
                parent_run_id=str(parent_run_id) if parent_run_id else None,
                tags=tags,
                error=dict(message=str(error), stacktrace=traceback.format_exc()),
            ),
        )

        # Unset the trace id if this trace has ended
        if self._trace_id == str(run_id):
            self._trace_id = None

    def on_agent_action(
        self,
        action: Any,  # AgentAction
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        self._send_event(
            "langchain.agent.action",
            properties=dict(
                run_id=str(run_id),
                parent_run_id=str(parent_run_id) if parent_run_id else None,
                tags=tags,
                tool=action.tool,
                tool_input=action.tool_input,
                log=action.log,
            ),
        )

    def on_agent_finish(
        self,
        finish: Any,  # AgentFinish
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        self._send_event(
            "langchain.agent.finish",
            properties=dict(
                run_id=str(run_id),
                parent_run_id=str(parent_run_id) if parent_run_id else None,
                tags=tags,
                return_values=finish.return_values,
                log=finish.log,
            ),
        )

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        name = serialized["name"]

        self._run_names[run_id] = name

        if not self._trace_id:
            self._trace_id = str(run_id)

        description = serialized.get("description")

        self._send_event(
            f"langchain.tool.{name}.start",
            properties=dict(
                run_id=str(run_id),
                parent_run_id=str(parent_run_id) if parent_run_id else None,
                tags=tags,
                input=input_str,
                description=description,
            ),
        )

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        name = self._run_names.pop(run_id, None)
        if not name:
            return

        self._send_event(
            f"langchain.tool.{name}.end",
            properties=dict(
                run_id=str(run_id),
                parent_run_id=str(parent_run_id) if parent_run_id else None,
                tags=tags,
                output=output,
            ),
        )

        # Unset the trace id if this trace has ended
        if self._trace_id == str(run_id):
            self._trace_id = None

    def on_tool_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        name = self._run_names.pop(run_id, None)
        if not name:
            return

        self._send_event(
            f"langchain.tool.{name}.error",
            properties=dict(
                run_id=str(run_id),
                parent_run_id=str(parent_run_id) if parent_run_id else None,
                tags=tags,
                error=dict(message=str(error), stacktrace=traceback.format_exc()),
            ),
        )

        # Unset the trace id if this trace has ended
        if self._trace_id == str(run_id):
            self._trace_id = None

    def on_text(self, *args, **kwargs) -> None:
        pass
