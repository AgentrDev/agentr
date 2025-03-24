import json
import yaml
from pathlib import Path

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
    
    # Iterate over paths and their operations
    for path, path_info in schema.get('paths', {}).items():
        for method in path_info:
            if method in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']:
                operation = path_info[method]
                method_code = generate_method_code(path, method, operation)
                methods.append(method_code)
    
    # Construct the class code
    class_code = (
        "import requests\n\n"
        "class APIClient:\n"
        "    def __init__(self, base_url):\n"
        "        self.base_url = base_url\n\n" +
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
        func_name = operation['operationId']
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
        body_lines.append(f"        response = requests.{method_func}(url, params=query_params, json=body)")
        body_lines.append("    else:")
        body_lines.append(f"        response = requests.{method_func}(url, params=query_params)")
    else:
        body_lines.append(f"    response = requests.{method_func}(url, params=query_params)")
    
    # Handle response
    body_lines.append("    response.raise_for_status()")
    body_lines.append("    return response.json()")
    
    return signature + '\n' + '\n'.join(body_lines)

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