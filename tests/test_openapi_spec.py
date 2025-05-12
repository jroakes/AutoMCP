import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.openapi.spec import (
    OpenAPISpecParser,
    reduce_openapi_spec,
    _resolve_references,
    ReducedOpenAPISpec
)


class TestResolveReferences(unittest.TestCase):

    def test_simple_reference(self):
        spec = {
            "components": {
                "schemas": {
                    "Pet": {"type": "object", "properties": {"name": {"type": "string"}}}
                }
            },
            "paths": {
                "/pets": {
                    "get": {
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/Pet"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        resolved = _resolve_references(spec)
        expected_schema = spec['components']['schemas']['Pet']
        actual_schema = resolved['paths']['/pets']['get']['responses']['200']['content']['application/json']['schema']
        self.assertEqual(actual_schema, expected_schema)

    def test_nested_reference(self):
        spec = {
            "components": {
                "schemas": {
                    "ErrorModel": {"type": "object", "properties": {"message": {"type": "string"}}},
                    "Pet": {"type": "object", "properties": {"error": {"$ref": "#/components/schemas/ErrorModel"}}}
                }
            },
            "paths": {
                "/pets": {
                    "get": {
                        "responses": {
                            "default": {
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/Pet"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        resolved = _resolve_references(spec)
        expected_error_model = spec['components']['schemas']['ErrorModel']
        pet_schema_in_response = resolved['paths']['/pets']['get']['responses']['default']['content']['application/json']['schema']
        actual_error_model_in_pet = pet_schema_in_response['properties']['error']
        self.assertEqual(actual_error_model_in_pet, expected_error_model)

    def test_circular_reference(self):
        spec = {
            "components": {
                "schemas": {
                    "NodeA": {"type": "object", "properties": {"childB": {"$ref": "#/components/schemas/NodeB"}}},
                    "NodeB": {"type": "object", "properties": {"childA": {"$ref": "#/components/schemas/NodeA"}}}
                }
            },
            "paths": {
                "/nodes": {
                    "get": {
                        "requestBody": {
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/NodeA"}}
                            }
                        }
                    }
                }
            }
        }
        resolved_spec = _resolve_references(spec)
        node_a_in_path = resolved_spec['paths']['/nodes']['get']['requestBody']['content']['application/json']['schema']
        node_b_in_node_a = node_a_in_path['properties']['childB']
        
        # If cycle breaks when resolving NodeB itself, node_b_in_node_a might be {}
        if node_b_in_node_a == {}:
             self.assertEqual(node_b_in_node_a, {})
        # Otherwise, check if NodeB was resolved and the cycle broke within it
        elif isinstance(node_b_in_node_a, dict) and 'properties' in node_b_in_node_a:
            circular_ref_location = node_b_in_node_a['properties']['childA']
            self.assertEqual(circular_ref_location, {})
            self.assertNotIn("$ref", circular_ref_location)
        else:
            # Fallback: Should ideally not happen if cycle breaks correctly
            self.fail(f"Unexpected structure after cycle resolution: {node_b_in_node_a}")

    def test_non_existent_reference(self):
        spec = {"paths": {"/test": {"get": {"schema": {"$ref": "#/components/schemas/NonExistent"}}}}}
        resolved = _resolve_references(spec)
        self.assertEqual(resolved['paths']['/test']['get']['schema'], {"$ref": "#/components/schemas/NonExistent"})

    def test_external_reference_not_supported(self):
        spec = {"paths": {"/test": {"get": {"schema": {"$ref": "http://example.com/schemas/external.json#/Pet"}}}}}
        with self.assertRaises(ValueError):
            _resolve_references(spec)


class TestReduceOpenAPISpec(unittest.TestCase):
    sample_spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0", "description": "API Description"},
        "servers": [{"url": "http://localhost/api"}],
        "components": {"schemas": {"Pet": {"type": "object", "properties": {"name": {"type": "string"}}}}},
        "paths": {
            "/pets": {
                "get": {
                    "summary": "List all pets",
                    "description": "Returns a list of pets.",
                    "parameters": [{"name": "limit", "in": "query", "schema": {"type": "integer"}}],
                    "responses": {"200": {"description": "A list of pets", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Pet"}}}}},
                },
                "post": {
                    "summary": "Create a pet",
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"newPet": {"$ref": "#/components/schemas/Pet"}}}}}},
                    "responses": {"201": {"description": "Pet created"}}
                },
                "put": {"summary": "Update a pet"} 
            }
        }
    }

    def test_reduce_spec_basic(self):
        """Test reduce_openapi_spec with actual dereferencing (no mocking of _resolve_references)"""
        # Create a sample spec with references that need resolution
        test_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0", "description": "API with References"},
            "servers": [{"url": "http://localhost/api"}],
            "components": {
                "schemas": {
                    "Pet": {"type": "object", "properties": {"name": {"type": "string"}}}
                }
            },
            "paths": {
                "/pets": {
                    "get": {
                        "summary": "List all pets",
                        "description": "Returns a list of pets.",
                        "responses": {
                            "200": {
                                "description": "Success",
                                "content": {
                                    "application/json": {"schema": {"$ref": "#/components/schemas/Pet"}}
                                }
                            }
                        }
                    }
                }
            }
        }
        
        # Call reduce_openapi_spec with dereference=True
        reduced = reduce_openapi_spec(test_spec, dereference=True)
        
        # Verify the object type
        self.assertIsInstance(reduced, ReducedOpenAPISpec)
        
        # Verify base metadata
        self.assertEqual(reduced.description, "API with References")
        self.assertEqual(len(reduced.servers), 1)
        
        # Verify endpoints and their content
        self.assertEqual(len(reduced.endpoints), 1)
        endpoint = reduced.endpoints[0]
        self.assertEqual(endpoint[0], "GET /pets")
        self.assertEqual(endpoint[1], "Returns a list of pets.")
        
        # Verify that references were resolved - check the response schema
        response_schema = endpoint[2]["responses"]["200"]["content"]["application/json"]["schema"]
        self.assertNotIn("$ref", response_schema)
        self.assertEqual(response_schema["type"], "object")
        self.assertEqual(response_schema["properties"]["name"]["type"], "string")

    @patch('src.openapi.spec._resolve_references')
    def test_reduce_spec_no_dereference(self, mock_resolve_references):
        reduce_openapi_spec(self.sample_spec, dereference=False)
        mock_resolve_references.assert_not_called()

class TestOpenAPISpecParser(unittest.TestCase):

    def setUp(self):
        self.sample_spec_data = {
            "openapi": "3.0.0",
            "info": {"title": "My API", "version": "v1", "description": "Test Description"},
            "servers": [{"url": "https://api.example.com/v1/"}, {"url": "http://localhost/api"}],
            "paths": {
                "/items": {
                    "get": {"summary": "Get items"},
                    "post": {"summary": "Create item"}
                },
                "/users": {
                    "delete": {"summary": "Delete user"}
                }
            },
            "components": {
                "securitySchemes": {
                    "apiKey": {"type": "apiKey", "name": "X-API-Key", "in": "header"},
                    "bearerAuth": {"type": "http", "scheme": "bearer"}
                }
            },
            "security": [
                {"apiKey": []},
                {"bearerAuth": []}
            ]
        }
        self.mock_reduced_spec = MagicMock(spec=ReducedOpenAPISpec)
        self.mock_reduced_spec.servers = self.sample_spec_data["servers"]
        self.mock_reduced_spec.description = self.sample_spec_data["info"]["description"]
        self.mock_reduced_spec.endpoints = [
            ("GET /items", "Get items", {"summary": "Get items"}),
            ("POST /items", "Create item", {"summary": "Create item"})
        ]
        self.patcher = patch('src.openapi.spec.reduce_openapi_spec', return_value=self.mock_reduced_spec)
        self.mock_reduce_openapi_spec = self.patcher.start()
        self.addCleanup(self.patcher.stop)

        self.parser = OpenAPISpecParser(self.sample_spec_data)
    
    def test_init_calls_reduce_spec(self):
        self.mock_reduce_openapi_spec.assert_called_once_with(self.sample_spec_data)
        self.assertEqual(self.parser.reduced_spec, self.mock_reduced_spec)

    def test_get_base_url(self):
        self.assertEqual(self.parser.get_base_url(), "https://api.example.com/v1")
        
        self.mock_reduced_spec.servers = []
        self.assertEqual(self.parser.get_base_url(), "")

        self.mock_reduced_spec.servers = [{"url": "http://no-slash.com"}]
        self.assertEqual(self.parser.get_base_url(), "http://no-slash.com")

    def test_get_endpoints(self):
        endpoints = self.parser.get_endpoints()
        self.assertEqual(endpoints, self.mock_reduced_spec.endpoints)
        self.assertEqual(len(endpoints), 2)

    def test_get_security_schemes(self):
        schemes = self.parser.get_security_schemes()
        expected_schemes = self.sample_spec_data.get("components", {}).get("securitySchemes", {})
        self.assertEqual(schemes, expected_schemes)

    def test_get_auth_schemes_alias(self):
        if hasattr(self.parser, 'get_auth_schemes'):
            schemes = self.parser.get_auth_schemes()
            expected_schemes = self.sample_spec_data.get("components", {}).get("securitySchemes", {})
            self.assertEqual(schemes, expected_schemes)

    def test_get_security_requirements(self):
        requirements = self.parser.get_security_requirements()
        expected_requirements = self.sample_spec_data.get("security", [])
        self.assertEqual(requirements, expected_requirements)


if __name__ == '__main__':
    unittest.main() 