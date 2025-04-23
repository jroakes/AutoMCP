"""OpenAPI specification parser."""

from typing import Any, Dict, List, Tuple

from pydantic import BaseModel


class ReducedOpenAPISpec(BaseModel):
    """A reduced OpenAPI spec for efficient processing.

    This is a simplified representation of OpenAPI specs that focuses
    on the most important parts for tool creation.
    """

    servers: List[Dict[str, Any]]
    description: str
    endpoints: List[Tuple[str, str, Dict[str, Any]]]


def reduce_openapi_spec(
    spec: Dict[str, Any], dereference: bool = True
) -> ReducedOpenAPISpec:
    """Simplify an OpenAPI spec to focus on essential components.

    Args:
        spec: The OpenAPI spec as a dictionary
        dereference: Whether to dereference the spec

    Returns:
        A reduced OpenAPI spec
    """
    # Extract only GET and POST endpoints as per requirements
    endpoints = [
        (f"{operation_name.upper()} {route}", docs.get("description", ""), docs)
        for route, operation in spec["paths"].items()
        for operation_name, docs in operation.items()
        if operation_name in ["get", "post"]
    ]

    # Replace refs if needed (this would require a dereferencing function)
    # For now, we're assuming the spec is already dereferenced

    # Strip docs down to required request args + happy path response
    def reduce_endpoint_docs(docs: Dict[str, Any]) -> Dict[str, Any]:
        out = {}
        if docs.get("description"):
            out["description"] = docs.get("description")
        if docs.get("summary"):
            out["summary"] = docs.get("summary")
        if docs.get("parameters"):
            out["parameters"] = [parameter for parameter in docs.get("parameters", [])]
        if docs.get("responses") and "200" in docs["responses"]:
            out["responses"] = {"200": docs["responses"]["200"]}
        if docs.get("requestBody"):
            out["requestBody"] = docs.get("requestBody")
        return out

    endpoints = [
        (name, description, reduce_endpoint_docs(docs))
        for name, description, docs in endpoints
    ]

    return ReducedOpenAPISpec(
        servers=spec.get("servers", []),
        description=spec.get("info", {}).get("description", ""),
        endpoints=endpoints,
    )


class OpenAPISpecParser:
    """Parser for OpenAPI specifications."""

    def __init__(self, spec: Dict[str, Any]):
        """Initialize the parser with an OpenAPI spec.

        Args:
            spec: The OpenAPI spec as a dictionary
        """
        self.spec = spec
        self.reduced_spec = reduce_openapi_spec(spec)

    def get_base_url(self) -> str:
        """Get the base URL from the OpenAPI spec.

        Returns:
            The base URL for API requests
        """
        if not self.reduced_spec.servers:
            return ""

        # Use the first server URL
        server = self.reduced_spec.servers[0]
        url = server.get("url", "")

        # Remove trailing slash if present
        if url.endswith("/"):
            url = url[:-1]

        return url

    def get_endpoints(self) -> List[Tuple[str, str, Dict[str, Any]]]:
        """Get all endpoints from the OpenAPI spec.

        Returns:
            A list of endpoints with their descriptions
        """
        return self.reduced_spec.endpoints

    def get_auth_schemes(self) -> Dict[str, Any]:
        """Get authentication schemes from the OpenAPI spec.

        Returns:
            A dictionary of authentication schemes
        """
        components = self.spec.get("components", {})
        security_schemes = components.get("securitySchemes", {})
        return security_schemes
