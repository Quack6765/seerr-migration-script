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
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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

    return parser.parse_args()

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
        logger.error(f"Failed to fetch data from {endpoint}: {str(e)}")
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
    try:
        r = requests.get(
            url=SOURCE_URL+"/settings/main", 
            headers={"X-Api-Key": SOURCE_APIKEY},
            timeout=10
        )
        r.raise_for_status()
        print("OK")
    except requests.exceptions.RequestException as e:
        logger.error(f"Couldn't connect to Overseerr! {str(e)}")
        return False

    # Test Jellyseerr connection
    status = "Testing Jellyseerr connection ... "
    print(status, end="", flush=True)
    try:
        r = requests.get(
            url=TARGET_URL+"/settings/main", 
            headers={"X-Api-Key": TARGET_APIKEY},
            timeout=10
        )
        r.raise_for_status()
        print("OK")
    except requests.exceptions.RequestException as e:
        logger.error(f"Couldn't connect to Jellyseerr! {str(e)}")
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

        # Check if user already exists
        existing_user = next(
            (u for u in TARGET_USERS if u["email"] == email),
            None
        )
        
        if existing_user:
            logger.info(f"User '{email}' already exists in Jellyseerr, skipping creation")
            userNewID = existing_user["id"]
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
                
                try:
                    r = requests.post(
                        url=f"{TARGET_URL}/user",
                        headers={"X-Api-Key": TARGET_APIKEY},
                        json=payload,
                        timeout=30
                    )
                    r.raise_for_status()
                    userNewID = r.json()["id"]
                    
                    # Update permissions
                    r = requests.put(
                        url=f"{TARGET_URL}/user/{userNewID}",
                        headers={"X-Api-Key": TARGET_APIKEY},
                        json={"permissions": user.get("permissions", 0)},
                        timeout=30
                    )
                    r.raise_for_status()
                    logger.info(f"User '{email}' created in Jellyseerr")
                    
                except RequestException as e:
                    logger.error(f"Failed to create/update user '{email}': {str(e)}")
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
    
    try:
        response = requests.post(
            url, 
            headers=headers, 
            json=notification_payload,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        logger.error(f"Failed to {change_type} notifications for user {user_id}: {str(e)}")
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

def migrateRequests(userOldID: int, userNewID: int) -> bool:
    """Migrate requests from Overseerr to Jellyseerr for a specific user.
    
    Args:
        userOldID: Source user ID in Overseerr
        userNewID: Target user ID in Jellyseerr
        
    Returns:
        bool: True if all requests were migrated successfully, False if there were any failures
    """
    try:
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
                
                payload = create_request_payload(request, userNewID)
                
                r = requests.post(
                    url=f"{TARGET_URL}/request",
                    headers={"X-Api-Key": TARGET_APIKEY},
                    json=payload,
                    timeout=30
                )
                r.raise_for_status()
                logger.info(f"Added request for {media_type} '{media_name}' (tmdbId:{tmdb_id}) to Jellyseerr")
                success_count += 1
                
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
        return failure_count == 0
                
    except Exception as e:
        logger.error(f"Failed to migrate requests for user {userOldID}: {str(e)}")
        return False

if __name__ == '__main__':
    main()
