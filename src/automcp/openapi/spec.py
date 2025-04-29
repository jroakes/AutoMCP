"""
Name: OpenAPI specification parser.
Description: Provides the OpenAPISpecParser class for extracting endpoints, parameters, and schemas from OpenAPI specifications. Also includes utilities for reducing specifications to essential components and reconstructing OpenAPI specs from tool schemas.
"""

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
    # Make a copy of the spec to avoid modifying the original
    spec = spec.copy()

    # Dereference the spec if requested
    if dereference:
        spec = _resolve_references(spec)

    # Extract only GET and POST endpoints as per requirements
    endpoints = [
        (f"{operation_name.upper()} {route}", docs.get("description", ""), docs)
        for route, operation in spec["paths"].items()
        for operation_name, docs in operation.items()
        if operation_name in ["get", "post"]
    ]

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


def _resolve_references(openapi_spec: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively resolves all $ref references in an OpenAPI specification.

    Handles circular references correctly.

    Args:
        openapi_spec: A dictionary representing the OpenAPI specification.

    Returns:
        A dictionary representing the OpenAPI specification with all references
        resolved.
    """
    import copy

    openapi_spec = copy.deepcopy(openapi_spec)  # Work on a copy
    resolved_cache = {}  # Cache resolved references

    def resolve_ref(ref_string, current_doc):
        """Resolves a single $ref string."""
        parts = ref_string.split("/")
        if parts[0] != "#":
            raise ValueError(f"External references not supported: {ref_string}")

        current = current_doc
        for part in parts[1:]:
            if part in current:
                current = current[part]
            else:
                return None  # Reference not found
        return current

    def recursive_resolve(obj, current_doc, seen_refs=None):
        """Recursively resolves references, handling circularity.

        Args:
            obj: The object to traverse.
            current_doc:  Document to search for refs.
            seen_refs: A set to track already-visited references (for circularity
              detection).

        Returns:
            The resolved object.
        """
        if seen_refs is None:
            seen_refs = set()  # Initialize the set if it's the first call

        if isinstance(obj, dict):
            if "$ref" in obj and isinstance(obj["$ref"], str):
                ref_string = obj["$ref"]

                # Check for circularity
                if ref_string in seen_refs and ref_string not in resolved_cache:
                    # Circular reference detected! Return a *copy* of the object,
                    # but *without* the $ref. This breaks the cycle while
                    # still maintaining the overall structure.
                    return {k: v for k, v in obj.items() if k != "$ref"}

                seen_refs.add(ref_string)  # Add the reference to the set

                # Check if we have a cached resolved value
                if ref_string in resolved_cache:
                    return copy.deepcopy(resolved_cache[ref_string])

                resolved_value = resolve_ref(ref_string, current_doc)
                if resolved_value is not None:
                    # Recursively resolve the *resolved* value,
                    # passing along the 'seen_refs' set
                    resolved_value = recursive_resolve(
                        resolved_value, current_doc, seen_refs
                    )
                    resolved_cache[ref_string] = resolved_value
                    return copy.deepcopy(resolved_value)  # return the cached result
                else:
                    return obj  # return original if no resolved value.

            else:
                new_dict = {}
                for key, value in obj.items():
                    new_dict[key] = recursive_resolve(value, current_doc, seen_refs)
                return new_dict

        elif isinstance(obj, list):
            return [recursive_resolve(item, current_doc, seen_refs) for item in obj]
        else:
            return obj

    return recursive_resolve(openapi_spec, openapi_spec)


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

    def get_security_schemes(self) -> Dict[str, Any]:
        """Extract security schemes defined in the specification.

        Returns:
            Dictionary of security schemes keyed by name
        """
        return self.spec.get("components", {}).get("securitySchemes", {})

    def get_security_requirements(self) -> List[Dict[str, List[str]]]:
        """Extract global security requirements defined in the specification.

        Returns:
            List of security requirement objects
        """
        return self.spec.get("security", [])


def extract_openapi_spec_from_tool(tools):
    """Extract OpenAPI spec from tool schemas.

    This function reconstructs an approximation of the original OpenAPI spec
    from the tool schemas that were generated from it.

    Args:
        tools: List of tool schemas

    Returns:
        OpenAPI spec as a dictionary
    """
    if not tools:
        return None

    # Create a basic OpenAPI spec
    openapi_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "Reconstructed API",
            "version": "1.0.0",
            "description": "API spec reconstructed from tool schemas",
        },
        "paths": {},
        "components": {
            "schemas": {},
            "securitySchemes": {},
        },
    }

    # Add paths from tool schemas
    for tool in tools:
        # Generate a path from the tool name
        tool_name = tool.get("name", "")
        path = f"/{tool_name.replace('_', '/')}"
        method = "get"  # Default to GET

        # Try to determine the HTTP method from the name
        if tool_name.startswith("post_"):
            method = "post"
            path = path.replace("/post/", "/", 1)
        elif tool_name.startswith("get_"):
            method = "get"
            path = path.replace("/get/", "/", 1)

        # Create path item
        path_item = {
            "operationId": tool_name,
            "summary": tool.get("description", ""),
            "parameters": [],
        }

        # Add parameters
        parameters = tool.get("parameters", {}).get("properties", {})
        required_params = tool.get("parameters", {}).get("required", [])

        for param_name, param_schema in parameters.items():
            parameter = {
                "name": param_name,
                "in": "query",  # Default to query
                "description": param_schema.get("description", ""),
                "required": param_name in required_params,
                "schema": {
                    "type": param_schema.get("type", "string"),
                },
            }

            # Add enum if available
            if "enum" in param_schema:
                parameter["schema"]["enum"] = param_schema["enum"]

            path_item["parameters"].append(parameter)

        # Add path to spec
        if path not in openapi_spec["paths"]:
            openapi_spec["paths"][path] = {}

        openapi_spec["paths"][path][method] = path_item

    return openapi_spec
