import json
import re 
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional 
import httpx 

ParameterObject = Dict[str, Any]


def to_snake_case(name: str) -> str:
    """Converts a PascalCase or camelCase string to snake_case."""
    if not name:
        return ""
    name = re.sub(r'(?<!^)(?=[A-Z])', '_', name)
    return name.lower()

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

    api_base_url = ""
    servers = schema.get('servers', [])
    if servers and isinstance(servers, list) and 'url' in servers[0]:
        api_base_url = servers[0]['url'].rstrip('/')
    else:
        api_base_url = "{YOUR_API_BASE_URL}" # Placeholder
        print("# Warning: No 'servers' found in OpenAPI schema. Set base URL manually.")

    info = schema.get('info', {})
    api_title = info.get('title', 'Generated API Client')
    api_version = info.get('version', '')
    api_description = info.get('description', '')

    base_name = "".join(part.capitalize() for part in api_title.replace("-", " ").replace("_", " ").split())
    sanitized_name = ''.join(c for c in base_name if c.isalnum() or c == '_')

    if not sanitized_name:
        sanitized_name = "GeneratedApiClient" # Use default if sanitization removed everything

    if sanitized_name[0].isdigit():
        class_name = "Api" + sanitized_name
    elif sanitized_name.startswith('_'):
         class_name = "Api" + sanitized_name
    else:
        class_name = sanitized_name
        
    for path, path_info in schema.get('paths', {}).items():
        path_level_params: List[ParameterObject] = path_info.get('parameters', [])

        for method in path_info:
            if method.lower() in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']:
                operation: Dict[str, Any] = path_info[method]

                operation_params: List[ParameterObject] = operation.get('parameters', [])

                combined_params_map: Dict[tuple[Optional[str], Optional[str]], ParameterObject] = {
                    (p.get('name'), p.get('in')): p for p in path_level_params if p.get('name') and p.get('in')
                }
                combined_params_map.update({
                    (p.get('name'), p.get('in')): p for p in operation_params if p.get('name') and p.get('in')
                })
                combined_parameters: List[ParameterObject] = list(combined_params_map.values())

                func_name, method_code, final_defs = generate_method_code(path, method, operation, combined_parameters, api_base_url)
                            
                if func_name and final_defs is not None:
                    tool_definition = generate_tool_definition(func_name, operation, final_defs) 

                    if method_code:
                        methods.append(method_code)
                    if tool_definition:
                         tools.append(tool_definition)
                else:
                    print(f"Warning: Skipping method/tool generation for {method.upper()} {path} due to errors in generate_method_code.")

    class_header = (
        "from typing import Optional, Dict, Any, List\n"
        "from agentr.application import APIApplication\n"
        "from agentr.integration import Integration # For type hinting\n"
        "from agentr.exceptions import NotAuthorizedError # For context\n"
        "import httpx # For response type hint\n\n"
    )

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

    tools_list_str = ",\n".join([f"        {json.dumps(tool, indent=16)}" for tool in tools]) 
    list_tools_method = (
        "    def list_tools(self) -> List[Dict[str, Any]]:\n"
        "        \"\"\"Lists the tools available in this application, derived from the OpenAPI schema.\"\"\"\n"
        f"        tools = [\n{tools_list_str}\n        ]\n" 
        "        return tools\n"
    )

    class_code = (
        class_header +
        class_def +
        '\n\n'.join(methods) + "\n\n" + 
        list_tools_method
    )
    return class_code


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
        tuple[Optional[str], Optional[str], Optional[List[Dict[str, Any]]]]: (function_name, python_code_for_the_method, final_parameter_definitions) or (None, None, None) if invalid
    """
    if 'operationId' in operation:
        op_id = operation['operationId']
        sanitized_op_id = op_id.replace('.', '_').replace('-', '_')
        func_name = to_snake_case(sanitized_op_id)
    else:
        path_parts = path.strip('/').split('/')
        name_parts = [method.lower()]
        for part in path_parts:
            if part.startswith('{') and part.endswith('}'):
                clean_part = part[1:-1].replace('-', '_')
                name_parts.append('by_' + clean_part)
            elif part:
                clean_part = part.replace('-', '_')
                name_parts.append(clean_part)
        func_name = '_'.join(name_parts).lower()

    request_body_info = operation.get('requestBody')
    has_body = bool(request_body_info)
    body_required = has_body and request_body_info.get('required', False)
    body_description = "The request body."
    body_content = request_body_info.get('content', {}) if has_body else {}
    json_schema = body_content.get('application/json', {}).get('schema', {})
    body_arg_type = "Dict[str, Any]" 

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


         if schema_type == 'array':
             items_schema = json_schema.get('items', {})
             items_type = items_schema.get('type', 'Any')
             py_item_type = openapi_type_to_python(items_type)
             if py_item_type in ["Dict[str, Any]", "Any"] and items_schema:
                 py_item_type = "Dict[str, Any]" # Assume array of objects commonly
             elif py_item_type == "List": # Array of arrays? Use Any
                  py_item_type = "Any"
             body_arg_type = f"List[{py_item_type}]"

         elif schema_type == 'object':
             body_arg_type = "Dict[str, Any]"
         elif schema_type: # string, number, integer, boolean
              body_arg_type = openapi_type_to_python(schema_type)

    args = []
    assigned_arg_names = set()
    final_param_defs = []

    for param in parameters:
        param_name = param.get('name')
        param_in = param.get('in')
        if not param_name or not param_in:
             print(f"Warning: Skipping parameter without name or location ('in') in operation '{func_name}': {param}")
             continue # Skip invalid parameter definitions

        initial_arg_name = param_name.replace('-', '_')

        unique_arg_name = initial_arg_name
        if initial_arg_name in assigned_arg_names:
            # Collision detected! Append the location to disambiguate
            unique_arg_name = f"{initial_arg_name}_{param_in}"
            # Add a counter just in case even this collides (very unlikely)
            counter = 2
            while unique_arg_name in assigned_arg_names:
                 unique_arg_name = f"{initial_arg_name}_{param_in}{counter}"
                 counter += 1

        is_required = param.get('required', False)
        param_schema = param.get('schema', {})
        param_type = param_schema.get('type', 'Any')
        py_type = openapi_type_to_python(param_type)

        param_def = {
            'name': param_name,            
            'arg_name': unique_arg_name,  
            'in': param_in,
            'required': is_required,
            'description': param.get('description', ''),
            'schema': param_schema,
            'py_type': py_type            # Store python type for reuse
        }
        final_param_defs.append(param_def)
        assigned_arg_names.add(unique_arg_name) # Mark this unique name as used

    for p_def in final_param_defs:
        arg_name = p_def['arg_name']
        py_type = p_def['py_type']
        if p_def['required']:
            args.append(f"{arg_name}: {py_type}")
        else:
            args.append(f"{arg_name}: Optional[{py_type}] = None")

    body_arg_name = "request_body" # Consistent name for body arg
    if has_body:
        while body_arg_name in assigned_arg_names:
             body_arg_name = f"_{body_arg_name}" # Prepend underscore

        if body_required:
            args.append(f"{body_arg_name}: {body_arg_type}")
        else:
            args.append(f"{body_arg_name}: Optional[{body_arg_type}] = None")

    signature = f"    def {func_name}(self, {', '.join(args)}) -> httpx.Response:"

    docstring_lines = [
        f"        \"\"\"{operation.get('summary', func_name)}", # Use summary or func_name
        "" 
    ]
    if operation.get('description'):
        desc = operation['description'].strip()
        docstring_lines.extend(f"        {line}" for line in desc.split('\n'))
        docstring_lines.append("") 

    docstring_lines.append("        Args:")
    for p_def in final_param_defs:
        docstring_lines.append(f"            {p_def['arg_name']}: {p_def.get('description', 'From OpenAPI spec.')}")
    if has_body:
        docstring_lines.append(f"            {body_arg_name}: {body_description}")

    docstring_lines.append("")
    docstring_lines.append("        Returns:")
    docstring_lines.append("            httpx.Response: The raw response from the API call.")
    docstring_lines.append("        \"\"\"")
    docstring = '\n'.join(docstring_lines)

    body_lines = []

    for p_def in final_param_defs:
        if p_def['required']:
            body_lines.append(f"        if {p_def['arg_name']} is None:")
            body_lines.append(f"            raise ValueError(\"Missing required {p_def['in']} parameter: {p_def['arg_name']} (original: {p_def['name']})\")")

    if has_body and body_required:
         body_lines.append(f"        if {body_arg_name} is None:")
         body_lines.append(f"            raise ValueError(\"Missing required request body\")")

    path_params_dict = ', '.join([f"'{p['name']}': {p['arg_name']}" for p in final_param_defs if p['in'] == 'path'])
    body_lines.append(f"        path_params = {{{path_params_dict}}}")

    body_lines.append(f"        url = f\"{{self.api_base_url}}{path}\".format_map(path_params)")

    query_params_items = ', '.join([f"('{p['name']}', {p['arg_name']})" for p in final_param_defs if p['in'] == 'query'])
    body_lines.append(
        f"        query_params = {{k: v for k, v in [{query_params_items}] if v is not None}}"
    )

    header_params_items = ', '.join([f"('{p['name']}', {p['arg_name']})" for p in final_param_defs if p['in'] == 'header'])
    body_lines.append(
        f"        header_params = {{k: v for k, v in [{header_params_items}] if v is not None}}"
    )
    
    http_verb = method.lower()
    request_args = ["url", "params=query_params", "headers=header_params"]

    if has_body:
        body_lines.append(f"        json_body = {body_arg_name} if {body_arg_name} is not None else None")
        request_args.append("json=json_body")
    elif http_verb in ['post', 'put', 'patch'] and not has_body:
        pass 

    body_lines.append(f"        response = self._{http_verb}({', '.join(request_args)})")
    body_lines.append("        # APIApplication's _get/_post/etc. methods handle exceptions")
    body_lines.append("        # and return the httpx.Response object.")
    body_lines.append("        return response")

    full_method_code = signature + '\n' + docstring + '\n' + '\n'.join(body_lines)

    return func_name, full_method_code, final_param_defs 


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
         # Determine body description and type
         body_description = "The request body."
         body_type = "object" # Default type for body
         body_content = request_body_info.get('content', {})
         json_schema = body_content.get('application/json', {}).get('schema', {})
         if json_schema:
             schema_type = json_schema.get('type', 'object')
             if schema_type == 'array':
                 body_type = 'array'
             elif schema_type == 'object':
                 body_type = 'object'
             if '$ref' in json_schema:
                 ref_name = json_schema['$ref'].split('/')[-1]
                 body_description = f"The request body. (Schema: {ref_name})"
             elif json_schema.get('title'):
                 body_description = f"The request body. (Schema: {json_schema['title']})"
             elif schema_type: # Add type if title/ref missing
                 body_description = f"The request body. (Type: {schema_type})"

         tool_params["properties"][body_arg_name] = {
             "description": body_description,
             "type": body_type,
         }
         if request_body_info.get('required', False):
             tool_params["required"].append(body_arg_name)
             
     if not tool_params["required"]:
         del tool_params["required"]

     tool_description = operation.get('summary', '').strip()
     if not tool_description:
        tool_description = operation.get('description', func_name).strip()

     tool_definition = {
         "name": func_name,
         "description": tool_description,
         "parameters": tool_params      
     }
     
     return tool_definition

if __name__ == "__main__":
    schema_path = Path('openapi.json') 
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