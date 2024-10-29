#!/usr/bin/env python3
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging
import os
from datetime import datetime
import requests
import kopf
import ipaddress

@dataclass
class GroupSpec:
    """Data class to validate and hold group specifications"""
    name: str
    description: str = ""
    peers: Optional[List[str]] = None  # Made peers optional
    id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GroupSpec':
        """Create GroupSpec from dictionary, ensuring required fields exist"""
        logging.debug(f"Creating GroupSpec from data: {data}")
        
        # Validate name field
        name = data.get('name')
        if not name:
            raise ValueError("name is required")

        # Make peers optional
        peers = data.get('peers', None)
        if peers is not None and not isinstance(peers, list):
            raise ValueError("if peers is provided, it must be a list")

        return cls(
            name=name,
            peers=peers,
            description=data.get('description', ''),
            id=data.get('id')
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert GroupSpec to dictionary for API requests"""
        result = {
            "name": self.name,
            "description": self.description,
        }
        
        # Only include peers if it's provided
        if self.peers is not None:
            result["peers"] = self.peers
            
        if self.id:
            result["id"] = self.id
            
        return result

@dataclass
class RouteSpec:
    """Data class to validate and hold route specifications"""
    network: str
    peer: str
    groups: List[str]
    network_id: str
    description: str = ""
    enabled: bool = True
    masquerade: bool = False
    metric: int = 9999
    id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RouteSpec':
        """Create RouteSpec from dictionary, ensuring required fields exist"""
        logging.debug(f"Creating RouteSpec from data: {data}")
        
        # Validate peerId field exists and convert to peer
        peer = data.get('peerId') or data.get('peer')
        if not peer:
            raise ValueError("peerId is required")

        # Validate network field
        network = data.get('network')
        if not network:
            raise ValueError("network is required")
        
        try:
            ipaddress.ip_network(network)
        except ValueError as e:
            raise ValueError(f"Invalid network format: {network}. Error: {str(e)}")

        groups = data.get('groups')
        if not groups or not isinstance(groups, list):
            raise ValueError("groups is required and must be a list")

        network_id = data.get('network_id')
        if not network_id:
            raise ValueError("network_id is required")

        metric = data.get('metric', 9999)
        if not isinstance(metric, (int, float)) or metric < 0:
            raise ValueError(f"Invalid metric value: {metric}. Must be a positive number.")

        return cls(
            network=network,
            peer=peer,
            groups=groups,
            network_id=network_id,
            description=data.get('description', ''),
            enabled=data.get('enabled', True),
            masquerade=data.get('masquerade', False),
            metric=metric,
            id=data.get('id')
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert RouteSpec to dictionary for API requests"""
        result = {
            "description": self.description,
            "network": self.network,
            "peer": self.peer,
            "groups": self.groups,
            "network_id": self.network_id,
            "enabled": self.enabled,
            "masquerade": self.masquerade,
            "metric": self.metric,
        }
        
        if self.id:
            result["id"] = self.id
            
        return result

class NetbirdClient:
    """Client for interacting with Netbird API"""
    def __init__(self, api_key: str):
        self.netbird_url = os.environ.get('NETBIRD_URL')
        if not self.netbird_url:
            raise ValueError("NETBIRD_URL environment variable is required")
            
        self.base_url = self.netbird_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def _make_request(self, method: str, endpoint: str, data: Optional[dict] = None) -> dict:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            logging.debug(f"Making {method} request to {url}")
            logging.debug(f"Headers (partially redacted): {{'Authorization': 'Bearer ...{self.api_key[-8:]}'}}")
            if data:
                logging.debug(f"Request payload: {data}")
            
            response = requests.request(method, url, headers=self.headers, json=data)
            
            logging.debug(f"Response status: {response.status_code}")
            if response.content:
                try:
                    logging.debug(f"Response body: {response.json()}")
                except ValueError:
                    logging.debug(f"Response body (raw): {response.text}")
            
            if response.status_code == 422:
                error_detail = "No error details available"
                try:
                    error_detail = response.json()
                except ValueError:
                    error_detail = response.text
                logging.error(f"422 Validation Error. Request payload: {data}")
                logging.error(f"Response details: {error_detail}")
                raise kopf.PermanentError(f"API validation failed: {error_detail}")
            
            response.raise_for_status()
            return response.json() if response.content else {}
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logging.error(f"Response status code: {e.response.status_code}")
                logging.error(f"Response body: {e.response.text}")
            raise

    def create_route(self, route_spec: RouteSpec) -> Dict[str, Any]:
        """Create a new route"""
        return self._make_request("POST", "/routes", route_spec.to_dict())

    def update_route(self, route_id: str, route_spec: RouteSpec) -> Dict[str, Any]:
        """Update an existing route"""
        existing_route = self.get_route(route_id)
        logging.debug(f"Existing route: {existing_route}")
        route_spec.id = existing_route['id']
        return self._make_request("PUT", f"/routes/{route_id}", route_spec.to_dict())

    def delete_route(self, route_id: str) -> None:
        """Delete a route"""
        self._make_request("DELETE", f"/routes/{route_id}")

    def get_route(self, route_id: str) -> Dict[str, Any]:
        """Get route details"""
        return self._make_request("GET", f"/routes/{route_id}")

    # Group methods
    def create_group(self, group_spec: GroupSpec) -> Dict[str, Any]:
        """Create a new group"""
        return self._make_request("POST", "/groups", group_spec.to_dict())

    # def update_group(self, group_id: str, group_spec: GroupSpec) -> Dict[str, Any]:
    #     """Update an existing group"""
    #     existing_group = self.get_group(group_id)
    #     logging.debug(f"Existing group: {existing_group}")
    #     group_spec.id = existing_group['id']
    #     return self._make_request("PUT", f"/groups/{group_id}", group_spec.to_dict())

    def delete_group(self, group_id: str) -> None:
        """Delete a group"""
        self._make_request("DELETE", f"/groups/{group_id}")

    # def get_group(self, group_id: str) -> Dict[str, Any]:
    #     """Get group details"""
    #     return self._make_request("GET", f"/groups/{group_id}")

    # def list_groups(self) -> List[Dict[str, Any]]:
    #     """List all groups"""
    #     return self._make_request("GET", "/groups")

def create_status_condition(status: str, reason: str, message: str, resource_id: Optional[str] = None) -> Dict[str, Any]:
    """Create a standardized status condition"""
    condition = {
        'type': 'Ready',
        'status': status,
        'lastTransitionTime': datetime.utcnow().isoformat(),
        'reason': reason,
        'message': message
    }
    
    result = {
        'lastSync': datetime.utcnow().isoformat(),
        'conditions': [condition],
        'status': status,  # Add status field for printer column
        'reason': reason   # Add reason field for printer column
    }
    
    if resource_id:
        result['resourceID'] = resource_id
    
    return result

@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    """Configure the operator settings"""
    settings.watching.server_timeout = 270
    settings.posting.level = logging.DEBUG
    settings.watching.cluster_scope = True
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logging.getLogger("urllib3").setLevel(logging.INFO)

@kopf.on.create('gitops.netbird.io', 'v1alpha1', 'networkroutes')
def create_fn(spec: Dict[str, Any], meta: Dict[str, Any], logger: logging.Logger, **_) -> Dict[str, Any]:
    """Handle creation of new Netbird routes"""
    logger.info("Starting route creation")
    logger.debug(f"Received spec: {spec}")
    
    api_key = os.environ.get('NETBIRD_API_KEY')
    if not api_key:
        status = create_status_condition(
            status='False',
            reason='ConfigError',
            message="NETBIRD_API_KEY environment variable is required"
        )
        raise kopf.PermanentError("NETBIRD_API_KEY environment variable is required", status=status)

    client = NetbirdClient(api_key)
    
    try:
        route_spec = RouteSpec.from_dict(spec)
        logger.info(f"Creating route for network {route_spec.network}")
        logger.debug(f"Prepared route specification: {route_spec.to_dict()}")
        
        route = client.create_route(route_spec)
        
        return create_status_condition(
            status='True',
            reason='RouteCreated',
            message=f"Route {route['id']} created successfully",
            resource_id=route['id']
        )
    except ValueError as e:
        status = create_status_condition(
            status='False',
            reason='ValidationError',
            message=str(e)
        )
        raise kopf.PermanentError(str(e), status=status)
    except Exception as e:
        status = create_status_condition(
            status='False',
            reason='Error',
            message=str(e)
        )
        raise kopf.TemporaryError(str(e), delay=60, status=status)


@kopf.on.update('gitops.netbird.io', 'v1alpha1', 'networkroutes')
def update_fn(spec: Dict[str, Any], status: Dict[str, Any], old: Dict[str, Any], new: Dict[str, Any], 
              logger: logging.Logger, **_) -> Dict[str, Any]:
    """Handle updates to existing Netbird routes"""
    logger.info("Starting route update")
    logger.debug(f"Received spec: {spec}")
    logger.debug(f"Current status: {status}")
    logger.debug(f"Old spec: {old.get('spec', {})}")
    logger.debug(f"New spec: {new.get('spec', {})}")

    if old.get('spec') == new.get('spec'):
        logger.info("No changes detected in spec, skipping update")
        return status

    api_key = os.environ.get('NETBIRD_API_KEY')
    if not api_key:
        status = create_status_condition(
            status='False',
            reason='ConfigError',
            message="NETBIRD_API_KEY environment variable is required"
        )
        raise kopf.PermanentError("NETBIRD_API_KEY environment variable is required", status=status)

    client = NetbirdClient(api_key)
    
    try:
        # Get route ID from create_fn status or update_fn status
        route_id = None
        if 'create_fn' in status and 'resourceID' in status['create_fn']:
            route_id = status['create_fn']['resourceID']
        elif 'update_fn' in status and 'resourceID' in status['update_fn']:
            route_id = status['update_fn']['resourceID']
        
        if not route_id:
            status = create_status_condition(
                status='False',
                reason='MissingResourceID',
                message="No route ID found in status"
            )
            raise kopf.PermanentError("No route ID found in status", status=status)

        route_spec = RouteSpec.from_dict(spec)
        logger.info(f"Updating route {route_id} for network {route_spec.network}")
        logger.debug(f"Prepared route specification: {route_spec.to_dict()}")
        
        route = client.update_route(route_id, route_spec)
        
        return create_status_condition(
            status='True',
            reason='RouteUpdated',
            message=f"Route {route['id']} updated successfully",
            resource_id=route['id']  # Changed from route_id to resource_id
        )
    except ValueError as e:
        status = create_status_condition(
            status='False',
            reason='ValidationError',
            message=str(e)
        )
        raise kopf.PermanentError(str(e), status=status)
    except Exception as e:
        status = create_status_condition(
            status='False',
            reason='Error',
            message=str(e)
        )
        raise kopf.TemporaryError(str(e), delay=60, status=status)

@kopf.on.delete('gitops.netbird.io', 'v1alpha1', 'networkroutes')
def delete_fn(spec: Dict[str, Any], status: Dict[str, Any], logger: logging.Logger, **_):
    """Handle deletion of Netbird routes"""
    logger.info("Starting route deletion")
    logger.debug(f"Current status: {status}")
    
    api_key = os.environ.get('NETBIRD_API_KEY')
    if not api_key:
        raise kopf.PermanentError("NETBIRD_API_KEY environment variable is required")

    client = NetbirdClient(api_key)
    
    try:
        # Get route ID from create_fn status or update_fn status
        route_id = None
        if 'create_fn' in status and 'resourceID' in status['create_fn']:
            route_id = status['create_fn']['resourceID']
        elif 'update_fn' in status and 'resourceID' in status['update_fn']:
            route_id = status['update_fn']['resourceID']

        if not route_id:
            logger.warning("No route ID found in status, skipping deletion")
            return

        logger.info(f"Deleting route {route_id}")
        client.delete_route(route_id)
        logger.info(f"Route {route_id} deleted successfully")
    except Exception as e:
        error_msg = f"Failed to delete route: {str(e)}"
        logger.error(error_msg)
        raise kopf.PermanentError(error_msg)

# Group Handlers
@kopf.on.create('gitops.netbird.io', 'v1alpha1', 'groups')
def create_group_fn(spec: Dict[str, Any], meta: Dict[str, Any], logger: logging.Logger, **_) -> Dict[str, Any]:
    """Handle creation of new Netbird groups"""
    logger.info(f"Starting group creation for {meta['name']}")
    
    api_key = os.environ.get('NETBIRD_API_KEY')
    if not api_key:
        raise kopf.PermanentError("NETBIRD_API_KEY environment variable is required")

    client = NetbirdClient(api_key)
    
    try:
        group_spec = GroupSpec.from_dict(spec)
        logger.info(f"Creating group {group_spec.name}")
        logger.debug(f"Prepared group specification: {group_spec.to_dict()}")
        
        group = client.create_group(group_spec)
        
        return create_status_condition(
            status='True',
            reason='GroupCreated',
            message=f"Group {group['id']} created successfully",
            resource_id=group['id']
        )
    except ValueError as e:
        logger.error(f"Invalid group specification: {str(e)}")
        raise kopf.PermanentError(f"Invalid group specification: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to create group: {str(e)}")
        raise kopf.TemporaryError(f"Failed to create group: {str(e)}", delay=60)

@kopf.on.delete('gitops.netbird.io', 'v1alpha1', 'groups')
def delete_group_fn(spec: Dict[str, Any], status: Dict[str, Any], meta: Dict[str, Any], 
                   logger: logging.Logger, **_):
    """Handle deletion of Netbird groups"""
    logger.info(f"Starting group deletion for {meta['name']}")
    
    api_key = os.environ.get('NETBIRD_API_KEY')
    if not api_key:
        raise kopf.PermanentError("NETBIRD_API_KEY environment variable is required")

    client = NetbirdClient(api_key)
    
    try:
        group_id = None
        for handler in ['create_group_fn', 'update_group_fn']:
            if handler in status and 'resourceID' in status[handler]:
                group_id = status[handler]['resourceID']
                break

        if not group_id:
            logger.warning(f"No group ID found in status for {meta['name']}, skipping deletion")
            return

        logger.info(f"Deleting group {group_id}")
        try:
            client.delete_group(group_id)
            logger.info(f"Group {group_id} deleted successfully")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.info(f"Group {group_id} already deleted")
            else:
                raise
    except Exception as e:
        error_msg = f"Failed to delete group: {str(e)}"
        logger.error(error_msg)
        raise kopf.PermanentError(error_msg)
