import json
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional # Added for type hinting

# Type hint for OpenAPI Parameter Object (simplified)
ParameterObject = Dict[str, Any]

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


def generate_api_client(schema):
    """
    Generate a Python API client class adhering to agentr.application.APIApplication standard.

    Args:
        schema (dict): The OpenAPI schema as a dictionary.

    Returns:
        str: A string containing the Python code for the API client class.
    """
    methods = []
    tools = [] # To store tool definitions for list_tools

    # --- Extract Base URL ---
    # Attempt to find a base URL from the 'servers' block
    api_base_url = ""
    servers = schema.get('servers', [])
    if servers and isinstance(servers, list) and 'url' in servers[0]:
        # Use the first server URL, remove trailing slash if present
        api_base_url = servers[0]['url'].rstrip('/')
    else:
        # Add a placeholder or warning if no server URL found
        api_base_url = "{YOUR_API_BASE_URL}" # Placeholder
        print("# Warning: No 'servers' found in OpenAPI schema. Set base URL manually.")

    # --- Extract General API Info ---
    info = schema.get('info', {})
    api_title = info.get('title', 'Generated API Client')
    api_version = info.get('version', '')
    api_description = info.get('description', '')
    class_name = "".join(part.capitalize() for part in api_title.replace("-", " ").replace("_", " ").split()) or "GeneratedApiClient"

    # --- Iterate over paths and operations ---
    for path, path_info in schema.get('paths', {}).items():
        # Get parameters defined at the path level (apply to all methods)
        path_level_params: List[ParameterObject] = path_info.get('parameters', [])

        for method in path_info:
            if method.lower() in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']:
                operation: Dict[str, Any] = path_info[method]

                # Get parameters defined specifically for this operation
                operation_params: List[ParameterObject] = operation.get('parameters', [])

                # --- Combine and Override Parameters ---
                # Use a dictionary to handle overrides: (name, in) -> parameter_object
                # Path parameters first
                combined_params_map: Dict[tuple[Optional[str], Optional[str]], ParameterObject] = {
                    (p.get('name'), p.get('in')): p for p in path_level_params if p.get('name') and p.get('in')
                }
                # Update with operation parameters, overriding path ones if name/in match
                combined_params_map.update({
                    (p.get('name'), p.get('in')): p for p in operation_params if p.get('name') and p.get('in')
                })
                # Final list of unique parameters for this operation
                combined_parameters: List[ParameterObject] = list(combined_params_map.values())

                # --- Generate Method and Tool Definition ---
                func_name, method_code = generate_method_code(path, method, operation, combined_parameters, api_base_url)
                tool_definition = generate_tool_definition(func_name, operation, combined_parameters)

                if method_code:
                    methods.append(method_code)
                if tool_definition:
                     tools.append(tool_definition)


    # --- Construct the Class Code ---
    # Header and Imports
    class_header = (
        "from typing import Optional, Dict, Any, List\n"
        "from agentr.application import APIApplication\n"
        "from agentr.integration import Integration # For type hinting\n"
        "from agentr.exceptions import NotAuthorizedError # For context\n"
        "import httpx # For response type hint\n\n"
    )

    # Class Definition Start
    class_def = (
        f"class {class_name}(APIApplication):\n"
        f"    \"\"\"API client generated from OpenAPI schema: {api_title}\n\n"
        f"    Version: {api_version}\n"
        f"    Description: {api_description}\n"
        f"    \"\"\"\n"
        f"    def __init__(self, name: str = '{class_name}', integration: Optional[Integration] = None, api_base_url: Optional[str] = None, **kwargs):\n"
        f"        super().__init__(name=name, integration=integration, **kwargs)\n"
        f"        # Prioritize provided api_base_url, then schema-derived, then maybe raise error or use placeholder\n"
        f"        self.api_base_url = api_base_url or '{api_base_url}'\n"
        f"        if not self.api_base_url or self.api_base_url == '{{YOUR_API_BASE_URL}}':\n"
        f"            # Use logger if available, otherwise print\n"
        f"            try:\n"
        f"                from loguru import logger\n"
        f"                logger.warning(f\"Base URL not configured for {class_name}. Pass 'api_base_url' during init or ensure schema has 'servers'.\")\n"
        f"            except ImportError:\n"
        f"                 print(f\"Warning: Base URL not configured for {class_name}. Pass 'api_base_url' during init or ensure schema has 'servers'.\")\n\n"
    )

    # list_tools method
    tools_list_str = ",\n".join([f"        {json.dumps(tool, indent=16)}" for tool in tools]) # Pretty print tool JSON
    list_tools_method = (
        "    def list_tools(self) -> List[Dict[str, Any]]:\n"
        "        \"\"\"Lists the tools available in this application, derived from the OpenAPI schema.\"\"\"\n"
        f"        tools = [\n{tools_list_str}\n        ]\n" # Indent tools properly
        "        return tools\n"
    )


    # Combine all parts
    class_code = (
        class_header +
        class_def +
        '\n\n'.join(methods) + "\n\n" + # Add newline between methods and list_tools
        list_tools_method
    )
    return class_code


def generate_method_code(path: str, method: str, operation: Dict[str, Any], parameters: List[ParameterObject], api_base_url: str):
    """
    Generate the code for a single API method compatible with APIApplication.

    Args:
        path (str): The API path (e.g., '/users/{user_id}').
        method (str): The HTTP method (e.g., 'get').
        operation (dict): The operation details from the schema.
        parameters (list): The combined list of parameters (path + operation).
        api_base_url (str): The base URL extracted from the schema or provided.

    Returns:
        tuple[str, str]: (function_name, python_code_for_the_method) or (None, None) if invalid
    """
    # --- Determine function name ---
    if 'operationId' in operation:
        func_name = operation['operationId'].replace('.', '_').replace('-', '_') # Sanitize
    else:
        # Generate name from path and method if no operationId
        path_parts = path.strip('/').split('/')
        name_parts = [method.lower()]
        for part in path_parts:
            if part.startswith('{') and part.endswith('}'):
                clean_part = part[1:-1].replace('-', '_') # Sanitize param name
                name_parts.append('by_' + clean_part)
            elif part: # Avoid empty parts from double slashes //
                clean_part = part.replace('-', '_') # Sanitize path part
                name_parts.append(clean_part)
        func_name = '_'.join(name_parts).lower()

    # --- Get request body info ---
    request_body_info = operation.get('requestBody')
    has_body = bool(request_body_info)
    body_required = has_body and request_body_info.get('required', False)
    # Try to get a schema description for the body parameter docstring
    body_description = "The request body."
    body_content = request_body_info.get('content', {}) if has_body else {}
    # Look for application/json first
    json_schema = body_content.get('application/json', {}).get('schema', {})
    if json_schema:
         body_description = f"The request body. (Schema: {json_schema.get('title', 'object')})"
         # If it's a reference, try to add the ref name
         if '$ref' in json_schema:
             ref_name = json_schema['$ref'].split('/')[-1]
             body_description = f"The request body. (Schema: {ref_name})"
    # Add fallback for other content types if needed


    # --- Build function arguments and signature ---
    args = []
    param_definitions = [] # For generating tool parameters later

    # Process combined parameters
    path_param_defs = []
    query_param_defs = []
    header_param_defs = []

    for param in parameters:
        param_name = param.get('name')
        param_in = param.get('in')
        if not param_name or not param_in:
             print(f"Warning: Skipping parameter without name or location ('in') in operation '{func_name}': {param}")
             continue # Skip invalid parameter definitions

        # Sanitize parameter name for Python argument
        arg_name = param_name.replace('-', '_')

        is_required = param.get('required', False)
        param_schema = param.get('schema', {})
        param_type = param_schema.get('type', 'Any')
        py_type = openapi_type_to_python(param_type)

        # Add type hint, default for optional args
        if is_required:
            args.append(f"{arg_name}: {py_type}")
        else:
            args.append(f"{arg_name}: Optional[{py_type}] = None")

        # Store details for tool definition and body generation
        param_def = {
            'name': param_name, # Original name for API call
            'arg_name': arg_name, # Python argument name
            'in': param_in,
            'required': is_required,
            'description': param.get('description', ''),
            'schema': param_schema
        }
        param_definitions.append(param_def)

        # Separate parameters by location for body generation
        if param_in == 'path':
            path_param_defs.append(param_def)
        elif param_in == 'query':
            query_param_defs.append(param_def)
        elif param_in == 'header':
            header_param_defs.append(param_def)
        # Add elif for 'cookie' if needed

    # Add request body argument if applicable
    if has_body:
        # Assuming JSON body for now, might need refinement for other types
        body_arg_type = "Dict[str, Any]" # Default to Dict if schema unknown
        if json_schema:
            # Basic type mapping, can be expanded
            if json_schema.get('type') == 'array':
                 body_arg_type = "List[Dict[str, Any]]" # Assuming array of objects
            elif json_schema.get('type') == 'object':
                 body_arg_type = "Dict[str, Any]"
            elif '$ref' in json_schema:
                 body_arg_type = "Dict[str, Any]" # Represent ref as Dict for now
            # Add more specific types if needed based on schema details

        body_arg_name = "request_body" # Consistent name for body arg
        if body_required:
            args.append(f"{body_arg_name}: {body_arg_type}")
        else:
            args.append(f"{body_arg_name}: Optional[{body_arg_type}] = None")


    signature = f"    def {func_name}(self, {', '.join(args)}) -> httpx.Response:"

    # --- Build method docstring ---
    docstring_lines = [
        f"        \"\"\"{operation.get('summary', func_name)}", # Use summary or func_name
        "" # Empty line
    ]
    if operation.get('description'):
        # Add operation description, handle multi-line descriptions potentially
        desc = operation['description'].strip()
        docstring_lines.extend(f"        {line}" for line in desc.split('\n'))
        docstring_lines.append("") # Empty line after description

    docstring_lines.append("        Args:")
    for param_def in param_definitions:
        # Use arg_name for docstring
        docstring_lines.append(f"            {param_def['arg_name']}: {param_def.get('description', 'From OpenAPI spec.')}")
    if has_body:
        # Add request body description
        docstring_lines.append(f"            {body_arg_name}: {body_description}")

    docstring_lines.append("") # Empty line
    docstring_lines.append("        Returns:")
    docstring_lines.append("            httpx.Response: The raw response from the API call.")
    docstring_lines.append("        \"\"\"")
    docstring = '\n'.join(docstring_lines)


    # --- Build method body ---
    body_lines = []

    # Parameter validation (check required args)
    for param_def in param_definitions:
        if param_def['required']:
            body_lines.append(f"        if {param_def['arg_name']} is None:")
            body_lines.append(f"            raise ValueError(\"Missing required {param_def['in']} parameter: {param_def['arg_name']} (original: {param_def['name']})\")")

    if has_body and body_required:
         body_lines.append(f"        if {body_arg_name} is None:")
         body_lines.append(f"            raise ValueError(\"Missing required request body\")")


    # Path parameters dictionary (using original names)
    path_params_dict = ', '.join([f"'{p['name']}': {p['arg_name']}" for p in path_param_defs])
    body_lines.append(f"        path_params = {{{path_params_dict}}}")

    # Format URL
    body_lines.append(f"        url = f\"{{self.api_base_url}}{path}\".format_map(path_params)")

    # Query parameters dictionary (using original names, filter None)
    query_params_items = ', '.join([f"('{p['name']}', {p['arg_name']})" for p in query_param_defs])
    body_lines.append(
        f"        query_params = {{k: v for k, v in [{query_params_items}] if v is not None}}"
    )

    # Header parameters dictionary (using original names, filter None)
    header_params_items = ', '.join([f"('{p['name']}', {p['arg_name']})" for p in header_param_defs])
    body_lines.append(
        f"        header_params = {{k: v for k, v in [{header_params_items}] if v is not None}}"
    )


    # Make HTTP request using base class methods
    http_verb = method.lower()
    request_args = ["url", "params=query_params", "headers=header_params"]

    if has_body:
        # Pass request_body as json=... if it's not None
        body_lines.append(f"        json_body = {body_arg_name} if {body_arg_name} is not None else None")
        request_args.append("json=json_body")
    elif http_verb in ['post', 'put', 'patch'] and not has_body:
        # Handle cases like POST with only query params (no body)
        pass # No json argument needed

    body_lines.append(f"        response = self._{http_verb}({', '.join(request_args)})")

    # Handle response (delegated to base class, just return)
    body_lines.append("        # APIApplication's _get/_post/etc. methods handle exceptions")
    body_lines.append("        # and return the httpx.Response object.")
    body_lines.append("        return response")

    full_method_code = signature + '\n' + docstring + '\n' + '\n'.join(body_lines)

    return func_name, full_method_code

def generate_tool_definition(func_name: str, operation: Dict[str, Any], parameters: List[ParameterObject]) -> Optional[Dict[str, Any]]:
    """Generates the tool definition dictionary for the list_tools method."""
    if not func_name:
        return None

    tool_params = {"type": "object", "properties": {}, "required": []}

    # Add parameters from query, path, header
    for param in parameters:
        param_name = param.get('name')
        param_in = param.get('in')
        if not param_name or not param_in:
            continue # Skip invalid params

        arg_name = param_name.replace('-', '_') # Use Python argument name
        param_schema = param.get('schema', {})
        param_type = param_schema.get('type', 'string') # Default to string if type missing
        # Basic type mapping for JSON schema in tools
        tool_type = param_type
        if tool_type == "integer":
            tool_type = "number"
        elif tool_type not in ["string", "number", "boolean", "array", "object"]:
            tool_type = "string" # Fallback for unknown types

        tool_params["properties"][arg_name] = {
            "description": param.get('description', ''),
            "type": tool_type,
            # Add format, enum, etc. if needed from param_schema
        }
        if param.get('required', False):
            tool_params["required"].append(arg_name) # Use Python arg name

    # Add request body if it exists
    request_body_info = operation.get('requestBody')
    if request_body_info:
        body_arg_name = "request_body"
        body_description = "The request body."
        # Try getting schema details for description/type
        body_content = request_body_info.get('content', {})
        json_schema = body_content.get('application/json', {}).get('schema', {})
        body_type = "object" # Default type for body
        if json_schema:
             schema_type = json_schema.get('type', 'object')
             if schema_type == 'array':
                 body_type = 'array'
             elif schema_type == 'object':
                 body_type = 'object'
             # Add more specific type info or description if desired
             if '$ref' in json_schema:
                 ref_name = json_schema['$ref'].split('/')[-1]
                 body_description = f"The request body. (Schema: {ref_name})"
             elif json_schema.get('title'):
                 body_description = f"The request body. (Schema: {json_schema['title']})"


        tool_params["properties"][body_arg_name] = {
            "description": body_description,
            "type": body_type, # Typically object or array for JSON body
            # Could potentially embed the actual JSON schema here if needed
        }
        if request_body_info.get('required', False):
            tool_params["required"].append(body_arg_name)

    # Remove 'required' list if it's empty
    if not tool_params["required"]:
        del tool_params["required"]

    tool_definition = {
        "name": func_name,
        "description": operation.get('summary', operation.get('description', func_name)).strip(),
        "parameters": tool_params
    }
    return tool_definition


def openapi_type_to_python(openapi_type: str) -> str:
    """Maps basic OpenAPI types to Python type hints."""
    mapping = {
        "string": "str",
        "integer": "int",
        "number": "float", # Or Decimal, depending on precision needs
        "boolean": "bool",
        "array": "List", # Consider List[Any] or more specific if items specified
        "object": "Dict[str, Any]",
    }
    return mapping.get(openapi_type, "Any") # Default to Any

# Example usage (remains mostly the same, but will now use the modified functions)
if __name__ == "__main__":
    # Load schema from file (e.g., openapi.json or openapi.yaml)
    schema_path = Path('openapi.json') # Or 'openapi.yaml'
    if not schema_path.exists():
         print(f"Error: Schema file {schema_path} not found.")
         # Use the sample schema if file doesn't exist
         print("Using sample schema instead.")
         schema = {
             "openapi": "3.0.0",
             "info": {"title": "Sample API", "version": "1.0"},
             "servers": [{"url": "https://api.example.com/v1"}],
             "paths": {
                 "/users": {
                     "parameters": [ # Path-level parameter
                          {
                              "name": "tenant_id",
                              "in": "header",
                              "required": False,
                              "schema": {"type": "string"}
                          }
                     ],
                     "get": {
                         "summary": "Get users list",
                         "operationId": "get_users",
                         "parameters": [ # Operation-level parameter
                             {
                                 "name": "limit",
                                 "in": "query",
                                 "required": False,
                                 "schema": {"type": "integer"}
                             }
                         ],
                         "responses": {"200": {"description": "A list of users"}}
                     },
                     "post": {
                         "summary": "Create user",
                         "operationId": "create_user",
                         "requestBody": {
                             "required": True,
                             "content": {
                                 "application/json": {
                                     "schema": {
                                         "type": "object",
                                         "properties": {"name": {"type": "string"}, "email": {"type": "string"}},
                                         "required": ["name", "email"]
                                     }
                                 }
                             }
                         },
                         "responses": {"201": {"description": "User created"}}
                     }
                 },
                 "/users/{user_id}": {
                    "parameters": [ # Path-level parameter
                        {
                            "name": "user_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"}
                        }
                    ],
                     "get": {
                         "summary": "Get user by ID",
                         "operationId": "get_user_by_id",
                         # No operation-specific parameters here, uses path-level user_id
                          "responses": {"200": {"description": "User details"}}
                     }
                 }
             }
         }
    else:
        try:
            schema = load_schema(schema_path)
        except Exception as e:
            print(f"Error loading schema from {schema_path}: {e}")
            exit(1)

    code = generate_api_client(schema)
    print(code)
    # Optionally write to a file
    # with open("generated_client.py", "w") as f:
    #     f.write(code)