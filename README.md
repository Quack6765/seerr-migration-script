# Overseerr to Jellyseerr Migration Script

## Overview
This Python script facilitates the migration of users and requests from Overseerr to Jellyseerr. It transfers user accounts and their existing media requests between the two platforms.

## Prerequisites
- Python 3.x
- `requests` library
- API access to both Overseerr and Jellyseerr instances

## Usage
```bash
python3 overseerr-migration-script.py -s SOURCE_URL -k SOURCE_API_KEY -t TARGET_URL -a TARGET_API_KEY [-m TMDB_API_KEY] [-d]
```

## Arguments
- `-s` or `--source`: URL of the source Overseerr instance
- `-k` or `--source_api_key`: API key for the source Overseerr instance
- `-t` or `--target`: URL of the target Jellyseerr instance
- `-a` or `--target_api_key`: API key for the target Jellyseerr instance
- `-m` or `--tmdb_api_key`: (Optional) TMDB API key for fetching media details
- `-d` or `--debug`: (Optional) Enable debug logging for detailed diagnostics

## Features
- 👥 Migrate user accounts
- 🎬 Transfer unfulfilled media requests
- 🌐 Optional media name retrieval using TMDB API
- 📝 Detailed logging of migration process

## Logging
The script generates a `migration.log` file with detailed information about the migration process. By default, the log includes INFO, WARNING, and ERROR level messages.

### Debug Mode
For more detailed logging, you can enable debug mode with the `-d` or `--debug` flag:

```bash
python3 overseerr-migration-script.py -s SOURCE_URL -k SOURCE_API_KEY -t TARGET_URL -a TARGET_API_KEY -d
```

Debug mode provides extensive information about:
- User details (ID, email, username, display name, type, permissions)
- Request payloads and responses
- API calls and responses
- Verification steps for users and requests

This is particularly useful for troubleshooting issues with:
- User creation or identification
- Request creation
- Permission problems
- API communication errors

### Log Examples

#### Successful Migration
```
2025-02-14 15:39:19,862 - INFO - User 'user@example.com' already exists in Jellyseerr with ID 123, source: jellyfin
2025-02-14 15:39:19,882 - INFO - Found 2 requests for user ID 539
2025-02-14 15:39:19,882 - INFO - Request for movie (tmdbId:1043499) already exists in Jellyseerr, skipping
2025-02-14 15:39:19,882 - INFO - Found 1 existing requests, 1 new requests to migrate
2025-02-14 15:39:19,992 - INFO - Added request for tv 'Alice in Borderland' (tmdbId:110316) to Jellyseerr - Request ID: 456
2025-02-14 15:39:19,992 - INFO - Verified request ID 456 exists in Jellyseerr
2025-02-14 15:39:19,992 - INFO - Request migration completed. Success: 2/2 (100.0%), Failures: 0/2 (0.0%)
```

#### Partial Migration with Errors
```
2025-02-14 14:54:04,208 - ERROR - Failed to migrate request for tv 'Some TV Show Name' (tmdbId:2176, seasons:[1,2,3]): 500 Server Error: Internal Server Error
```

#### Debug Mode Example
```
2025-02-14 15:39:19,862 - DEBUG - Fetching user with email 'user@example.com' from Jellyseerr
2025-02-14 15:39:19,872 - DEBUG - Found user with email 'user@example.com': ID 123, Type: jellyfin
2025-02-14 15:39:19,882 - DEBUG - User details - ID: 123, Email: user@example.com, Username: username, Display Name: User Name, Type: jellyfin, Created: 2025-02-10T12:34:56.000Z
2025-02-14 15:39:19,882 - DEBUG - User permissions: 2
2025-02-14 15:39:19,882 - INFO - User 'user@example.com' already exists in Jellyseerr with ID 123, source: jellyfin
2025-02-14 15:39:19,882 - INFO - Adding request permission to existing user 'user@example.com'
```

### Diagnostic Information
The detailed logs help you diagnose migration issues:
- Successful requests show the media name, TMDB ID, and request ID
- Failed requests include:
  - Media type (tv/movie)
  - Media name
  - TMDB ID
  - Specific seasons (for TV shows)
  - Exact error message
- User information includes:
  - User ID
  - Email
  - Username
  - User type (local, jellyfin, plex)
  - Permissions

This makes it easy to:
- Track which media was successfully migrated
- Identify which specific requests failed
- Understand the reason for migration failures
- Detect user permission or identification issues
- Manually handle problematic requests if needed

## Examples

### Basic Usage
```bash
python3 overseerr-migration-script.py \
  -s https://your-overseerr.example.com \
  -k YOUR_OVERSEERR_API_KEY \
  -t https://your-jellyseerr.example.com \
  -a YOUR_JELLYSEERR_API_KEY \
  -m YOUR_TMDB_API_KEY
```

## Notes
- The TMDB API key is optional but recommended for retrieving media names
- Use the debug flag (`-d`) when troubleshooting issues with the migration
- Existing users and requests will be skipped to prevent duplicates
- Notifications are temporarily disabled during migration to prevent mass send of emails
- If you want to use the 'Jellyfin Login' feature for your new users, make sure to import the Jellyfin users manually in Jellyseerr using the 'Import Jellyfin Users' button beforehand
