import json
import yaml
import re
from pathlib import Path


def convert_to_snake_case(identifier: str) -> str:
    """
    Convert a camelCase or PascalCase identifier to snake_case.
    
    Args:
        identifier (str): The string to convert
        
    Returns:
        str: The converted snake_case string
    """
    if not identifier:
        return identifier
    # Add underscore between lowercase and uppercase letters
    result = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', identifier)
    # Convert to lowercase
    return result.lower()


def load_schema(path: Path):
    if path.suffix == '.yaml':
        type = 'yaml'
    else:
        type = 'json'
    with open(path, 'r') as f:
        if type == 'yaml':
            return yaml.safe_load(f)
        else:
            return json.load(f)


def generate_api_client(schema):
    """
    Generate a Python API client class from an OpenAPI schema.
    
    Args:
        schema (dict): The OpenAPI schema as a dictionary.
    
    Returns:
        str: A string containing the Python code for the API client class.
    """
    methods = []
    method_names = []
    
    # Iterate over paths and their operations
    for path, path_info in schema.get('paths', {}).items():
        for method in path_info:
            if method in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']:
                operation = path_info[method]
                method_code, func_name = generate_method_code(path, method, operation)
                methods.append(method_code)
                method_names.append(func_name)
    
    # Generate list_tools method with all the function names
    tools_list = ", ".join([f"self.{name}" for name in method_names])
    list_tools_method = f"    def list_tools(self):\n        return [{tools_list}]\n"
    
    # Construct the class code
    class_code = (
        "from agentr.application import APIApplication\n\n"
        "class APIClient(APIApplication):\n"
        "    def __init__(self, base_url, integration=None, **kwargs):\n"
        "        super().__init__(name='api_client', integration=integration, **kwargs)\n"
        "        self.base_url = base_url\n\n" +
        list_tools_method + "\n" +
        '\n\n'.join(methods)
    )
    return class_code


def generate_method_code(path, method, operation):
    """
    Generate the code for a single API method.
    
    Args:
        path (str): The API path (e.g., '/users/{user_id}').
        method (str): The HTTP method (e.g., 'get').
        operation (dict): The operation details from the schema.
    
    Returns:
        str: The Python code for the method.
    """
    # Determine function name
    if 'operationId' in operation:
        raw_name = operation['operationId']
        # Clean invalid characters first
        cleaned_name = raw_name.replace('.', '_').replace('-', '_')
        # Then convert to snake_case
        func_name = convert_to_snake_case(cleaned_name)
    else:
        # Generate name from path and method
        path_parts = path.strip('/').split('/')
        name_parts = [method]
        for part in path_parts:
            if part.startswith('{') and part.endswith('}'):
                name_parts.append('by_' + part[1:-1])
            else:
                name_parts.append(part)
        func_name = '_'.join(name_parts).replace('-', '_').lower()
    
    # Get parameters and request body
    parameters = operation.get('parameters', [])
    has_body = 'requestBody' in operation
    body_required = has_body and operation['requestBody'].get('required', False)
    
    # Build function arguments
    args = []
    for param in parameters:
        if param.get('required', False):
            args.append(param['name'])
        else:
            args.append(f"{param['name']}=None")
    if has_body:
        args.append('body' if body_required else 'body=None')
    signature = f"def {func_name}(self, {', '.join(args)}):"
    
    # Build method body
    body_lines = []
    
    # Path parameters
    path_params = [p for p in parameters if p['in'] == 'path']
    path_params_dict = ', '.join([f"'{p['name']}': {p['name']}" for p in path_params])
    body_lines.append(f"    path_params = {{{path_params_dict}}}")
    
    # Query parameters
    query_params = [p for p in parameters if p['in'] == 'query']
    query_params_items = ', '.join([f"('{p['name']}', {p['name']})" for p in query_params])
    body_lines.append(
        f"    query_params = {{k: v for k, v in [{query_params_items}] if v is not None}}"
    )
    
    # Format URL
    body_lines.append(f"    url = f\"{{self.base_url}}{path}\".format_map(path_params)")
    
    # Make HTTP request
    method_func = method.lower()
    if has_body:
        body_lines.append("    if body is not None:")
        body_lines.append(f"        response = self._{method_func}(url, body)")
        body_lines.append("    else:")
        body_lines.append(f"        response = self._{method_func}(url, {{}})")
    else:
        if method_func == "get" or method_func == "delete":
            body_lines.append(f"    response = self._{method_func}(url, query_params)")
        else:
            body_lines.append(f"    response = self._{method_func}(url, {{}})")
    
    # Handle response
    body_lines.append("    if hasattr(response, 'json'):")
    body_lines.append("        return response.json()")
    body_lines.append("    return response")
    
    method_code = signature + '\n' + '\n'.join(body_lines)
    return method_code, func_name  # Return both the code and the function name


# Example usage
if __name__ == "__main__":
    # Sample OpenAPI schema
    schema = {
        "paths": {
            "/users": {
                "get": {
                    "summary": "Get a list of users",
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer"}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "A list of users",
                            "content": {"application/json": {"schema": {"type": "array"}}}
                        }
                    }
                },
                "post": {
                    "summary": "Create a user",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"name": {"type": "string"}}
                                }
                            }
                        }
                    },
                    "responses": {
                        "201": {"description": "User created"}
                    }
                }
            },
            "/users/{user_id}": {
                "get": {
                    "summary": "Get a user by ID",
                    "parameters": [
                        {
                            "name": "user_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"}
                        }
                    ],
                    "responses": {
                        "200": {"description": "User details"}
                    }
                }
            }
        }
    }
    

    schema = load_schema('openapi.yaml')
    code = generate_api_client(schema)
    print(code)