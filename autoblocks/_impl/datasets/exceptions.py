"""Custom exceptions for Datasets API."""

import json
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import httpx


class AutoblocksError(Exception):
    """Base class for all Autoblocks exceptions."""

    pass


class ValidationError(AutoblocksError):
    """Raised when a validation error occurs."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.details = details or {}
        super().__init__(message)


class ValidationIssue:
    """Structure representing a validation issue."""

    def __init__(
        self,
        code: str,
        message: str,
        path: Optional[List[str]] = None,
        expected: Optional[str] = None,
        received: Optional[str] = None,
        options: Optional[List[str]] = None,
    ):
        self.code = code
        self.message = message
        self.path = path or []
        self.expected = expected
        self.received = received
        self.options = options

    @property
    def path_str(self) -> str:
        """Get the path as a dot-joined string."""
        return ".".join(self.path) if self.path else "(root)"


class ApiErrorResponse:
    """Structure representing API error response."""

    def __init__(self, success: bool = False, error: Optional[Dict[str, Any]] = None):
        self.success = success
        self.error = error or {}

    @property
    def error_message(self) -> Optional[str]:
        """Get the error message."""
        return self.error.get("message")

    @property
    def error_name(self) -> Optional[str]:
        """Get the error name."""
        return self.error.get("name")

    @property
    def issues(self) -> List[ValidationIssue]:
        """Get validation issues."""
        issues_data = self.error.get("issues", [])
        return [
            ValidationIssue(
                code=issue.get("code", ""),
                message=issue.get("message", ""),
                path=issue.get("path"),
                expected=issue.get("expected"),
                received=issue.get("received"),
                options=issue.get("options"),
            )
            for issue in issues_data
        ]


class APIError(AutoblocksError):
    """
    Raised when an API error occurs.

    Example:
    ```python
    try:
        client.create(dataset_request)
    except APIError as e:
        # Log the detailed error message with formatted validation issues
        print(e)

        # You can also programmatically access validation issues
        if e.validation_issues:
            # Take action based on specific validation errors
            has_schema_issues = any(
                'schema' in issue.path_str for issue in e.validation_issues
            )

            if has_schema_issues:
                # Handle schema-specific validation issues
                pass

        # Access other error details
        print(f"Status: {e.status_code}")
        print(f"URL: {e.url}")
    ```
    """

    def __init__(
        self,
        status_code: int,
        message: str,
        response: Optional[httpx.Response] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.status_code = status_code
        self.response = response
        self.details = details or {}
        self.url = response.url if response else None
        self.method = response.request.method if response else "UNKNOWN"
        self.raw_response = None
        self.validation_issues: List[Dict[str, Any]] = []

        # Parse error response if available
        if response and response.content:
            try:
                self.raw_response = response.json()
                self._parse_validation_issues()
            except Exception:
                pass

        # Build detailed error message
        detailed_message = self._build_detailed_message(message)
        super().__init__(detailed_message)

    def _parse_validation_issues(self) -> None:
        """Parse validation issues from the response."""
        if not self.raw_response:
            return

        error = self.raw_response.get("error", {})
        issues = error.get("issues", [])

        if issues:
            self.validation_issues = [
                {
                    "path": ".".join(issue.get("path", [])) or "(root)",
                    "message": issue.get("message", ""),
                    "code": issue.get("code", ""),
                    "options": issue.get("options", []),
                    "expected": issue.get("expected"),
                    "received": issue.get("received"),
                }
                for issue in issues
            ]

    def _build_detailed_message(self, base_message: str) -> str:
        """Build a detailed error message with validation issues."""
        message = f"HTTP {self.status_code}: {base_message}"

        # Add validation error context if available
        if self.validation_issues:
            issues_by_path: Dict[str, List[Dict[str, Any]]] = {}

            # Group issues by path for better readability
            for issue in self.validation_issues:
                path = issue["path"]
                if path not in issues_by_path:
                    issues_by_path[path] = []
                issues_by_path[path].append(issue)

            message += f"\n\nValidation errors ({len(self.validation_issues)} total):"

            for path, path_issues in issues_by_path.items():
                message += f"\n- Field: {path}"

                for issue in path_issues:
                    message += f"\n  • {issue['message']}"

                    if issue["code"] == "invalid_union_discriminator" and issue.get("options"):
                        message += f"\n    Valid options: {', '.join(issue['options'])}"

                    if issue["code"] == "invalid_type" and issue.get("expected") and issue.get("received"):
                        message += f" (received: {issue['received']}, expected: {issue['expected']})"

        # If we have raw response details but no structured validation issues
        elif self.raw_response and self.raw_response.get("error", {}).get("message"):
            message += f"\nDetails: {self.raw_response['error']['message']}"

        # If we have any other details in the response
        elif self.response and self.response.content:
            content = self.response.text
            if len(content) < 1000:
                try:
                    # Try to format JSON for better readability
                    parsed_json = json.loads(content)
                    message += f"\n\nResponse: {json.dumps(parsed_json, indent=2)}"
                except Exception:  # Use a specific exception type rather than bare except
                    # If it's not valid JSON, just include the raw text
                    message += f"\n\nResponse: {content}"
            else:
                # For very large responses, include a truncated version
                message += f"\n\nResponse: {content[:500]}... (truncated)"

        return message


class ConfigurationError(AutoblocksError):
    """Raised when there is a configuration error."""

    pass


class ResourceNotFoundError(APIError):
    """Raised when a resource is not found."""

    def __init__(self, resource_type: str, resource_id: str, response: Optional[httpx.Response] = None):
        super().__init__(404, f"{resource_type} not found: {resource_id}", response)
        self.resource_type = resource_type
        self.resource_id = resource_id


class AuthenticationError(APIError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed", response: Optional[httpx.Response] = None):
        super().__init__(401, message, response)


class RateLimitError(APIError):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", response: Optional[httpx.Response] = None):
        super().__init__(429, message, response)


def parse_error_response(response: httpx.Response) -> APIError:
    """
    Parse an error response and create a structured APIError.

    Args:
        response: The HTTP response object

    Returns:
        An APIError instance with detailed error information
    """
    status_code = response.status_code

    try:
        error_info = response.json()
    except Exception:
        error_info = {"message": response.text}

    message = error_info.get("message", response.reason_phrase)

    if status_code == 401:
        return AuthenticationError(message, response)
    elif status_code == 404:
        # Try to extract resource info from URL
        url_parts = response.url.path.split("/")
        resource_type = url_parts[-2] if len(url_parts) >= 2 else "Resource"
        resource_id = url_parts[-1] if len(url_parts) >= 1 else "unknown"
        return ResourceNotFoundError(resource_type, resource_id, response)
    elif status_code == 429:
        return RateLimitError(message, response)
    else:
        return APIError(status_code, message, response, error_info)
