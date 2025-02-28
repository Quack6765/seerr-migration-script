#!/usr/bin/env python3
# Python script to migrate Overseerr to Jellyseerr
# https://github.com/Quack6765/seerr-migration-script

import sys
import time
import argparse
import requests
import json
import logging
from typing import List, Dict, Any, Optional
from requests.exceptions import RequestException

# Setup logging
logging.basicConfig(
    level=logging.INFO,  # Default to INFO level
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add command-line arguments
def parse_args():
    parser = argparse.ArgumentParser()
    
    # Add source argument
    parser.add_argument('-s', '--source', help='The URL source from which to retrieve data (Overseerr)')

    # Add source API key argument
    parser.add_argument('-k', '--source_api_key', help='The API Key for the source (Overseerr)')

    # Add target argument
    parser.add_argument('-t', '--target', help='The URL target where to send data (Jellyseerr)')
    
    # Add target API key argument
    parser.add_argument('-a', '--target_api_key', help='The API Key for the target (Jellyseerr)')

    # Add TMDB API key argument (optional)
    parser.add_argument('-m', '--tmdb_api_key', help='The API Key for TMDB (optional)', required=False)
    
    # Add debug flag
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug logging')

    args = parser.parse_args()
    
    # Set logging level based on debug flag
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    return args

def main() -> int:
    """Main entry point for the migration script.
    
    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    try:
        args = parse_args()

        if not all([args.source, args.source_api_key, args.target, args.target_api_key]):
            logger.error("All arguments must be provided and cannot be empty.")
            return 1

        global SOURCE_URL
        global SOURCE_APIKEY
        global TARGET_URL
        global TARGET_APIKEY
        global TMDB_APIKEY

        SOURCE_URL = f"{args.source.rstrip('/')}/api/v1"
        SOURCE_APIKEY = args.source_api_key
        TARGET_URL = f"{args.target.rstrip('/')}/api/v1"
        TARGET_APIKEY = args.target_api_key
        TMDB_APIKEY = args.tmdb_api_key or ''
        
        logger.info("Starting migration process...")
        success = migration()
        
        if success:
            logger.info("Migration completed successfully!")
            return 0
        else:
            logger.warning("Migration completed with errors. Check the logs for details.")
            return 1
        
    except KeyboardInterrupt:
        logger.info("\nMigration interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}", exc_info=True)
        return 1

def fetch_data(url: str, api_key: str, endpoint: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Fetch data from API endpoint with error handling.
    
    Args:
        url: Base URL for the API
        api_key: API key for authentication
        endpoint: API endpoint to fetch from
        params: Query parameters
        
    Returns:
        List of results from the API
        
    Raises:
        RequestException: If the API request fails
    """
    # Initialize response variable before try block
    r = None
    try:
        r = requests.get(
            url=f"{url}{endpoint}",
            headers={"X-Api-Key": api_key},
            params=params,
            timeout=30
        )
        r.raise_for_status()
        return r.json()["results"]
    except RequestException as e:
        logger.error(f"Failed to fetch data from {endpoint}: {str(e)} - Response: {r.text if r and hasattr(r, 'text') else 'No response text'}")
        raise

def migration() -> bool:
    """Main migration function to transfer users and requests.
    
    Returns:
        bool: True if migration was successful, False if there were any errors
    """
    try:
        if not testConnections():
            logger.error("Connection test failed")
            return False

        # Get list of current users and requests
        global SOURCE_USERS, TARGET_USERS, SOURCE_REQUESTS, TARGET_REQUESTS
        
        logger.info("Fetching users and requests from both systems...")
        try:
            SOURCE_USERS = fetch_data(SOURCE_URL, SOURCE_APIKEY, "/user", {"take": 500})
            TARGET_USERS = fetch_data(TARGET_URL, TARGET_APIKEY, "/user", {"take": 500})
            SOURCE_REQUESTS = fetch_data(SOURCE_URL, SOURCE_APIKEY, "/request", {"take": 1000, "filter": "unavailable"})
            TARGET_REQUESTS = fetch_data(TARGET_URL, TARGET_APIKEY, "/request", {"take": 1000, "filter": "unavailable"})
        except Exception as e:
            logger.error(f"Failed to fetch initial data: {str(e)}")
            return False

        # Migrate users
        logger.info(f"Starting migration of {len(SOURCE_USERS)} users...")
        success_count = 0
        failure_count = 0
        
        for user in SOURCE_USERS:
            try:
                if migrateUser(user):
                    success_count += 1
                else:
                    failure_count += 1
            except Exception as e:
                logger.error(f"Unexpected error migrating user: {str(e)}")
                failure_count += 1
                continue  # Continue with next user
                
        total = len(SOURCE_USERS)
        logger.info(f"Migration completed. Success: {success_count}/{total} ({success_count/total*100:.1f}%), Failures: {failure_count}/{total} ({failure_count/total*100:.1f}%)")
        return failure_count == 0
            
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}", exc_info=True)
        return False

def testConnections() -> bool:
    """Test connections to both Overseerr and Jellyseerr servers.
    
    Returns:
        bool: True if both connections succeed, False otherwise
    """
    # Test Overseerr connection
    status = "Testing Overseerr connection ... "
    print(status, end="", flush=True)
    r = None
    try:
        r = requests.get(
            url=SOURCE_URL+"/settings/main",
            headers={"X-Api-Key": SOURCE_APIKEY},
            timeout=10
        )
        r.raise_for_status()
        print("OK")
    except requests.exceptions.RequestException as e:
        logger.error(f"Couldn't connect to Overseerr! {str(e)} - Response: {r.text if r and hasattr(r, 'text') else 'No response text'}")
        return False

    # Test Jellyseerr connection
    status = "Testing Jellyseerr connection ... "
    print(status, end="", flush=True)
    r = None
    try:
        r = requests.get(
            url=TARGET_URL+"/settings/main",
            headers={"X-Api-Key": TARGET_APIKEY},
            timeout=10
        )
        r.raise_for_status()
        print("OK")
    except requests.exceptions.RequestException as e:
        logger.error(f"Couldn't connect to Jellyseerr! {str(e)} - Response: {r.text if r and hasattr(r, 'text') else 'No response text'}")
        return False
        
    return True
        
def migrateUser(user: Dict[str, Any]) -> bool:
    """Migrate a single user from Overseerr to Jellyseerr.
    
    Args:
        user: User data dictionary from Overseerr
        
    Returns:
        bool: True if migration was successful, False otherwise
    """
    try:
        email = user.get("email")
        if not email:
            logger.error("User data missing email field")
            return False

        logger.info(f"Processing user: {email}")

        # Check if user already exists - use the new function to get detailed user info
        existing_user = fetch_user_by_email(email)
        
        if existing_user:
            userNewID = existing_user["id"]
            user_source = existing_user.get("userType", "unknown")
            display_name = existing_user.get("displayName", "unknown")
            
            logger.info(f"User '{email}' already exists in Jellyseerr with ID {userNewID}, source: {user_source}, display name: {display_name}")
            logger.debug(f"Existing user details: {json.dumps(existing_user)}")
            
            # Check if user has request permissions
            permissions = existing_user.get("permissions", 0)
            if (permissions & 1) != 1:
                logger.info(f"Adding request permission to existing user '{email}'")
                permissions |= 1  # Set bit 1 (request permission)
                
                # Update permissions
                r = requests.put(
                    url=f"{TARGET_URL}/user/{userNewID}",
                    headers={"X-Api-Key": TARGET_APIKEY},
                    json={"permissions": permissions},
                    timeout=30
                )
                r.raise_for_status()
                logger.info(f"Updated permissions for user '{email}' to {permissions}")
            else:
                logger.info(f"User '{email}' already has request permissions")
        else:
            # Before creating a new user, check if there's a Jellyfin user with the same email
            # This requires fetching all users and checking their details
            logger.info(f"No exact match found for user '{email}', checking for Jellyfin users with the same email")
            
            # Get all users
            all_users = fetch_data(TARGET_URL, TARGET_APIKEY, "/user", {"take": 500})
            
            # Check for any user with the same email, regardless of source
            jellyfin_user = None
            for u in all_users:
                if u.get("email") == email:
                    # Get detailed user info
                    user_detail = fetch_user_by_email(email)
                    if user_detail and user_detail.get("userType") == "jellyfin":
                        jellyfin_user = user_detail
                        break
            
            if jellyfin_user:
                userNewID = jellyfin_user["id"]
                logger.info(f"Found Jellyfin user with email '{email}', ID: {userNewID}. Using this user instead of creating a new one.")
                
                # Update permissions if needed
                permissions = jellyfin_user.get("permissions", 0)
                if (permissions & 1) != 1:
                    logger.info(f"Adding request permission to Jellyfin user '{email}'")
                    permissions |= 1  # Set bit 1 (request permission)
                    
                    # Update permissions
                    r = requests.put(
                        url=f"{TARGET_URL}/user/{userNewID}",
                        headers={"X-Api-Key": TARGET_APIKEY},
                        json={"permissions": permissions},
                        timeout=30
                    )
                    r.raise_for_status()
                    logger.info(f"Updated permissions for Jellyfin user '{email}' to {permissions}")
            else:
                # Create new user
                try:
                    newUsername = user.get("username") or user.get("plexUsername")
                    if not newUsername:
                        logger.error(f"User '{email}' missing both username and plexUsername")
                        return False
                        
                    payload = {
                        "email": email,
                        "username": newUsername,
                        "permissions": user.get("permissions", 0)  # Default to 0 permissions if not specified
                    }
                    
                    r = None
                    try:
                        r = requests.post(
                            url=f"{TARGET_URL}/user",
                            headers={"X-Api-Key": TARGET_APIKEY},
                            json=payload,
                            timeout=30
                        )
                        r.raise_for_status()
                        userNewID = r.json()["id"]
                        
                        # Update permissions - ensure user has request permissions (bit 1)
                        permissions = user.get("permissions", 0)
                        # Set bit 1 (request permission) if not already set
                        if (permissions & 1) != 1:
                            logger.info(f"Adding request permission to user '{email}'")
                            permissions |= 1  # Set bit 1 (request permission)
                        
                        r = requests.put(
                            url=f"{TARGET_URL}/user/{userNewID}",
                            headers={"X-Api-Key": TARGET_APIKEY},
                            json={"permissions": permissions},
                            timeout=30
                        )
                        r.raise_for_status()
                        logger.info(f"User '{email}' created in Jellyseerr with permissions: {permissions}")
                        
                    except RequestException as e:
                        logger.error(f"Failed to create/update user '{email}': {str(e)} - Response: {r.text if r and hasattr(r, 'text') else 'No response text'}")
                        return False
                        
                except Exception as e:
                    logger.error(f"Failed to prepare user data for '{email}': {str(e)}")
                    return False

        # Get source user ID
        userOldID = next(
            (u["id"] for u in SOURCE_USERS if u["email"] == email),
            None
        )
        if not userOldID:
            logger.error(f"Could not find source user ID for email: {email}")
            return False

        # Handle notifications and requests
        try:
            # Handle notifications and requests
            notifications_disabled = change_jellyseerr_user_notifications(TARGET_URL, TARGET_APIKEY, userNewID, "disable")
            if not notifications_disabled:
                logger.warning(f"Failed to disable notifications for user '{email}', continuing anyway")
            
            requests_success = migrateRequests(userOldID, userNewID)
            
            notifications_enabled = change_jellyseerr_user_notifications(TARGET_URL, TARGET_APIKEY, userNewID, "enable")
            if not notifications_enabled:
                logger.warning(f"Failed to enable notifications for user '{email}', continuing anyway")
                
            # Verify all requests for this user after migration
            logger.info(f"Verifying all requests for user '{email}' (ID: {userNewID}) in Jellyseerr after migration")
            jellyseerr_requests = fetch_user_requests(userNewID)
            if jellyseerr_requests:
                logger.info(f"Found {len(jellyseerr_requests)} requests for user '{email}' in Jellyseerr")
                for req in jellyseerr_requests:
                    media_type = req["media"]["mediaType"]
                    tmdb_id = req["media"]["tmdbId"]
                    title = req["media"].get("title", req["media"].get("name", "Unknown"))
                    logger.info(f"Request: {media_type} '{title}' (tmdbId:{tmdb_id})")
            else:
                logger.warning(f"No requests found for user '{email}' in Jellyseerr after migration")
            
            # Consider migration successful if requests were migrated successfully
            # Notification failures are treated as warnings only
            return requests_success
            
        except Exception as e:
            logger.error(f"Failed to handle notifications/requests for user '{email}': {str(e)}")
            return False
        
    except Exception as e:
        logger.error(f"Failed to migrate user '{user.get('email', 'unknown')}': {str(e)}")
        return False

def change_jellyseerr_user_notifications(jellyseerr_url: str, jellyseerr_api_key: str, user_id: int, change_type: str) -> Optional[Dict[str, Any]]:
    """Change notification settings for a Jellyseerr user.
    
    Args:
        jellyseerr_url: Base URL for Jellyseerr API
        jellyseerr_api_key: API key for authentication
        user_id: ID of the user to modify
        change_type: Either 'enable' or 'disable'
        
    Returns:
        Optional[Dict[str, Any]]: Response from the API if successful, None if failed
        
    Raises:
        ValueError: If change_type is invalid
        RequestException: If the API request fails
    """
    if change_type not in ["enable", "disable"]:
        raise ValueError(f"Invalid change_type: {change_type}")

    headers = {
        "X-Api-Key": jellyseerr_api_key,
        "Content-Type": "application/json"
    }
    url = f"{jellyseerr_url}/user/{user_id}/settings/notifications"

    notification_payload_value = 3661 if change_type == "enable" else 0

    notification_payload = {
        "notificationTypes": {
            "discord": notification_payload_value,
            "email": notification_payload_value,
            "pushbullet": notification_payload_value,
            "pushover": notification_payload_value,
            "slack": notification_payload_value,
            "telegram": notification_payload_value,
            "webhook": notification_payload_value,
            "webpush": notification_payload_value
        }
    }
    
    # Initialize response variable before try block
    response = None
    try:
        logger.debug(f"Sending {change_type} notifications request for user {user_id} to {url}")
        logger.debug(f"Notification payload: {json.dumps(notification_payload)}")
        
        response = requests.post(
            url,
            headers=headers,
            json=notification_payload,
            timeout=30
        )
        response.raise_for_status()
        
        response_data = response.json()
        logger.debug(f"Notification {change_type} response: {json.dumps(response_data)}")
        return response_data
    except RequestException as e:
        logger.error(f"Failed to {change_type} notifications for user {user_id}: {str(e)} - Response: {response.text if response and hasattr(response, 'text') else 'No response text'}")
        raise

def create_request_payload(request: Dict[str, Any], user_id: int) -> Dict[str, Any]:
    """Create a request payload for Jellyseerr API.
    
    Args:
        request: Source request data from Overseerr
        user_id: Target user ID in Jellyseerr
        
    Returns:
        Dict[str, Any]: Request payload for Jellyseerr API
    """
    is4k = request["is4k"]
    media_type = request["media"]["mediaType"]
    tmdb_id = request["media"]["tmdbId"]
    
    logger.debug(f"Creating request payload for {media_type} (tmdbId:{tmdb_id}) with user ID {user_id}")
    
    # Ensure user_id is an integer
    if not isinstance(user_id, int):
        logger.warning(f"User ID {user_id} is not an integer, converting to int")
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            logger.error(f"Failed to convert user ID {user_id} to integer")
            # Raise an exception instead of defaulting to admin user
            raise ValueError(f"Invalid user ID: {user_id}")
    
    logger.debug(f"Using user ID {user_id} for request")
    
    payload = {
        "mediaType": media_type,
        "mediaId": tmdb_id,
        "tmdbId": tmdb_id,
        "is4k": is4k,
        "userId": user_id,
        "sendNotification": False
    }
    
    if media_type == "tv":
        payload["seasons"] = [season["seasonNumber"] for season in request["seasons"]]
        logger.debug(f"Adding seasons to request: {payload['seasons']}")
    
    logger.debug(f"Final request payload: {json.dumps(payload)}")
    return payload

def fetch_tmdb_media_details(tmdb_id: int, media_type: str) -> Dict[str, Any]:
    """Fetch media details from TMDB API.
    
    Args:
        tmdb_id: TMDB ID of the media
        media_type: Type of media ('movie' or 'tv')
        
    Returns:
        Dict containing media details
    """
    try:
        endpoint = 'movie' if media_type == 'movie' else 'tv'
        r = requests.get(
            f"https://api.themoviedb.org/3/{endpoint}/{tmdb_id}",
            params={"api_key": TMDB_APIKEY}
        )
        r.raise_for_status()
        return r.json()
    except RequestException as e:
        logger.error(f"Failed to fetch TMDB details for {media_type} with ID {tmdb_id}: {str(e)}")
        return {}

def is_request_exists(request: Dict[str, Any], target_requests: List[Dict[str, Any]]) -> bool:
    """Check if a request already exists in Jellyseerr.
    
    Args:
        request: Source request from Overseerr
        target_requests: List of existing requests in Jellyseerr
        
    Returns:
        bool: True if request exists, False otherwise
    """
    for target_request in target_requests:
        if (request["media"]["tmdbId"] == target_request["media"]["tmdbId"] and
            request["is4k"] == target_request["is4k"]):
            
            if request["media"]["mediaType"] == "tv":
                requested_seasons = set(season["seasonNumber"] for season in request["seasons"])
                target_seasons = set(season["seasonNumber"] for season in target_request["seasons"])
                if requested_seasons & target_seasons:  # Check for any common seasons
                    return True
            else:
                return True
    return False

def verify_request_created(request_id: int) -> bool:
    """Verify that a request was actually created in Jellyseerr by fetching it.
    
    Args:
        request_id: The ID of the request to verify
        
    Returns:
        bool: True if the request exists, False otherwise
    """
    try:
        logger.debug(f"Verifying request ID {request_id} exists in Jellyseerr")
        r = requests.get(
            url=f"{TARGET_URL}/request/{request_id}",
            headers={"X-Api-Key": TARGET_APIKEY},
            timeout=30
        )
        r.raise_for_status()
        
        # Log details about the request
        request_data = r.json()
        media_type = request_data.get("media", {}).get("mediaType", "unknown")
        tmdb_id = request_data.get("media", {}).get("tmdbId", "unknown")
        title = request_data.get("media", {}).get("title", request_data.get("media", {}).get("name", "Unknown"))
        user_id = request_data.get("requestedBy", {}).get("id", "unknown")
        status = request_data.get("status", "unknown")
        
        logger.debug(f"Request details - ID: {request_id}, Type: {media_type}, Title: '{title}', TMDB ID: {tmdb_id}, User ID: {user_id}, Status: {status}")
        return True
    except Exception as e:
        logger.error(f"Failed to verify request ID {request_id}: {str(e)}")
        return False

def verify_user_exists(user_id: int) -> bool:
    """Verify that a user exists in Jellyseerr by fetching their details.
    
    Args:
        user_id: The ID of the user to verify
        
    Returns:
        bool: True if the user exists, False otherwise
    """
    try:
        logger.info(f"Verifying user ID {user_id} (type: {type(user_id).__name__}) exists in Jellyseerr")
        
        # Ensure user_id is an integer
        if not isinstance(user_id, int):
            logger.warning(f"User ID {user_id} is not an integer, attempting to convert")
            try:
                user_id = int(user_id)
                logger.info(f"Successfully converted user ID to integer: {user_id}")
            except (ValueError, TypeError) as e:
                logger.error(f"Failed to convert user ID {user_id} to integer: {str(e)}")
                return False
        
        r = requests.get(
            url=f"{TARGET_URL}/user/{user_id}",
            headers={"X-Api-Key": TARGET_APIKEY},
            timeout=30
        )
        r.raise_for_status()
        user_data = r.json()
        
        # Log detailed user information
        email = user_data.get('email', 'unknown')
        username = user_data.get('username', 'unknown')
        display_name = user_data.get('displayName', 'unknown')
        user_type = user_data.get('userType', 'unknown')
        created_at = user_data.get('createdAt', 'unknown')
        
        logger.info(f"User verified - ID: {user_id}, Email: {email}, Username: {username}, Display Name: {display_name}, Type: {user_type}")
        logger.debug(f"Full user data: {json.dumps(user_data)}")
        
        # Check if the user has the necessary permissions to make requests
        permissions = user_data.get('permissions', 0)
        logger.debug(f"User permissions: {permissions}")
        
        # Check if user has request permissions (bit 1)
        can_request = (permissions & 1) == 1
        if not can_request:
            logger.warning(f"User ID {user_id} does not have request permissions (permissions={permissions})")
        
        return True
    except Exception as e:
        logger.error(f"Failed to verify user ID {user_id}: {str(e)}")
        return False

def fetch_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Fetch a user by email from Jellyseerr.
    
    Args:
        email: The email of the user to fetch
        
    Returns:
        Optional[Dict[str, Any]]: User data if found, None otherwise
    """
    try:
        logger.debug(f"Fetching user with email '{email}' from Jellyseerr")
        # First, get all users
        r = requests.get(
            url=f"{TARGET_URL}/user",
            headers={"X-Api-Key": TARGET_APIKEY},
            params={"take": 500},
            timeout=30
        )
        r.raise_for_status()
        users_data = r.json()["results"]
        
        # Find user with matching email
        for user in users_data:
            if user.get("email") == email:
                user_id = user.get("id")
                user_type = user.get("userType", "unknown")
                logger.debug(f"Found user with email '{email}': ID {user_id}, Type: {user_type}")
                
                # Get detailed user info
                r = requests.get(
                    url=f"{TARGET_URL}/user/{user_id}",
                    headers={"X-Api-Key": TARGET_APIKEY},
                    timeout=30
                )
                r.raise_for_status()
                user_data = r.json()
                logger.debug(f"User details: {json.dumps(user_data)}")
                return user_data
                
        logger.debug(f"No user found with email '{email}'")
        return None
    except Exception as e:
        logger.error(f"Failed to fetch user with email '{email}': {str(e)}")
        return None

def fetch_user_requests(user_id: int) -> List[Dict[str, Any]]:
    """Fetch all requests for a specific user from Jellyseerr.
    
    Args:
        user_id: The ID of the user to fetch requests for
        
    Returns:
        List[Dict[str, Any]]: List of requests for the user
    """
    try:
        logger.debug(f"Fetching requests for user ID {user_id} from Jellyseerr")
        r = requests.get(
            url=f"{TARGET_URL}/request",
            headers={"X-Api-Key": TARGET_APIKEY},
            params={"take": 100, "requestedBy": user_id},
            timeout=30
        )
        r.raise_for_status()
        requests_data = r.json()["results"]
        logger.debug(f"Found {len(requests_data)} requests for user ID {user_id}")
        
        for req in requests_data:
            media_type = req["media"]["mediaType"]
            tmdb_id = req["media"]["tmdbId"]
            title = req["media"].get("title", req["media"].get("name", "Unknown"))
            logger.debug(f"Request: {media_type} '{title}' (tmdbId:{tmdb_id})")
            
        return requests_data
    except Exception as e:
        logger.error(f"Failed to fetch requests for user ID {user_id}: {str(e)}")
        return []

def migrateRequests(userOldID: int, userNewID: int) -> bool:
    """Migrate requests from Overseerr to Jellyseerr for a specific user.
    
    Args:
        userOldID: Source user ID in Overseerr
        userNewID: Target user ID in Jellyseerr
        
    Returns:
        bool: True if all requests were migrated successfully, False if there were any failures
    """
    try:
        logger.info(f"Migrating requests from Overseerr user ID {userOldID} to Jellyseerr user ID {userNewID}")
        
        # Verify the user exists in Jellyseerr
        if not verify_user_exists(userNewID):
            logger.error(f"User ID {userNewID} does not exist in Jellyseerr or could not be verified")
            return False
        
        # Get all requests for this user
        user_requests = [r for r in SOURCE_REQUESTS if r["requestedBy"]["id"] == userOldID]
        total_requests = len(user_requests)
        logger.info(f"Found {total_requests} requests for user ID {userOldID}")
        
        if not user_requests:
            return True  # No requests to migrate is considered success
            
        # Pre-filter requests that already exist
        new_requests = []
        existing_count = 0
        
        for request in user_requests:
            if is_request_exists(request, TARGET_REQUESTS):
                existing_count += 1
                logger.info(f"Request for {request['media']['mediaType']} (tmdbId:{request['media']['tmdbId']}) already exists in Jellyseerr, skipping")
            else:
                new_requests.append(request)
                
        logger.info(f"Found {existing_count} existing requests, {len(new_requests)} new requests to migrate")
        
        if not new_requests:
            logger.info("All requests already exist in Jellyseerr, skipping migration")
            return True
            
        # Migrate only new requests
        success_count = existing_count  # Start with existing requests as successes
        failure_count = 0
        
        for request in new_requests:
            try:
                tmdb_id = request["media"]["tmdbId"]
                media_type = request["media"]["mediaType"]
                
                # Fetch media details from TMDB
                tmdb_details = fetch_tmdb_media_details(tmdb_id, media_type)
                media_name = tmdb_details.get('title', tmdb_details.get('name', 'Unknown'))
                
                # Log user ID information before creating payload
                logger.info(f"Creating request for {media_type} '{media_name}' (tmdbId:{tmdb_id}) with user ID {userNewID} (type: {type(userNewID).__name__})")
                
                payload = create_request_payload(request, userNewID)
                
                # Log the payload for debugging
                logger.debug(f"Sending request payload: {json.dumps(payload)}")
                
                r = requests.post(
                    url=f"{TARGET_URL}/request",
                    headers={"X-Api-Key": TARGET_APIKEY},
                    json=payload,
                    timeout=30
                )
                r.raise_for_status()
                
                # Check the response content
                response_data = r.json()
                if 'id' in response_data:
                    request_id = response_data['id']
                    logger.info(f"Added request for {media_type} '{media_name}' (tmdbId:{tmdb_id}) to Jellyseerr - Request ID: {request_id}")
                    
                    # Verify the request was created by fetching it back
                    if verify_request_created(request_id):
                        logger.info(f"Verified request ID {request_id} exists in Jellyseerr")
                        success_count += 1
                    else:
                        logger.warning(f"Could not verify request ID {request_id} exists in Jellyseerr")
                        failure_count += 1
                else:
                    logger.warning(f"Request for {media_type} '{media_name}' (tmdbId:{tmdb_id}) may not have been created properly. Response: {json.dumps(response_data)}")
                    failure_count += 1
                
            except RequestException as e:
                # For TV shows, include specific seasons in the error log
                if media_type == 'tv':
                    seasons = [season["seasonNumber"] for season in request.get("seasons", [])]
                    logger.error(f"Failed to migrate request for {media_type} '{media_name}' (tmdbId:{tmdb_id}, seasons:{seasons}): {str(e)}")
                else:
                    logger.error(f"Failed to migrate request for {media_type} '{media_name}' (tmdbId:{tmdb_id}): {str(e)}")
                failure_count += 1
                continue
            except Exception as e:
                # For TV shows, include specific seasons in the error log
                if media_type == 'tv':
                    seasons = [season["seasonNumber"] for season in request.get("seasons", [])]
                    logger.error(f"Unexpected error processing request for {media_type} '{media_name}' (tmdbId:{tmdb_id}, seasons:{seasons}): {str(e)}")
                else:
                    logger.error(f"Unexpected error processing request for {media_type} '{media_name}' (tmdbId:{tmdb_id}): {str(e)}")
                failure_count += 1
                continue
                
        logger.info(f"Request migration completed. Success: {success_count}/{total_requests} ({success_count/total_requests*100:.1f}%), Failures: {failure_count}/{total_requests} ({failure_count/total_requests*100:.1f}%)")
        
        # Verify all requests were created by fetching them from Jellyseerr
        logger.info(f"Verifying all requests for user ID {userNewID} in Jellyseerr")
        jellyseerr_requests = fetch_user_requests(userNewID)
        if jellyseerr_requests:
            logger.info(f"Found {len(jellyseerr_requests)} requests for user ID {userNewID} in Jellyseerr")
        else:
            logger.warning(f"No requests found for user ID {userNewID} in Jellyseerr")
            
        return failure_count == 0
                
    except Exception as e:
        logger.error(f"Failed to migrate requests for user {userOldID}: {str(e)}")
        return False

if __name__ == '__main__':
    main()
