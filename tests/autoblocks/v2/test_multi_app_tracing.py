import os
from unittest import mock

from autoblocks._impl.prompts.v2.models import PromptParameter
from autoblocks._impl.prompts.v2.manager import AutoblocksPromptManager
from autoblocks.tracer import AutoblocksTracer


class MockTemplateRenderer:
    """Mock template renderer for testing."""
    
    def render(self, template, params):
        """Mock render method that just returns the template."""
        return f"Rendered template with params: {params}"


class MockPromptExecutionContext:
    """Mock execution context for testing."""
    
    def __init__(self, content="Mock response"):
        self.content = content
    
    def execute(self, prompt, params, **kwargs):
        """Mock execute method that returns a fixed response."""
        return self


class SearchAppManager(AutoblocksPromptManager):
    """Mock prompt manager for search app."""
    
    def __init__(self):
        super().__init__(
            prompt_id="search-prompt",
            app_id="search_app",
            major_version="1",
            minor_version="0",
            template="Search for {{ query }} in {{ source }}",
            parameters=[
                PromptParameter(
                    name="query",
                    type="string",
                    description="The search query",
                    required=True
                ),
                PromptParameter(
                    name="source",
                    type="string", 
                    description="The source to search in",
                    required=True
                )
            ]
        )
        self._template_renderer = MockTemplateRenderer()
        self._execution_context = MockPromptExecutionContext("Search results")


class NlpAppManager(AutoblocksPromptManager):
    """Mock prompt manager for NLP app."""
    
    def __init__(self):
        super().__init__(
            prompt_id="summarize-prompt",
            app_id="nlp_app",
            major_version="2",
            minor_version="1",
            template="Summarize the following text: {{ text }}",
            parameters=[
                PromptParameter(
                    name="text",
                    type="string",
                    description="The text to summarize",
                    required=True
                )
            ]
        )
        self._template_renderer = MockTemplateRenderer()
        self._execution_context = MockPromptExecutionContext("Summary result")


class TestMultiAppTracing:
    """Tests for multi-app prompt tracing with a single tracer."""
    
    def test_trace_single_app_prompt(self):
        """Test tracing a single app's prompt execution."""
        # Setup tracer
        tracer = AutoblocksTracer()
        tracer.track = mock.MagicMock()
        
        # Execute prompt with tracer
        manager = SearchAppManager()
        result = manager.execute(
            query="climate change",
            source="scientific journals",
            tracer=tracer
        )
        
        # Verify response
        assert result.content == "Search results"
        
        # Verify tracer was called correctly
        tracer.track.assert_called_once()
        
        # Check event details
        call_args = tracer.track.call_args[1]
        assert call_args["event_name"] == "prompt_execution"
        assert "properties" in call_args
        
        # Check traced properties
        props = call_args["properties"]
        assert props["promptId"] == "search-prompt"
        assert props["appId"] == "search_app"
        assert props["parameters"]["query"] == "climate change"
        assert props["parameters"]["source"] == "scientific journals"
    
    def test_trace_multiple_app_prompts(self):
        """Test tracing prompts from multiple apps with a single tracer."""
        # Setup tracer
        tracer = AutoblocksTracer()
        tracer.track = mock.MagicMock()
        
        # Execute search app prompt
        search_manager = SearchAppManager()
        search_result = search_manager.execute(
            query="climate change",
            source="scientific journals",
            tracer=tracer
        )
        
        # Execute NLP app prompt
        nlp_manager = NlpAppManager()
        nlp_result = nlp_manager.execute(
            text="This is a long article that needs summarization.",
            tracer=tracer
        )
        
        # Verify responses
        assert search_result.content == "Search results"
        assert nlp_result.content == "Summary result"
        
        # Verify tracer was called twice
        assert tracer.track.call_count == 2
        
        # Get call arguments
        call_args_list = tracer.track.call_args_list
        
        # Check first call (search app)
        search_call = call_args_list[0][1]
        assert search_call["event_name"] == "prompt_execution"
        assert search_call["properties"]["promptId"] == "search-prompt"
        assert search_call["properties"]["appId"] == "search_app"
        assert search_call["properties"]["parameters"]["query"] == "climate change"
        
        # Check second call (NLP app)
        nlp_call = call_args_list[1][1]
        assert nlp_call["event_name"] == "prompt_execution"
        assert nlp_call["properties"]["promptId"] == "summarize-prompt"
        assert nlp_call["properties"]["appId"] == "nlp_app"
        assert nlp_call["properties"]["parameters"]["text"] == "This is a long article that needs summarization."
    
    def test_custom_event_name(self):
        """Test using custom event names for different apps."""
        # Setup tracer
        tracer = AutoblocksTracer()
        tracer.track = mock.MagicMock()
        
        # Execute search app prompt with custom event name
        search_manager = SearchAppManager()
        search_result = search_manager.execute(
            query="climate change",
            source="scientific journals",
            tracer=tracer,
            event_name="search_execution"
        )
        
        # Execute NLP app prompt with custom event name
        nlp_manager = NlpAppManager()
        nlp_result = nlp_manager.execute(
            text="This is a long article that needs summarization.",
            tracer=tracer,
            event_name="summarize_execution"
        )
        
        # Verify tracer was called with custom event names
        assert tracer.track.call_count == 2
        
        # Get call arguments
        call_args_list = tracer.track.call_args_list
        
        # Check event names
        assert call_args_list[0][1]["event_name"] == "search_execution"
        assert call_args_list[1][1]["event_name"] == "summarize_execution"
    
    def test_custom_properties(self):
        """Test adding custom properties to traced events."""
        # Setup tracer
        tracer = AutoblocksTracer()
        tracer.track = mock.MagicMock()
        
        # Execute search app prompt with custom properties
        search_manager = SearchAppManager()
        search_result = search_manager.execute(
            query="climate change",
            source="scientific journals",
            tracer=tracer,
            custom_properties={
                "source_type": "academic",
                "search_intent": "research"
            }
        )
        
        # Execute NLP app prompt with custom properties
        nlp_manager = NlpAppManager()
        nlp_result = nlp_manager.execute(
            text="This is a long article that needs summarization.",
            tracer=tracer,
            custom_properties={
                "text_length": 150,
                "language": "english"
            }
        )
        
        # Verify tracer was called with custom properties
        assert tracer.track.call_count == 2
        
        # Get call arguments
        call_args_list = tracer.track.call_args_list
        
        # Check custom properties were merged
        search_props = call_args_list[0][1]["properties"]
        assert search_props["source_type"] == "academic"
        assert search_props["search_intent"] == "research"
        
        nlp_props = call_args_list[1][1]["properties"]
        assert nlp_props["text_length"] == 150
        assert nlp_props["language"] == "english"
    
    def test_traced_render_template(self):
        """Test tracing template rendering for multiple apps."""
        # Setup tracer
        tracer = AutoblocksTracer()
        tracer.track = mock.MagicMock()
        
        # Render templates with tracer
        search_manager = SearchAppManager()
        search_template = search_manager.render_template(
            query="climate change",
            source="scientific journals",
            tracer=tracer
        )
        
        nlp_manager = NlpAppManager()
        nlp_template = nlp_manager.render_template(
            text="This is a long article that needs summarization.",
            tracer=tracer
        )
        
        # Verify tracer was called twice
        assert tracer.track.call_count == 2
        
        # Get call arguments
        call_args_list = tracer.track.call_args_list
        
        # Check event names and properties
        assert call_args_list[0][1]["event_name"] == "prompt_render"
        assert call_args_list[0][1]["properties"]["promptId"] == "search-prompt"
        assert call_args_list[0][1]["properties"]["appId"] == "search_app"
        
        assert call_args_list[1][1]["event_name"] == "prompt_render"
        assert call_args_list[1][1]["properties"]["promptId"] == "summarize-prompt"
        assert call_args_list[1][1]["properties"]["appId"] == "nlp_app" 