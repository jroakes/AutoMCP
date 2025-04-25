"""Unit tests for the OpenAPI spec parser."""

import unittest


from src.openapi.spec import OpenAPISpecParser, reduce_openapi_spec


class TestOpenAPISpecParser(unittest.TestCase):
    """Tests for the OpenAPISpecParser class."""

    def setUp(self):
        """Set up the test fixture with a sample OpenAPI spec."""
        self.sample_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "Sample API",
                "version": "1.0.0",
                "description": "A sample API for testing",
            },
            "servers": [
                {
                    "url": "https://api.example.com/v1",
                    "description": "Production server",
                },
                {
                    "url": "https://staging-api.example.com/v1",
                    "description": "Staging server",
                },
            ],
            "paths": {
                "/users": {
                    "get": {
                        "summary": "List all users",
                        "description": "Returns a list of users",
                        "parameters": [
                            {
                                "name": "limit",
                                "in": "query",
                                "schema": {"type": "integer"},
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "A list of users",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "array",
                                            "items": {
                                                "$ref": "#/components/schemas/User"
                                            },
                                        }
                                    }
                                },
                            }
                        },
                    },
                    "post": {
                        "summary": "Create a user",
                        "description": "Creates a new user",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/User"}
                                }
                            },
                        },
                        "responses": {
                            "201": {
                                "description": "Created",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/User"}
                                    }
                                },
                            }
                        },
                    },
                },
                "/users/{userId}": {
                    "get": {
                        "summary": "Get a user by ID",
                        "description": "Returns a single user",
                        "parameters": [
                            {
                                "name": "userId",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string"},
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "A user",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/User"}
                                    }
                                },
                            },
                            "404": {"description": "User not found"},
                        },
                    }
                },
            },
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "name": {"type": "string"},
                            "email": {"type": "string"},
                        },
                    }
                },
                "securitySchemes": {
                    "bearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT",
                    },
                    "apiKey": {"type": "apiKey", "in": "header", "name": "X-API-KEY"},
                },
            },
        }
        self.parser = OpenAPISpecParser(self.sample_spec)

    def test_load_spec_from_dict(self):
        """Test loading a spec from a dictionary."""
        # Create parser directly with dict
        parser = OpenAPISpecParser(self.sample_spec)

        # Verify the parser was created correctly
        self.assertEqual(parser.spec["info"]["title"], "Sample API")
        self.assertEqual(parser.spec["info"]["version"], "1.0.0")

        # Check that reduced_spec was created
        self.assertIsNotNone(parser.reduced_spec)
        self.assertEqual(parser.reduced_spec.description, "A sample API for testing")

    def test_reduce_openapi_spec(self):
        """Test the reduce_openapi_spec function."""
        reduced = reduce_openapi_spec(self.sample_spec)

        # Check the basics
        self.assertEqual(reduced.description, "A sample API for testing")
        self.assertEqual(len(reduced.servers), 2)
        self.assertEqual(reduced.servers[0]["url"], "https://api.example.com/v1")

        # Check that only GET and POST endpoints are included
        self.assertEqual(len(reduced.endpoints), 3)

        # Check endpoint format: tuple of (name, description, docs)
        for endpoint in reduced.endpoints:
            name, description, docs = endpoint
            self.assertIn(name, ["GET /users", "POST /users", "GET /users/{userId}"])
            self.assertIsInstance(description, str)
            self.assertIsInstance(docs, dict)

    def test_get_endpoints(self):
        """Test getting all endpoints from the spec."""
        endpoints = self.parser.get_endpoints()

        # Check that we have the expected number of endpoints
        self.assertEqual(len(endpoints), 3)

        # Endpoints should be a list of tuples: (name, docs_dict)
        for endpoint in endpoints:
            name, description, docs = endpoint
            self.assertIn(name, ["GET /users", "POST /users", "GET /users/{userId}"])
            self.assertIsInstance(description, str)
            self.assertIsInstance(docs, dict)

            # Check specifics based on the endpoint name
            if name == "GET /users":
                self.assertIn("summary", docs)
                self.assertEqual(docs.get("summary"), "List all users")
            elif name == "POST /users":
                self.assertIn("summary", docs)
                self.assertEqual(docs.get("summary"), "Create a user")

    def test_get_base_url(self):
        """Test getting the base URL from the spec."""
        base_url = self.parser.get_base_url()
        self.assertEqual(base_url, "https://api.example.com/v1")

        # Test with empty servers list
        spec_no_servers = dict(self.sample_spec)
        spec_no_servers["servers"] = []
        parser = OpenAPISpecParser(spec_no_servers)
        self.assertEqual(parser.get_base_url(), "")

    def test_get_auth_schemes(self):
        """Test getting authentication schemes from the spec."""
        schemes = self.parser.get_auth_schemes()
        self.assertEqual(len(schemes), 2)
        self.assertIn("bearerAuth", schemes)
        self.assertIn("apiKey", schemes)
        self.assertEqual(schemes["bearerAuth"]["type"], "http")
        self.assertEqual(schemes["bearerAuth"]["scheme"], "bearer")
        self.assertEqual(schemes["apiKey"]["type"], "apiKey")
        self.assertEqual(schemes["apiKey"]["in"], "header")


if __name__ == "__main__":
    unittest.main()
