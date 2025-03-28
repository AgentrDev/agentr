import json
import yaml
import re
import sys
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
    # Improved snake_case conversion
    name = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
    name = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', name).lower()
    name = name.replace('-', '_') # Also replace hyphens often used in operationIds
    # Ensure it doesn't start with underscore after conversions
    name = name.lstrip('_')
    if not name: # Handle cases that become empty
        return "unnamed_operation"
    return name


# Helper function to map OpenAPI types to JSON Schema types (handling anyOf with null)
def _map_openapi_type_to_json_schema_type(schema_info: Optional[Dict[str, Any]]) -> Optional[str]:
    if schema_info is None:
        return None

    # Handle anyOf containing null
    if 'anyOf' in schema_info and isinstance(schema_info['anyOf'], list):
        non_null_type = None
        for item in schema_info['anyOf']:
            if isinstance(item, dict) and item.get('type') != 'null':
                # Recursively call for the non-null type definition
                non_null_type = _map_openapi_type_to_json_schema_type(item)
                if non_null_type:
                    break # Use the first non-null type found
        if non_null_type:
            return non_null_type
        # If only null or empty anyOf, fallback below

    openapi_type = schema_info.get('type')
    if openapi_type is None:
         # If type is missing, but properties exist, it's likely an object
         if 'properties' in schema_info:
             return 'object'
         # If $ref exists, it's often an object, but could be other things. Defaulting to object is safer for tools.
         if '$ref' in schema_info:
             return 'object'
         return None # Cannot determine type

    mapping = {
        "integer": "integer",
        "number": "number",
        "string": "string",
        "boolean": "boolean",
        "array": "array",
        "object": "object",
        # Add more mappings if needed (e.g., date, byte map to string)
    }
    return mapping.get(openapi_type, "string") # Default to string if unknown type


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
    method_defs = [] # Store full method definition strings
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
    # Ensure CamelCase
    class_name = ''.join(word.capitalize() for word in class_name.split('_'))


    # --- Base URL ---
    servers = schema.get('servers', [])
    base_url_from_schema = ""
    if servers and isinstance(servers, list) and servers[0].get('url'):
        base_url_from_schema = servers[0]['url']
        # Basic variable substitution - replace {var} syntax
        base_url_from_schema = re.sub(r'\{[^{}]+\}', '', base_url_from_schema).rstrip('/')


    # --- Iterate over paths and operations ---
    for path, path_info in schema.get('paths', {}).items():
        for method_http in path_info:
            if method_http.lower() in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head', 'trace']:
                operation = path_info[method_http]
                if not isinstance(operation, dict): continue

                # --- Generate Full Method Definition ---
                # generate_method_code now returns the complete method string
                full_method_code, func_name = generate_method_code(path, method_http, operation)
                method_defs.append(full_method_code)

                # --- Gather Tool Information ---
                tool_info = extract_tool_info(func_name, path, method_http, operation)
                if tool_info:
                    tool_definitions.append(tool_info)

    # --- Generate list_tools Method ---
    list_tools_code = generate_list_tools_method(tool_definitions)

    # --- Construct the Class Code ---
    # Notice how `method_defs` are joined *after* __init__
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
        # --- Init Method ---
        f"    def __init__(self, name: str = '{class_name}', integration: Optional[Integration] = None, api_base_url: Optional[str] = None, **kwargs):\n"
        f"        super().__init__(name=name, integration=integration, **kwargs)\n"
        f"        # Prioritize provided api_base_url, then schema, then empty string\n"
        f"        self.api_base_url = api_base_url or '{base_url_from_schema}'\n"
        f"        if not self.api_base_url:\n"
        f"            # Use logger if available, otherwise print\n"
        f"            try:\n"
        f"                from loguru import logger\n"
        f"                logger.warning(f\"No base URL found in schema or provided for {class_name}. API calls may fail.\")\n"
        f"            except ImportError:\n"
        f"                 print(f\"Warning: No base URL found in schema or provided for {class_name}. API calls may fail.\")\n"
        # --- Method Definitions ---
        "\n\n" +
        '\n\n'.join(method_defs) + "\n\n" +
        # --- List Tools Method ---
        list_tools_code
    )
    return class_code


def generate_method_code(path: str, method_http: str, operation: Dict[str, Any]) -> tuple[str, str]:
    """
    Generate the code for a single API method compatible with APIApplication,
    including the signature and body.

    Args:
        path (str): The API path (e.g., '/users/{user_id}').
        method_http (str): The HTTP method (e.g., 'get').
        operation (dict): The operation details from the schema.

    Returns:
        tuple[str, str]: The full Python code string for the method, and the function name.
    """
    # --- Determine function name ---
    if 'operationId' in operation:
        func_name = _generate_python_identifier(operation['operationId'])
    else:
        # Generate name from path and method
        path_parts = path.strip('/').split('/')
        name_parts = [method_http.lower()]
        for part in path_parts:
            if part.startswith('{') and part.endswith('}'):
                param_name = _generate_python_identifier(part[1:-1])
                name_parts.append('by_' + param_name)
            elif part:
                part_name = _generate_python_identifier(part)
                name_parts.append(part_name)
        func_name = '_'.join(name_parts)
        if not func_name: func_name = f"{method_http}_root" # Handle root path case

    # --- Get parameters and request body ---
    parameters = operation.get('parameters', [])
    request_body_spec = operation.get('requestBody')
    has_body = bool(request_body_spec)
    body_content_type = 'application/json' # Default
    if has_body and request_body_spec.get('content'):
        # Prioritize JSON, then form, then first available
        content = request_body_spec['content']
        if 'application/json' in content: body_content_type = 'application/json'
        elif 'application/x-www-form-urlencoded' in content: body_content_type = 'application/x-www-form-urlencoded'
        elif 'multipart/form-data' in content: body_content_type = 'multipart/form-data'
        else: body_content_type = next(iter(content), 'application/json')

    # --- Build function arguments ---
    args = ["self"]
    path_params_names = {p['name'] for p in parameters if p['in'] == 'path'}
    query_params_names = {p['name'] for p in parameters if p['in'] == 'query'}
    header_params_names = {p['name'] for p in parameters if p['in'] == 'header'}

    all_param_names = set()

    # Add path, query, header params
    for param in parameters:
        param_name_orig = param['name']
        param_name_py = _generate_python_identifier(param_name_orig) # Use valid Python name for arg
        if param_name_py in all_param_names: continue
        all_param_names.add(param_name_py)

        param_type = "Any"
        schema_info = param.get('schema', {})
        # More robust type hinting based on schema type and format
        py_type_map = {'string': 'str', 'integer': 'int', 'number': 'float', 'boolean': 'bool', 'array': 'List', 'object': 'Dict'}
        schema_type = schema_info.get('type')
        schema_format = schema_info.get('format')
        param_type = py_type_map.get(schema_type, 'Any')
        if param_type == 'List' and 'items' in schema_info:
             item_type = py_type_map.get(schema_info['items'].get('type'), 'Any')
             param_type = f"List[{item_type}]"
        elif param_type == 'Dict':
             param_type = "Dict[str, Any]" # Simple dict hint

        is_required = param.get('required', False) or param['in'] == 'path'

        if is_required:
             args.append(f"{param_name_py}: {param_type}")
        else:
             args.append(f"{param_name_py}: Optional[{param_type}] = None")

    # Add request body parameter if applicable
    body_param_name = "request_body" # Consistent Python name
    if has_body:
        body_required = request_body_spec.get('required', False)
        # Basic type hinting for body
        body_type = "Any"
        try:
            # Find the schema, potentially dealing with content types
            body_schema = request_body_spec['content'][body_content_type]['schema']
            schema_type = body_schema.get('type')
            py_type_map = {'string': 'str', 'integer': 'int', 'number': 'float', 'boolean': 'bool', 'array': 'List', 'object': 'Dict'}
            body_type = py_type_map.get(schema_type, 'Any')
            if body_type == 'List' and 'items' in body_schema:
                 item_type = py_type_map.get(body_schema['items'].get('type'), 'Any')
                 # TODO: Handle $ref in items
                 body_type = f"List[{item_type}]"
            elif body_type == 'Dict' or body_type == 'Any' and ('properties' in body_schema or '$ref' in body_schema):
                 body_type = "Dict[str, Any]" # Default complex objects/refs to Dict
        except (KeyError, TypeError):
            pass # Keep Any if schema is missing or complex

        if body_required:
            args.append(f"{body_param_name}: {body_type}")
        else:
            args.append(f"{body_param_name}: Optional[{body_type}] = None")

    # --- Method Signature ---
    signature = f"    def {func_name}({', '.join(args)}) -> httpx.Response:"

    # --- Method Body ---
    body_lines = []

    # Docstring
    docstring_lines = [f"        \"\"\"{operation.get('summary', func_name)}\n"]
    if operation.get('description') and operation.get('description') != operation.get('summary'):
         docstring_lines.append(f"\n        {operation.get('description')}\n")
    docstring_lines.append(f"\n        Args:")
    for arg_str in args[1:]: # Skip self
        arg_name = arg_str.split(':')[0].strip()
        # Find original param name for doc lookup if needed (simplified here)
        docstring_lines.append(f"            {arg_name}: From OpenAPI spec.")
    docstring_lines.append(f"\n        Returns:")
    docstring_lines.append(f"            httpx.Response: The raw response from the API call.")
    docstring_lines.append(f"        \"\"\"")
    body_lines.extend(docstring_lines)


    # Path parameters formatting & checks
    path_params_dict_items = []
    for p in parameters:
         if p['in'] == 'path':
             p_name_orig = p['name']
             p_name_py = _generate_python_identifier(p_name_orig)
             path_params_dict_items.append(f"'{p_name_orig}': {p_name_py}")
             # Path params are always required
             body_lines.append(f"        if {p_name_py} is None:")
             body_lines.append(f"            raise ValueError(\"Missing required path parameter: {p_name_py} (original: {p_name_orig})\")")
    body_lines.append(f"        path_params = {{{', '.join(path_params_dict_items)}}}")


    # Format URL
    formatted_path = path if path.startswith('/') else '/' + path
    body_lines.append(f"        url = f\"{{self.api_base_url}}{formatted_path}\".format_map(path_params)")


    # Query parameters & checks
    query_params_items = []
    for p in parameters:
        if p['in'] == 'query':
            p_name_orig = p['name']
            p_name_py = _generate_python_identifier(p_name_orig)
            query_params_items.append(f"('{p_name_orig}', {p_name_py})")
            if p.get('required', False):
                 body_lines.append(f"        if {p_name_py} is None:")
                 body_lines.append(f"            raise ValueError(\"Missing required query parameter: {p_name_py} (original: {p_name_orig})\")")
    query_params_list_str = '[' + ', '.join(query_params_items) + ']'
    body_lines.append(
        f"        query_params = {{k: v for k, v in {query_params_list_str} if v is not None}}"
    )


    # Header parameters
    header_params_items = []
    for p in parameters:
        if p['in'] == 'header':
            p_name_orig = p['name']
            p_name_py = _generate_python_identifier(p_name_orig)
            header_params_items.append(f"('{p_name_orig}', {p_name_py})")
            # Required check for headers can be tricky, often handled by API or base class
    header_params_list_str = '[' + ', '.join(header_params_items) + ']'
    body_lines.append(
        f"        header_params = {{k: v for k, v in {header_params_list_str} if v is not None}}"
    )


    # Make HTTP request using APIApplication methods
    api_method = f"self._{method_http.lower()}"
    request_args = ["url"]
    request_kwargs = ["params=query_params", "headers=header_params"]

    # Body handling
    if method_http.lower() in ['post', 'put', 'patch']:
        if has_body:
             if request_body_spec.get('required', False):
                 body_lines.append(f"        if {body_param_name} is None:")
                 body_lines.append(f"            raise ValueError(\"Missing required request body\")")

             # Add body based on content type
             if body_content_type == 'application/json':
                 request_kwargs.append(f"json={body_param_name}")
             elif 'form' in body_content_type:
                 request_kwargs.append(f"data={body_param_name}")
             else: # Default for other types (e.g., text/plain)
                 request_kwargs.append(f"content={body_param_name}") # Use content for raw data

        body_lines.append(f"        response = {api_method}({', '.join(request_args + request_kwargs)})")

    elif method_http.lower() in ['get', 'delete', 'head', 'options']:
         body_lines.append(f"        response = {api_method}({', '.join(request_args + request_kwargs)})")
    else: # TRACE etc.
         body_lines.append(f"        response = {api_method}({', '.join(request_args + request_kwargs)})")

    # Return statement
    body_lines.append("        # APIApplication's _get/_post/etc. methods handle exceptions")
    body_lines.append("        # and return the httpx.Response object.")
    body_lines.append("        return response")

    # --- Combine signature and body ---
    full_method_code = signature + '\n' + '\n'.join(body_lines)

    return full_method_code, func_name


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
        param_name = _generate_python_identifier(param['name']) # Use pythonic name for tool param
        param_schema = param.get('schema', {})
        param_description = param.get('description', '')
        param_type = _map_openapi_type_to_json_schema_type(param_schema)

        if param_type is None: # Skip params where type cannot be determined
            continue

        prop_def = {
            "description": param_description,
            "type": param_type
        }
        # Add enum, default etc. if present
        if 'enum' in param_schema: prop_def['enum'] = param_schema['enum']
        if 'default' in param_schema: prop_def['default'] = param_schema['default']
        # Handle array items type
        if prop_def['type'] == 'array' and 'items' in param_schema:
            items_schema = param_schema['items']
            item_type = _map_openapi_type_to_json_schema_type(items_schema)
            if item_type:
                prop_def['items'] = { "type": item_type }
                # TODO: Deeper schema nesting for items/objects if needed

        properties[param_name] = prop_def

        if param.get('required', False) or param['in'] == 'path': # Path params always required
            required_params.append(param_name)

    # Process request body
    if request_body_spec:
        body_param_name = "request_body" # Consistent name
        body_required = request_body_spec.get('required', False)
        body_description = request_body_spec.get('description', 'The request body.')

        body_schema = {}
        ref_name = None
        if request_body_spec.get('content'):
            # Find preferred content type schema
            content = request_body_spec['content']
            body_content_type = None
            if 'application/json' in content: body_content_type = 'application/json'
            elif 'application/x-www-form-urlencoded' in content: body_content_type = 'application/x-www-form-urlencoded'
            elif 'multipart/form-data' in content: body_content_type = 'multipart/form-data'
            else: body_content_type = next(iter(content), None)

            if body_content_type and 'schema' in content[body_content_type]:
                body_schema = content[body_content_type]['schema']
                # Check for $ref and add to description
                if '$ref' in body_schema and isinstance(body_schema['$ref'], str):
                    try:
                        ref_name = body_schema['$ref'].split('/')[-1]
                        body_description += f" (Schema: {ref_name})"
                    except: pass # Ignore parsing errors

        body_type = _map_openapi_type_to_json_schema_type(body_schema)
        if body_type is None: body_type = 'object' # Default to object if type is complex/undetermined

        prop_def = {
             "description": body_description.strip(),
             "type": body_type
        }
        # Add details from schema if available (basic)
        if prop_def['type'] == 'object' and 'properties' in body_schema:
             prop_def['properties'] = {} # Placeholder for deeper schema generation if needed
        elif prop_def['type'] == 'array' and 'items' in body_schema:
             items_schema = body_schema['items']
             item_type = _map_openapi_type_to_json_schema_type(items_schema)
             if item_type:
                prop_def['items'] = { "type": item_type }

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
    try:
        tools_list_str = json.dumps(tool_definitions, indent=8) # Indent with 8 spaces
    except TypeError as e:
        print(f"Error serializing tool definitions to JSON: {e}")
        print("Problematic tool definitions:", tool_definitions)
        tools_list_str = "[] # Error during serialization"


    # Add indentation to each line of the generated string
    indented_tools_list_str = "\n".join(["        " + line for line in tools_list_str.splitlines()])

    method_code = (
        "    def list_tools(self) -> List[Dict[str, Any]]:\n"
        "        \"\"\"Lists the tools available in this application, derived from the OpenAPI schema.\"\"\"\n"
        f"        tools = {indented_tools_list_str}\n"
        "        return tools\n"
    )
    return method_code

# Example usage
if __name__ == "__main__":
    schema_file = Path("openapi.json") # Use the provided JSON file

    if not schema_file.exists():
         print(f"Error: Schema file '{schema_file}' not found.", file=sys.stderr)
         # Create a dummy openapi.yaml for testing if needed
         dummy_schema_path = Path("openapi.yaml")
         if not dummy_schema_path.exists():
            print(f"Creating dummy {dummy_schema_path} for testing.")
            # ... (dummy yaml content from previous example) ...
            # with open(dummy_schema_path, "w") as f: f.write(dummy_schema_content)
         # sys.exit(1) # Exit if the target file isn't there


    try:
        print(f"Loading schema from: {schema_file.resolve()}")
        schema_data = load_schema(schema_file)

        print("Generating API client code...")
        generated_code = generate_api_client(schema_data)

        print("\n--- Generated Code ---")
        print(generated_code)
        print("--- End Generated Code ---")

        output_file = Path("generated_api_client.py")
        with open(output_file, "w", encoding='utf-8') as f:
            f.write(generated_code)
        print(f"\nGenerated code written to: {output_file.resolve()}")

    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
