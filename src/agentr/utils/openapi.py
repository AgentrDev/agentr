# --- START OF FILE openapi.py ---

import json
import yaml
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

# Helper function to create valid Python identifiers (basic version)
def _generate_python_identifier(name: str) -> str:
    # Remove invalid characters
    name = re.sub(r'\W|^(?=\d)', '_', name)
    # Handle potential empty strings or leading underscores after cleaning
    if not name or name.startswith('_'):
        name = 'operation' + name
    # Convert to snake_case (optional, but common for methods)
    name = re.sub('([A-Z]+)', r'_\1', name).lower().strip('_')
    return name

# Helper function to map OpenAPI types to JSON Schema types (basic)
def _map_openapi_type_to_json_schema_type(openapi_type: Optional[str]) -> Optional[str]:
    if openapi_type is None:
        return None
    mapping = {
        "integer": "integer",
        "number": "number",
        "string": "string",
        "boolean": "boolean",
        "array": "array",
        "object": "object",
        # Add more mappings if needed (e.g., date, byte)
    }
    return mapping.get(openapi_type, "string") # Default to string if unknown

def load_schema(path: Path) -> Dict[str, Any]:
    """Loads an OpenAPI schema from a YAML or JSON file."""
    if not path.is_file():
        raise FileNotFoundError(f"Schema file not found: {path}")
    suffix = path.suffix.lower()
    if suffix == '.yaml' or suffix == '.yml':
        loader = yaml.safe_load
    elif suffix == '.json':
        loader = json.load
    else:
        raise ValueError(f"Unsupported schema file type: {suffix}. Use .yaml or .json.")

    with open(path, 'r', encoding='utf-8') as f:
        try:
            return loader(f)
        except Exception as e:
            raise ValueError(f"Error parsing schema file {path}: {e}") from e


def generate_api_client(schema: Dict[str, Any]) -> str:
    """
    Generate a Python API client class inheriting from APIApplication
    from an OpenAPI schema.

    Args:
        schema (dict): The OpenAPI schema as a dictionary.

    Returns:
        str: A string containing the Python code for the API client class.
    """
    methods = []
    tool_definitions = [] # Store data for list_tools

    # --- Class Name ---
    info = schema.get('info', {})
    title = info.get('title', 'GeneratedApi')
    # Sanitize title to create a valid Python class name (CamelCase)
    class_name = re.sub(r'[^a-zA-Z0-9_]', '', title).strip()
    if not class_name:
        class_name = "GeneratedApiApplication"
    elif not class_name[0].isalpha():
         class_name = "Api" + class_name # Ensure starts with letter
    class_name = class_name[0].upper() + class_name[1:] # Ensure CamelCase

    # --- Base URL ---
    # Try to get the first server URL, default to empty string
    servers = schema.get('servers', [])
    base_url_from_schema = ""
    if servers and isinstance(servers, list) and servers[0].get('url'):
        base_url_from_schema = servers[0]['url']
        # Basic variable substitution (e.g., { R } -> R) - might need enhancement
        base_url_from_schema = re.sub(r'\{.*?\}', '', base_url_from_schema).rstrip('/')


    # --- Iterate over paths and operations ---
    for path, path_info in schema.get('paths', {}).items():
        for method_http in path_info:
            # Ensure it's a valid HTTP method defined in the spec
            if method_http.lower() in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head', 'trace']:
                operation = path_info[method_http]
                if not isinstance(operation, dict): continue # Skip non-dict entries like 'parameters' at path level

                # --- Generate Method Code ---
                method_code, func_name = generate_method_code(path, method_http, operation)
                methods.append(method_code)

                # --- Gather Tool Information ---
                tool_info = extract_tool_info(func_name, path, method_http, operation)
                if tool_info:
                    tool_definitions.append(tool_info)

    # --- Generate list_tools Method ---
    list_tools_code = generate_list_tools_method(tool_definitions)

    # --- Construct the Class Code ---
    class_code = (
        "from typing import Optional, Dict, Any, List\n"
        "from agentr.application import APIApplication\n"
        "from agentr.integration import Integration # For type hinting\n"
        "from agentr.exceptions import NotAuthorizedError # For context\n"
        "import httpx # For response type hint\n\n\n"
        f"class {class_name}(APIApplication):\n"
        f"    \"\"\"API client generated from OpenAPI schema: {info.get('title', 'N/A')}\n\n"
        f"    Version: {info.get('version', 'N/A')}\n"
        f"    Description: {info.get('description', '').strip()}\n"
        f"    \"\"\"\n"
        f"    def __init__(self, name: str = '{class_name}', integration: Optional[Integration] = None, api_base_url: Optional[str] = None, **kwargs):\n"
        f"        super().__init__(name=name, integration=integration, **kwargs)\n"
        f"        # Prioritize provided api_base_url, then schema, then empty string\n"
        f"        self.api_base_url = api_base_url or '{base_url_from_schema}'\n"
        f"        if not self.api_base_url:\n"
        f"            print(f\"Warning: No base URL found in schema or provided for {class_name}. API calls may fail.\")\n\n" +
        '\n\n'.join(methods) + "\n\n" +
        list_tools_code
    )
    return class_code


def generate_method_code(path: str, method_http: str, operation: Dict[str, Any]) -> tuple[str, str]:
    """
    Generate the code for a single API method compatible with APIApplication.

    Args:
        path (str): The API path (e.g., '/users/{user_id}').
        method_http (str): The HTTP method (e.g., 'get').
        operation (dict): The operation details from the schema.

    Returns:
        tuple[str, str]: The Python code for the method, and the function name.
    """
    # --- Determine function name ---
    if 'operationId' in operation:
        # Use operationId directly if available and valid
        func_name = _generate_python_identifier(operation['operationId'])
    else:
        # Generate name from path and method
        path_parts = path.strip('/').split('/')
        name_parts = [method_http.lower()]
        for part in path_parts:
            if part.startswith('{') and part.endswith('}'):
                # Sanitize parameter name for function name part
                param_name = _generate_python_identifier(part[1:-1])
                name_parts.append('by_' + param_name)
            elif part: # Avoid empty parts from //
                 # Sanitize static path part
                part_name = _generate_python_identifier(part)
                name_parts.append(part_name)
        func_name = '_'.join(name_parts)

    # --- Get parameters and request body ---
    parameters = operation.get('parameters', [])
    request_body_spec = operation.get('requestBody')
    has_body = bool(request_body_spec)
    # Default body content type (can be refined)
    body_content_type = 'application/json'
    if has_body and request_body_spec.get('content'):
        # Get the first content type, default to json
        body_content_type = next(iter(request_body_spec['content']), 'application/json')


    # --- Build function arguments ---
    args = ["self"]
    path_params_names = {p['name'] for p in parameters if p['in'] == 'path'}
    query_params_names = {p['name'] for p in parameters if p['in'] == 'query'}
    header_params_names = {p['name'] for p in parameters if p['in'] == 'header'} # Track header params

    all_param_names = set() # Track to avoid duplicates if defined in multiple places

    # Add path and query params first (often required)
    for param in parameters:
        param_name = param['name']
        if param_name in all_param_names: continue
        all_param_names.add(param_name)

        # Basic type hinting (can be expanded)
        param_type = "Any"
        schema_info = param.get('schema', {})
        if 'type' in schema_info:
            py_type = {'string': 'str', 'integer': 'int', 'number': 'float', 'boolean': 'bool', 'array': 'List', 'object': 'Dict'}.get(schema_info['type'], 'Any')
            param_type = py_type

        if param.get('required', False):
             args.append(f"{param_name}: {param_type}")
        else:
            args.append(f"{param_name}: Optional[{param_type}] = None")

    # Add request body parameter if applicable
    if has_body:
        body_required = request_body_spec.get('required', False)
        body_param_name = "request_body" # Use a distinct name
        # Basic type hinting for body
        body_type = "Any"
        try:
            body_schema = request_body_spec['content'][body_content_type]['schema']
            if 'type' in body_schema:
                 body_type = {'string': 'str', 'integer': 'int', 'number': 'float', 'boolean': 'bool', 'array': 'List', 'object': 'Dict'}.get(body_schema['type'], 'Any')
        except KeyError:
            pass # Keep Any if schema is complex or missing

        if body_required:
            args.append(f"{body_param_name}: {body_type}")
        else:
            args.append(f"{body_param_name}: Optional[{body_type}] = None")
            
    # Add header parameters (usually optional)
    for param in parameters:
        if param['in'] == 'header':
            param_name = param['name']
            if param_name in all_param_names: continue
            all_param_names.add(param_name)
            # Basic type hinting
            param_type = "Any"
            schema_info = param.get('schema', {})
            if 'type' in schema_info:
                py_type = {'string': 'str', 'integer': 'int', 'number': 'float', 'boolean': 'bool'}.get(schema_info['type'], 'Any') # No list/dict for headers usually
                param_type = py_type
                
            # Headers often not marked required in schema but might be needed
            # Defaulting to optional for generation simplicity
            args.append(f"{param_name}: Optional[{param_type}] = None")


    signature = f"    def {func_name}({', '.join(args)}) -> httpx.Response:" # Return raw response for flexibility


    # --- Build method body ---
    body_lines = []
    docstring_lines = [f"        \"\"\"{operation.get('summary', '')}\n"]
    if operation.get('description'):
         docstring_lines.append(f"        {operation.get('description')}\n")
    docstring_lines.append(f"        Args:")
    # Add args documentation (simplified)
    for arg in args[1:]: # Skip self
        arg_name = arg.split(':')[0].strip()
        docstring_lines.append(f"            {arg_name}: From OpenAPI spec.") # TODO: Add description from schema if possible
    docstring_lines.append(f"\n        Returns:")
    docstring_lines.append(f"            httpx.Response: The raw response from the API call.")
    docstring_lines.append(f"        \"\"\"")
    body_lines.extend(docstring_lines)


    # Path parameters formatting
    path_params_dict_str = ', '.join([f"'{p['name']}': {p['name']}" for p in parameters if p['in'] == 'path'])
    body_lines.append(f"        path_params = {{{path_params_dict_str}}}")
    # Check required path params
    for p in parameters:
        if p['in'] == 'path' and p.get('required', True): # Path params are implicitly required
             body_lines.append(f"        if {p['name']} is None:")
             body_lines.append(f"            raise ValueError(\"Missing required path parameter: {p['name']}\")")


    # Format URL
    # Ensure path starts with '/' if base_url is present, otherwise handle relative paths
    formatted_path = path if path.startswith('/') else '/' + path
    body_lines.append(f"        url = f\"{{self.api_base_url}}{formatted_path}\".format_map(path_params)")

    # Query parameters
    query_params_items = []
    for p in parameters:
        if p['in'] == 'query':
            query_params_items.append(f"('{p['name']}', {p['name']})")
            # Check required query params (if explicitly required)
            if p.get('required', False):
                 body_lines.append(f"        if {p['name']} is None:")
                 body_lines.append(f"            raise ValueError(\"Missing required query parameter: {p['name']}\")")

    query_params_list_str = '[' + ', '.join(query_params_items) + ']'
    body_lines.append(
        f"        query_params = {{k: v for k, v in {query_params_list_str} if v is not None}}"
    )

    # Header parameters
    header_params_items = []
    for p in parameters:
        if p['in'] == 'header':
            header_params_items.append(f"('{p['name']}', {p['name']})")
            # No check for required here, handled by APIApplication potentially

    header_params_list_str = '[' + ', '.join(header_params_items) + ']'
    body_lines.append(
        f"        header_params = {{k: v for k, v in {header_params_list_str} if v is not None}}"
    )

    # Make HTTP request using APIApplication methods
    api_method = f"self._{method_http.lower()}"
    request_args = ["url"]
    request_kwargs = ["params=query_params", "headers=header_params"] # Pass headers

    if method_http.lower() in ['post', 'put', 'patch']:
        if has_body:
             # Check required body
             if request_body_spec.get('required', False):
                 body_lines.append(f"        if {body_param_name} is None:")
                 body_lines.append(f"            raise ValueError(\"Missing required request body\")")

             # Pass body as 'json' assuming application/json.
             # More complex handling needed for other content types (form data etc.)
             if body_content_type == 'application/json':
                 request_kwargs.append(f"json={body_param_name}")
             elif 'form' in body_content_type: # Basic form data handling
                 request_kwargs.append(f"data={body_param_name}")
             else: # Default or other types - pass as data, might need adjustment
                 request_kwargs.append(f"data={body_param_name}") # Or content= ? Check httpx/APIApplication

        body_lines.append(f"        response = {api_method}({', '.join(request_args + request_kwargs)})")

    elif method_http.lower() in ['get', 'delete', 'head', 'options']:
         # No body for these typically
         body_lines.append(f"        response = {api_method}({', '.join(request_args + request_kwargs)})")
    else: # TRACE etc. - handle simply
         body_lines.append(f"        response = {api_method}({', '.join(request_args + request_kwargs)})")


    # Return the response (APIApplication handles raise_for_status)
    body_lines.append("        # APIApplication's _get/_post/etc. methods handle exceptions\n        # and return the httpx.Response object or raise/return error info.")
    body_lines.append("        return response")

    return '\n'.join(body_lines), func_name


def extract_tool_info(func_name: str, path: str, method_http: str, operation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extracts information needed for list_tools from an operation."""
    if not func_name or not operation:
        return None

    tool_name = func_name
    description = operation.get('summary', operation.get('description', f'Invoke {func_name}'))
    parameters = operation.get('parameters', [])
    request_body_spec = operation.get('requestBody')

    # --- Build JSON Schema for parameters ---
    properties = {}
    required_params = []

    # Process path, query, header, cookie parameters
    for param in parameters:
        param_name = param['name']
        param_schema = param.get('schema', {})
        prop_def = {
            "description": param.get('description', ''),
            "type": _map_openapi_type_to_json_schema_type(param_schema.get('type'))
        }
        # Add enum, default etc. if present
        if 'enum' in param_schema: prop_def['enum'] = param_schema['enum']
        if 'default' in param_schema: prop_def['default'] = param_schema['default']
        # Handle array items type
        if prop_def['type'] == 'array' and 'items' in param_schema:
            items_schema = param_schema['items']
            prop_def['items'] = { "type": _map_openapi_type_to_json_schema_type(items_schema.get('type'))}
            # TODO: Deeper schema nesting for items/objects if needed

        properties[param_name] = prop_def

        if param.get('required', False) or param['in'] == 'path': # Path params always required
            required_params.append(param_name)

    # Process request body
    if request_body_spec:
        body_param_name = "request_body" # Consistent name
        body_required = request_body_spec.get('required', False)
        body_description = request_body_spec.get('description', 'The request body.')

        # Try to get schema for the primary content type
        body_schema = {}
        body_content_type = None
        if request_body_spec.get('content'):
            content = request_body_spec['content']
            # Prefer JSON, then form, then first available
            if 'application/json' in content:
                body_content_type = 'application/json'
            elif 'application/x-www-form-urlencoded' in content:
                 body_content_type = 'application/x-www-form-urlencoded'
            elif 'multipart/form-data' in content:
                 body_content_type = 'multipart/form-data'
            else:
                 body_content_type = next(iter(content), None)

            if body_content_type and 'schema' in content[body_content_type]:
                body_schema = content[body_content_type]['schema']

        prop_def = {
             "description": body_description,
             "type": _map_openapi_type_to_json_schema_type(body_schema.get('type', 'object')) # Default to object if type missing
        }
        # Add details from schema if available (basic)
        if prop_def['type'] == 'object' and 'properties' in body_schema:
             # Could recursively define properties here, keeping it simple for now
             prop_def['properties'] = {} # Placeholder
        elif prop_def['type'] == 'array' and 'items' in body_schema:
             items_schema = body_schema['items']
             prop_def['items'] = { "type": _map_openapi_type_to_json_schema_type(items_schema.get('type'))}

        properties[body_param_name] = prop_def

        if body_required:
            required_params.append(body_param_name)


    tool_parameters_schema = {
        "type": "object",
        "properties": properties,
    }
    if required_params:
        tool_parameters_schema["required"] = sorted(list(set(required_params))) # Ensure unique and sorted

    return {
        "name": tool_name,
        "description": description,
        "parameters": tool_parameters_schema
    }


def generate_list_tools_method(tool_definitions: List[Dict[str, Any]]) -> str:
    """Generates the list_tools method code."""
    if not tool_definitions:
        return (
            "    def list_tools(self) -> List[Dict[str, Any]]:\n"
            "        \"\"\"Lists the tools available in this application.\"\"\"\n"
            "        return []\n"
        )

    # Use json.dumps for pretty printing the list of dicts within the code
    # Need to indent it correctly for the method body
    tools_list_str = json.dumps(tool_definitions, indent=8) # Indent with 8 spaces for inside method

    # Add indentation to each line of the generated string
    indented_tools_list_str = "\n".join(["        " + line for line in tools_list_str.splitlines()])

    method_code = (
        "    def list_tools(self) -> List[Dict[str, Any]]:\n"
        "        \"\"\"Lists the tools available in this application, derived from the OpenAPI schema.\"\"\"\n"
        f"        tools = {indented_tools_list_str}\n"
        "        return tools\n"
    )
    return method_code

# Example usage - replace with your actual schema file path
if __name__ == "__main__":
    # Create a dummy openapi.yaml for testing if it doesn't exist
    dummy_schema_path = Path("openapi.yaml")
    if not dummy_schema_path.exists():
        print(f"Creating dummy {dummy_schema_path} for testing.")
        dummy_schema_content = """
openapi: 3.0.0
info:
  title: Sample Pet Store API
  version: 1.0.0
  description: A sample API to demonstrate OpenAPI generation for AgentR
servers:
  - url: https://api.example.com/v1
    description: Production server
paths:
  /pets:
    get:
      summary: List all pets
      operationId: listPets
      parameters:
        - name: limit
          in: query
          description: How many items to return at one time (max 100)
          required: false
          schema:
            type: integer
            format: int32
      responses:
        '200':
          description: A paged array of pets
          content:
            application/json:
              schema:
                type: array
                items:
                  type: object
                  properties:
                    id: { type: integer }
                    name: { type: string }
    post:
      summary: Create a pet
      operationId: createPet
      requestBody:
        description: The pet to create
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [name]
              properties:
                name: { type: string }
                tag: { type: string }
      responses:
        '201':
          description: Null response
  /pets/{petId}:
    get:
      summary: Info for a specific pet
      operationId: showPetById
      parameters:
        - name: petId
          in: path
          required: true
          description: The id of the pet to retrieve
          schema:
            type: string
      responses:
        '200':
          description: Expected response to a valid request
          content:
            application/json:
              schema:
                  type: object
                  properties:
                    id: { type: integer }
                    name: { type: string }
"""
        with open(dummy_schema_path, "w") as f:
            f.write(dummy_schema_content)

    schema_file = Path("openapi.yaml") # Or Path("openapi.json")

    try:
        print(f"Loading schema from: {schema_file.resolve()}")
        schema_data = load_schema(schema_file)

        print("Generating API client code...")
        generated_code = generate_api_client(schema_data)

        print("\n--- Generated Code ---")
        print(generated_code)
        print("--- End Generated Code ---")

        # Optional: Write to a file
        output_file = Path("generated_api_client.py")
        with open(output_file, "w", encoding='utf-8') as f:
            f.write(generated_code)
        print(f"\nGenerated code written to: {output_file.resolve()}")

    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# --- END OF FILE openapi.py ---