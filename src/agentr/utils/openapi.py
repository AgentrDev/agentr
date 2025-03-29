import json
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional # Added for type hinting
import httpx # Ensure this is imported

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

    # --- Generate Class Name (Modified Logic) ---
    base_name = "".join(part.capitalize() for part in api_title.replace("-", " ").replace("_", " ").split())
    sanitized_name = ''.join(c for c in base_name if c.isalnum() or c == '_')

    if not sanitized_name:
        sanitized_name = "GeneratedApiClient" # Use default if sanitization removed everything

    if sanitized_name[0].isdigit():
        class_name = "Api" + sanitized_name
    # 5. Check if the first character is an underscore (less common, but possible)
    elif sanitized_name.startswith('_'):
         class_name = "Api" + sanitized_name
    else:
        # Use the sanitized name if it starts with a valid character (letter)
        class_name = sanitized_name
        
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
                func_name, method_code, final_defs = generate_method_code(path, method, operation, combined_parameters, api_base_url)
                            
                if func_name and final_defs is not None: # Check if generation was successful
                    # *** MODIFIED CALL: Pass final_defs ***
                    tool_definition = generate_tool_definition(func_name, operation, final_defs) # Pass final_defs here

                    if method_code:
                        methods.append(method_code)
                    if tool_definition:
                         tools.append(tool_definition)
                else:
                    print(f"Warning: Skipping method/tool generation for {method.upper()} {path} due to errors in generate_method_code.")


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


# You should also have the openapi_type_to_python helper function defined somewhere
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

def generate_method_code(path: str, method: str, operation: Dict[str, Any], parameters: List[Dict[str, Any]], api_base_url: str):
    """
    Generate the code for a single API method compatible with APIApplication.

    Args:
        path (str): The API path (e.g., '/users/{user_id}').
        method (str): The HTTP method (e.g., 'get').
        operation (dict): The operation details from the schema.
        parameters (list): The combined list of parameters (path + operation).
        api_base_url (str): The base URL extracted from the schema or provided.

    Returns:
        # *** MODIFIED DOCSTRING RETURN TYPE HINT ***
        tuple[Optional[str], Optional[str], Optional[List[Dict[str, Any]]]]: (function_name, python_code_for_the_method, final_parameter_definitions) or (None, None, None) if invalid
    """
    # --- Determine function name ---
    if 'operationId' in operation:
        # Sanitize operationId: replace dots and hyphens with underscores
        func_name = operation['operationId'].replace('.', '_').replace('-', '_')
    else:
        # Generate name from path and method if no operationId
        path_parts = path.strip('/').split('/')
        name_parts = [method.lower()]
        for part in path_parts:
            if part.startswith('{') and part.endswith('}'):
                # Sanitize param name in path part
                clean_part = part[1:-1].replace('-', '_')
                name_parts.append('by_' + clean_part)
            elif part: # Avoid empty parts from double slashes //
                # Sanitize path part itself
                clean_part = part.replace('-', '_')
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
    body_arg_type = "Dict[str, Any]" # Default body type hint

    if json_schema:
         schema_title = json_schema.get('title')
         schema_ref = json_schema.get('$ref')
         schema_type = json_schema.get('type')

         if schema_ref:
             ref_name = schema_ref.split('/')[-1]
             body_description = f"The request body. (Schema: {ref_name})"
             # Keep default body_arg_type for refs, or enhance if resolving refs
         elif schema_title:
              body_description = f"The request body. (Schema: {schema_title})"
         elif schema_type:
              body_description = f"The request body. (Type: {schema_type})"


         # Basic type mapping for body argument hint
         if schema_type == 'array':
             # Could try to get item type, but default to List[Any] or List[Dict]
             items_schema = json_schema.get('items', {})
             items_type = items_schema.get('type', 'Any')
             py_item_type = openapi_type_to_python(items_type)
             # If items are complex ($ref or object), use Dict or Any
             if py_item_type in ["Dict[str, Any]", "Any"] and items_schema:
                 py_item_type = "Dict[str, Any]" # Assume array of objects commonly
             elif py_item_type == "List": # Array of arrays? Use Any
                  py_item_type = "Any"
             body_arg_type = f"List[{py_item_type}]"

         elif schema_type == 'object':
             body_arg_type = "Dict[str, Any]"
         elif schema_type: # string, number, integer, boolean
              body_arg_type = openapi_type_to_python(schema_type)


    # --- Build function arguments and signature ---
    args = []
    # Keep track of python argument names we've already assigned
    assigned_arg_names = set()
    # Store the final parameter definitions with potentially modified arg_names
    final_param_defs = []

    # Process combined parameters to create unique arg names
    for param in parameters:
        param_name = param.get('name')
        param_in = param.get('in')
        if not param_name or not param_in:
             print(f"Warning: Skipping parameter without name or location ('in') in operation '{func_name}': {param}")
             continue # Skip invalid parameter definitions

        # 1. Calculate initial Python argument name (replace hyphens)
        initial_arg_name = param_name.replace('-', '_')

        # 2. Check for collision and disambiguate if needed
        unique_arg_name = initial_arg_name
        if initial_arg_name in assigned_arg_names:
            # Collision detected! Append the location to disambiguate
            unique_arg_name = f"{initial_arg_name}_{param_in}"
            # Add a counter just in case even this collides (very unlikely)
            counter = 2
            while unique_arg_name in assigned_arg_names:
                 unique_arg_name = f"{initial_arg_name}_{param_in}{counter}"
                 counter += 1

        # 3. Store the final definition with the unique name
        is_required = param.get('required', False)
        param_schema = param.get('schema', {})
        param_type = param_schema.get('type', 'Any') # Default to Any if schema or type missing
        py_type = openapi_type_to_python(param_type)

        param_def = {
            'name': param_name,            # Original name for API call
            'arg_name': unique_arg_name,   # Unique Python argument name
            'in': param_in,
            'required': is_required,
            'description': param.get('description', ''),
            'schema': param_schema,
            'py_type': py_type            # Store python type for reuse
        }
        final_param_defs.append(param_def)
        assigned_arg_names.add(unique_arg_name) # Mark this unique name as used

    # Now build the Python argument list string using the final definitions
    for p_def in final_param_defs:
        arg_name = p_def['arg_name']
        py_type = p_def['py_type']
        if p_def['required']:
            args.append(f"{arg_name}: {py_type}")
        else:
            args.append(f"{arg_name}: Optional[{py_type}] = None")

    # Add request body argument if applicable
    body_arg_name = "request_body" # Consistent name for body arg
    if has_body:
        # Ensure the body argument name doesn't collide (extremely unlikely but possible)
        while body_arg_name in assigned_arg_names:
             body_arg_name = f"_{body_arg_name}" # Prepend underscore

        if body_required:
            args.append(f"{body_arg_name}: {body_arg_type}")
        else:
            args.append(f"{body_arg_name}: Optional[{body_arg_type}] = None")
        # No need to add body_arg_name to assigned_arg_names here, as param loop is finished

    # Final signature string
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
    # Use the unique arg_name from final_param_defs for the docstring
    for p_def in final_param_defs:
        docstring_lines.append(f"            {p_def['arg_name']}: {p_def.get('description', 'From OpenAPI spec.')}")
    if has_body:
        # Add request body description using the final body_arg_name
        docstring_lines.append(f"            {body_arg_name}: {body_description}")

    docstring_lines.append("") # Empty line
    docstring_lines.append("        Returns:")
    docstring_lines.append("            httpx.Response: The raw response from the API call.")
    docstring_lines.append("        \"\"\"")
    docstring = '\n'.join(docstring_lines)

    # --- Build method body ---
    body_lines = []

    # Parameter validation (check required args using unique arg_name)
    for p_def in final_param_defs:
        if p_def['required']:
            body_lines.append(f"        if {p_def['arg_name']} is None:")
            # Provide both original and python name in error for clarity
            body_lines.append(f"            raise ValueError(\"Missing required {p_def['in']} parameter: {p_def['arg_name']} (original: {p_def['name']})\")")

    if has_body and body_required:
         body_lines.append(f"        if {body_arg_name} is None:")
         body_lines.append(f"            raise ValueError(\"Missing required request body\")")


    # Path parameters dictionary (using original name as key, unique arg_name as value source)
    path_params_dict = ', '.join([f"'{p['name']}': {p['arg_name']}" for p in final_param_defs if p['in'] == 'path'])
    body_lines.append(f"        path_params = {{{path_params_dict}}}")

    # Format URL (remains the same, uses path placeholders like {param_name})
    body_lines.append(f"        url = f\"{{self.api_base_url}}{path}\".format_map(path_params)")

    # Query parameters dictionary (original name -> unique arg_name, filter None)
    query_params_items = ', '.join([f"('{p['name']}', {p['arg_name']})" for p in final_param_defs if p['in'] == 'query'])
    body_lines.append(
        f"        query_params = {{k: v for k, v in [{query_params_items}] if v is not None}}"
    )

    # Header parameters dictionary (original name -> unique arg_name, filter None)
    header_params_items = ', '.join([f"('{p['name']}', {p['arg_name']})" for p in final_param_defs if p['in'] == 'header'])
    body_lines.append(
        f"        header_params = {{k: v for k, v in [{header_params_items}] if v is not None}}"
    )
    # Add cookie params if needed:
    # cookie_params_items = ', '.join([f"('{p['name']}', {p['arg_name']})" for p in final_param_defs if p['in'] == 'cookie'])
    # body_lines.append(f"        cookie_params = {{k: v for k, v in [{cookie_params_items}] if v is not None}}")


    # Make HTTP request using base class methods
    http_verb = method.lower()
    # Base arguments for the APIApplication helper methods
    request_args = ["url", "params=query_params", "headers=header_params"]
    # Add cookies if implemented: request_args.append("cookies=cookie_params")

    if has_body:
        # Pass request_body as json=... if it's not None
        # Use the final (potentially modified) body_arg_name
        body_lines.append(f"        json_body = {body_arg_name} if {body_arg_name} is not None else None")
        request_args.append("json=json_body")
    elif http_verb in ['post', 'put', 'patch'] and not has_body:
        # Handle cases like POST/PUT/PATCH with only query/path/header params (no body)
        pass # No json argument needed, already handled by base case

    # Construct the call string
    body_lines.append(f"        response = self._{http_verb}({', '.join(request_args)})")

    # Handle response (delegated to base class, just return)
    body_lines.append("        # APIApplication's _get/_post/etc. methods handle exceptions")
    body_lines.append("        # and return the httpx.Response object.")
    body_lines.append("        return response")

    # Combine all parts into the final method code string
    full_method_code = signature + '\n' + docstring + '\n' + '\n'.join(body_lines)

    # *** MODIFIED RETURN STATEMENT ***
    # Return the function name, its code, AND the final parameter definitions
    return func_name, full_method_code, final_param_defs # Added final_param_defs her


def generate_tool_definition(func_name: str, operation: Dict[str, Any], final_param_defs: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
     """Generates the tool definition dictionary for the list_tools method."""
     if not func_name:
         return None

     tool_params = {"type": "object", "properties": {}, "required": []}

     # Use the final_param_defs which have unique arg_names
     for param_def in final_param_defs:
         # Use the unique Python argument name for the tool parameter key
         arg_name = param_def['arg_name']
         param_schema = param_def.get('schema', {})
         param_type = param_schema.get('type', 'string')
         tool_type = param_type
         if tool_type == "integer":
             tool_type = "number"
         elif tool_type not in ["string", "number", "boolean", "array", "object"]:
             tool_type = "string" # Fallback

         tool_params["properties"][arg_name] = {
             "description": param_def.get('description', ''),
             "type": tool_type,
         }
         if param_def.get('required', False):
             tool_params["required"].append(arg_name) # Use unique arg name

     # Add request body if it exists (using the unique arg name, e.g., "request_body")
     request_body_info = operation.get('requestBody')
     if request_body_info:
         body_arg_name = "request_body" # Assuming this is the chosen unique name
         # ... (logic to determine body description and type as before) ...
         tool_params["properties"][body_arg_name] = {
            # ... (description, type) ...
         }
         if request_body_info.get('required', False):
             tool_params["required"].append(body_arg_name)

     # ... (rest of tool definition generation: remove empty required, create final dict) ...
     if not tool_params["required"]:
         del tool_params["required"]

     tool_definition = {
        # ... (name, description) ...
        "parameters": tool_params
     }
     return tool_definition

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