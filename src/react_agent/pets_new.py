from agentr.applications import APIApplication
from agentr.integrations import Integration
from typing import Any, Dict, List

class SwaggerPetstoreOpenapi30App(APIApplication):
    def __init__(self, integration: Integration = None, **kwargs) -> None:
        """
        Initialize a new Swagger Pet Store OpenAPI 3.0 application instance.
        
        Args:
            integration: Optional integration layer for the application.
            **kwargs: Additional keyword arguments passed to the parent class constructor.
        
        Returns:
            None
        """
        super().__init__(name='swaggerpetstoreopenapi30app', integration=integration, **kwargs)
        self.base_url = "/api/v3"

    def update_pet(self, request_body) -> Dict[str, Any]:
        """
        Updates an existing pet in the pet store with new information from the provided request body.
        
        Args:
            request_body: Dictionary containing the updated pet information. Cannot be None.
        
        Returns:
            Dictionary containing the response data from the pet update operation.
        """
        if request_body is None:
            raise ValueError("Missing required request body")
        path_params = {}
        url = f"{self.base_url}/pet".format_map(path_params)
        query_params = {}
        json_body = request_body if request_body is not None else None
        response = self._put(url, data=json_body, params=query_params)
        response.raise_for_status()
        return response.json()

    def add_pet(self, request_body) -> Dict[str, Any]:
        """
        Adds a new pet to the store by making a POST request to the pet endpoint.
        
        Args:
            request_body: JSON-serializable object containing pet information to be added to the store. Cannot be None.
        
        Returns:
            Dictionary containing the response data from the server after adding the pet.
        """
        if request_body is None:
            raise ValueError("Missing required request body")
        path_params = {}
        url = f"{self.base_url}/pet".format_map(path_params)
        query_params = {}
        json_body = request_body if request_body is not None else None
        response = self._post(url, data=json_body, params=query_params)
        response.raise_for_status()
        return response.json()

    def find_pets_by_status(self, status=None) -> List[Any]:
        """
        Finds pets by their status in the pet store API.
        
        Args:
            status: The status of pets to find. If None, no status filter is applied.
        
        Returns:
            A list of pet objects that match the specified status.
        """
        path_params = {}
        url = f"{self.base_url}/pet/findByStatus".format_map(path_params)
        query_params = {k: v for k, v in [('status', status)] if v is not None}
        response = self._get(url, params=query_params)
        response.raise_for_status()
        return response.json()

    def find_pets_by_tags(self, tags=None) -> List[Any]:
        """
        Find pets by tags in the pet store database.
        
        Args:
            tags: A list of tag names to filter pets by. Only pets with matching tags will be returned.
        
        Returns:
            A list of Pet objects that match the specified tags.
        """
        path_params = {}
        url = f"{self.base_url}/pet/findByTags".format_map(path_params)
        query_params = {k: v for k, v in [('tags', tags)] if v is not None}
        response = self._get(url, params=query_params)
        response.raise_for_status()
        return response.json()

    def get_pet_by_id(self, petId) -> Dict[str, Any]:
        """
        Retrieves a pet from the pet store API by its ID.
        
        Args:
            petId: The unique identifier of the pet to retrieve. Must not be None.
        
        Returns:
            A dictionary containing the pet information retrieved from the API.
        """
        if petId is None:
            raise ValueError("Missing required parameter 'petId'")
        path_params = {'petId': petId}
        url = f"{self.base_url}/pet/{petId}".format_map(path_params)
        query_params = {}
        response = self._get(url, params=query_params)
        response.raise_for_status()
        return response.json()

    def update_pet_with_form(self, petId, name=None, status=None) -> Dict[str, Any]:
        """
        Updates an existing pet information with form data using a POST request.
        
        Args:
            petId: The ID of the pet to update. Required parameter.
            name: Optional new name to update the pet with.
            status: Optional new status of the pet (e.g., 'available', 'pending', 'sold').
        
        Returns:
            A dictionary containing the API response data for the updated pet.
        """
        if petId is None:
            raise ValueError("Missing required parameter 'petId'")
        path_params = {'petId': petId}
        url = f"{self.base_url}/pet/{petId}".format_map(path_params)
        query_params = {k: v for k, v in [('name', name), ('status', status)] if v is not None}
        response = self._post(url, data={}, params=query_params)
        response.raise_for_status()
        return response.json()

    def delete_pet(self, petId, api_key=None) -> Any:
        """
        Deletes a pet from the pet store by its ID.
        
        Args:
            petId: The ID of the pet to delete (required)
            api_key: API authentication key (optional)
        
        Returns:
            The API response converted to a JSON object
        """
        if petId is None:
            raise ValueError("Missing required parameter 'petId'")
        path_params = {'petId': petId}
        url = f"{self.base_url}/pet/{petId}".format_map(path_params)
        query_params = {}
        response = self._delete(url, params=query_params)
        response.raise_for_status()
        return response.json()

    def upload_file(self, petId, additionalMetadata=None, request_body=None) -> Dict[str, Any]:
        """
        Uploads an image file for a pet to the server.
        
        Args:
            petId: Required. The ID of the pet to which the image will be uploaded.
            additionalMetadata: Optional. Additional metadata about the uploaded image.
            request_body: Optional. The image file data to be uploaded.
        
        Returns:
            Dictionary containing the API response with information about the uploaded image.
        """
        if petId is None:
            raise ValueError("Missing required parameter 'petId'")
        path_params = {'petId': petId}
        url = f"{self.base_url}/pet/{petId}/uploadImage".format_map(path_params)
        query_params = {k: v for k, v in [('additionalMetadata', additionalMetadata)] if v is not None}
        json_body = request_body if request_body is not None else None
        response = self._post(url, data=json_body, params=query_params)
        response.raise_for_status()
        return response.json()

    def get_inventory(self, ) -> Dict[str, Any]:
        """
        Retrieves the current inventory from the store API.
        
        Args:
            self: Instance of the class containing API connection details.
        
        Returns:
            Dictionary mapping product SKUs to their quantities and other inventory information.
        """
        path_params = {}
        url = f"{self.base_url}/store/inventory".format_map(path_params)
        query_params = {}
        response = self._get(url, params=query_params)
        response.raise_for_status()
        return response.json()

    def place_order(self, request_body=None) -> Dict[str, Any]:
        """
        Places an order in the store by sending a POST request to the store order endpoint.
        
        Args:
            request_body: JSON-serializable dictionary containing the order details. If None, an empty order will be created.
        
        Returns:
            Dictionary containing the response data from the created order.
        """
        path_params = {}
        url = f"{self.base_url}/store/order".format_map(path_params)
        query_params = {}
        json_body = request_body if request_body is not None else None
        response = self._post(url, data=json_body, params=query_params)
        response.raise_for_status()
        return response.json()

    def get_order_by_id(self, orderId) -> Dict[str, Any]:
        """
        Retrieves an order from the store by its ID.
        
        Args:
            orderId: The unique identifier of the order to retrieve. Must not be None.
            self: Instance of the class containing base URL and request methods.
        
        Returns:
            A dictionary containing the order details.
        """
        if orderId is None:
            raise ValueError("Missing required parameter 'orderId'")
        path_params = {'orderId': orderId}
        url = f"{self.base_url}/store/order/{orderId}".format_map(path_params)
        query_params = {}
        response = self._get(url, params=query_params)
        response.raise_for_status()
        return response.json()

    def delete_order(self, orderId) -> Any:
        """
        Deletes an order from the store by its ID.
        
        Args:
            orderId: The ID of the order to be deleted. Cannot be None.
        
        Returns:
            The JSON response from the server after deleting the order.
        """
        if orderId is None:
            raise ValueError("Missing required parameter 'orderId'")
        path_params = {'orderId': orderId}
        url = f"{self.base_url}/store/order/{orderId}".format_map(path_params)
        query_params = {}
        response = self._delete(url, params=query_params)
        response.raise_for_status()
        return response.json()

    def create_user(self, request_body=None) -> Dict[str, Any]:
        """
        Creates a new user by sending a POST request to the API endpoint.
        
        Args:
            request_body: Optional dictionary containing user data to be sent in the request body. If None, an empty body will be sent.
        
        Returns:
            The JSON response from the API as a dictionary containing user information.
        """
        path_params = {}
        url = f"{self.base_url}/user".format_map(path_params)
        query_params = {}
        json_body = request_body if request_body is not None else None
        response = self._post(url, data=json_body, params=query_params)
        response.raise_for_status()
        return response.json()

    def create_users_with_list_input(self, request_body=None) -> Dict[str, Any]:
        """
        Creates multiple users with a list input through a POST request to the API endpoint.
        
        Args:
            self: Instance of the class that contains this method.
            request_body: Optional JSON-serializable object containing the list of users to be created. If None, no data will be sent in the request body.
        
        Returns:
            Dictionary containing the API response data converted from JSON format.
        """
        path_params = {}
        url = f"{self.base_url}/user/createWithList".format_map(path_params)
        query_params = {}
        json_body = request_body if request_body is not None else None
        response = self._post(url, data=json_body, params=query_params)
        response.raise_for_status()
        return response.json()

    def login_user(self, username=None, password=None) -> Any:
        """
        Logs in a user with the provided credentials.
        
        Args:
            username: The username for authentication. If None, no username is sent in the request.
            password: The password for authentication. If None, no password is sent in the request.
        
        Returns:
            The JSON response from the server containing user login information.
        """
        path_params = {}
        url = f"{self.base_url}/user/login".format_map(path_params)
        query_params = {k: v for k, v in [('username', username), ('password', password)] if v is not None}
        response = self._get(url, params=query_params)
        response.raise_for_status()
        return response.json()

    def logout_user(self, ) -> Any:
        """
        Logs out the current user from the system.
        
        Args:
            self: Reference to the class instance that provides access to API endpoints.
        
        Returns:
            JSON response containing logout confirmation data.
        """
        path_params = {}
        url = f"{self.base_url}/user/logout".format_map(path_params)
        query_params = {}
        response = self._get(url, params=query_params)
        response.raise_for_status()
        return response.json()

    def get_user_by_name(self, username) -> Dict[str, Any]:
        """
        Retrieves user information by username from the API.
        
        Args:
            username: The unique username of the user to retrieve. Cannot be None.
            self: Instance of the class containing API client configuration.
        
        Returns:
            A dictionary containing the user's information retrieved from the API.
        """
        if username is None:
            raise ValueError("Missing required parameter 'username'")
        path_params = {'username': username}
        url = f"{self.base_url}/user/{username}".format_map(path_params)
        query_params = {}
        response = self._get(url, params=query_params)
        response.raise_for_status()
        return response.json()

    def update_user(self, username, request_body=None) -> Any:
        """
        Updates a user's information in the system.
        
        Args:
            username: The username of the user to update. Cannot be None.
            request_body: JSON-serializable dictionary containing the updated user information. If None, no data will be sent in the request body.
        
        Returns:
            The updated user data as a dictionary parsed from the JSON response.
        """
        if username is None:
            raise ValueError("Missing required parameter 'username'")
        path_params = {'username': username}
        url = f"{self.base_url}/user/{username}".format_map(path_params)
        query_params = {}
        json_body = request_body if request_body is not None else None
        response = self._put(url, data=json_body, params=query_params)
        response.raise_for_status()
        return response.json()

    def delete_user(self, username) -> Any:
        """
        Deletes a user by username from the system.
        
        Args:
            username: The username of the user to delete. Cannot be None.
        
        Returns:
            The JSON response from the server after the deletion operation.
        """
        if username is None:
            raise ValueError("Missing required parameter 'username'")
        path_params = {'username': username}
        url = f"{self.base_url}/user/{username}".format_map(path_params)
        query_params = {}
        response = self._delete(url, params=query_params)
        response.raise_for_status()
        return response.json()

    def list_tools(self):
        """
        Returns a list of all available API tools for pet store management.
        
        Args:
            self: Reference to the current instance of the class.
        
        Returns:
            A list of method references for pet, store, and user management operations including pet CRUD operations, inventory management, order processing, and user account functions.
        """
        return [
            self.update_pet,
            self.add_pet,
            self.find_pets_by_status,
            self.find_pets_by_tags,
            self.get_pet_by_id,
            self.update_pet_with_form,
            self.delete_pet,
            self.upload_file,
            self.get_inventory,
            self.place_order,
            self.get_order_by_id,
            self.delete_order,
            self.create_user,
            self.create_users_with_list_input,
            self.login_user,
            self.logout_user,
            self.get_user_by_name,
            self.update_user,
            self.delete_user
        ]

