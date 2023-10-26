import traceback
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union
from uuid import UUID

from autoblocks._impl.tracer import AutoblocksTracer
from autoblocks._impl.util import ingestion_key_from_env

try:
    import langchain
    from langchain.callbacks.base import BaseCallbackHandler
    from langchain.schema import AgentAction
    from langchain.schema import AgentFinish
    from langchain.schema import BaseMessage
    from langchain.schema import LLMResult
except ImportError:
    raise ImportError("You must have langchain installed in order to use AutoblocksCallbackHandler.")


class AutoblocksCallbackHandler(BaseCallbackHandler):
    def __init__(self) -> None:
        super().__init__()
        self._trace_id = None
        self._tracer = AutoblocksTracer(
            ingestion_key_from_env(),
            properties={
                "__langchainVersion": langchain.__version__,
                "__langchainLanguage": "python",
            },
        )

    def _send_event(self, message: str, properties: Dict) -> None:
        # Remove None values from properties
        properties = {k: v for k, v in properties.items() if v is not None}
        self.tracer.send_event(
            message,
            trace_id=self._trace_id,
            properties=properties,
        )

    def _on_start(self, run_id: UUID) -> None:
        if self.tracer.trace_id:
            # Trace ID is being managed by the user
            return
        elif self._trace_id:
            # Trace ID has already been set by this handler
            return

        self._trace_id = str(run_id)

    def _on_end(self, run_id: UUID) -> None:
        if self._trace_id == str(run_id):
            self._trace_id = None

    @staticmethod
    def _serialize_error(error: Union[Exception, KeyboardInterrupt]) -> Dict:
        return dict(
            type=type(error).__name__,
            message=str(error),
            traceback=traceback.format_exc(),
        )

    @property
    def tracer(self) -> AutoblocksTracer:
        return self._tracer

    def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[BaseMessage]],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        self._on_start(run_id)

        self._send_event(
            "langchain.chatmodel.start",
            properties=dict(
                run_id=str(run_id),
                parent_run_id=str(parent_run_id) if parent_run_id else None,
                serialized=serialized,
                messages=[[m.to_json() for m in group] for group in messages],
                **kwargs,
            ),
        )

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        self._on_start(run_id)

        self._send_event(
            "langchain.llm.start",
            properties=dict(
                run_id=str(run_id),
                parent_run_id=str(parent_run_id) if parent_run_id else None,
                serialized=serialized,
                prompts=prompts,
                **kwargs,
            ),
        )

    def on_llm_new_token(self, *args, **kwargs) -> None:
        pass

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        response_serialized = dict(
            llm_output=response.llm_output,
            generations=[[g.to_json() for g in group] for group in response.generations],
        )

        self._send_event(
            "langchain.llm.end",
            properties=dict(
                run_id=str(run_id),
                parent_run_id=str(parent_run_id) if parent_run_id else None,
                response=response_serialized,
                **kwargs,
            ),
        )

        self._on_end(run_id)

    def on_llm_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        self._send_event(
            "langchain.llm.error",
            properties=dict(
                run_id=str(run_id),
                parent_run_id=str(parent_run_id) if parent_run_id else None,
                error=self._serialize_error(error),
                **kwargs,
            ),
        )

        self._on_end(run_id)

    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        self._on_start(run_id)

        self._send_event(
            "langchain.chain.start",
            properties=dict(
                run_id=str(run_id),
                parent_run_id=str(parent_run_id) if parent_run_id else None,
                serialized=serialized,
                inputs=inputs,
                **kwargs,
            ),
        )

    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        self._send_event(
            "langchain.chain.end",
            properties=dict(
                run_id=str(run_id),
                parent_run_id=str(parent_run_id) if parent_run_id else None,
                outputs=outputs,
                **kwargs,
            ),
        )

        self._on_end(run_id)

    def on_chain_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        self._send_event(
            "langchain.chain.error",
            properties=dict(
                run_id=str(run_id),
                parent_run_id=str(parent_run_id) if parent_run_id else None,
                error=self._serialize_error(error),
                **kwargs,
            ),
        )

        self._on_end(run_id)

    def on_agent_action(
        self,
        action: AgentAction,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        # Agent callbacks are only called within a chain run so we don't call on_start within this handler
        self._send_event(
            "langchain.agent.action",
            properties=dict(
                run_id=str(run_id),
                parent_run_id=str(parent_run_id) if parent_run_id else None,
                tool=action.tool,
                tool_input=action.tool_input,
                log=action.log,
                **kwargs,
            ),
        )

    def on_agent_finish(
        self,
        finish: AgentFinish,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        self._send_event(
            "langchain.agent.finish",
            properties=dict(
                run_id=str(run_id),
                parent_run_id=str(parent_run_id) if parent_run_id else None,
                return_values=finish.return_values,
                log=finish.log,
                **kwargs,
            ),
        )

        # Agent callbacks are only called within a chain run so we don't call on_end within this handler

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        self._on_start(run_id)

        self._send_event(
            "langchain.tool.start",
            properties=dict(
                run_id=str(run_id),
                parent_run_id=str(parent_run_id) if parent_run_id else None,
                serialized=serialized,
                input_str=input_str,
                **kwargs,
            ),
        )

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        self._send_event(
            "langchain.tool.end",
            properties=dict(
                run_id=str(run_id),
                parent_run_id=str(parent_run_id) if parent_run_id else None,
                output=output,
                **kwargs,
            ),
        )

        self._on_end(run_id)

    def on_tool_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        self._send_event(
            "langchain.tool.error",
            properties=dict(
                run_id=str(run_id),
                parent_run_id=str(parent_run_id) if parent_run_id else None,
                error=self._serialize_error(error),
                **kwargs,
            ),
        )

        self._on_end(run_id)

    def on_text(self, *args, **kwargs) -> None:
        pass
