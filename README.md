# Overseerr to Jellyseerr Migration Script

## Overview
This Python script facilitates the migration of users and requests from Overseerr to Jellyseerr. It transfers user accounts and their existing media requests between the two platforms.

## Prerequisites
- Python 3.x
- `requests` library
- API access to both Overseerr and Jellyseerr instances

## Usage
```bash
python3 overseerr-migration-script.py -s SOURCE_URL -k SOURCE_API_KEY -t TARGET_URL -a TARGET_API_KEY [-m TMDB_API_KEY]
```

## Arguments
- `-s` or `--source`: URL of the source Overseerr instance
- `-k` or `--source_api_key`: API key for the source Overseerr instance
- `-t` or `--target`: URL of the target Jellyseerr instance
- `-a` or `--target_api_key`: API key for the target Jellyseerr instance
- `-m` or `--tmdb_api_key`: (Optional) TMDB API key for fetching media details

## Features
- 👥 Migrate user accounts
- 🎬 Transfer media requests
- 🌐 Optional media name retrieval using TMDB API
- 📝 Detailed logging of migration process

## Logging
The script generates a `migration.log` file with detailed information about the migration process.

### Log Examples

#### Successful Migration
```
2025-02-14 15:39:19,862 - INFO - User 'user@example.com' already exists in Jellyseerr, skipping creation
2025-02-14 15:39:19,882 - INFO - Found 2 requests for user ID 539
2025-02-14 15:39:19,882 - INFO - Request for movie (tmdbId:1043499) already exists in Jellyseerr, skipping
2025-02-14 15:39:19,882 - INFO - Found 1 existing requests, 1 new requests to migrate
2025-02-14 15:39:19,992 - INFO - Added request for tv 'Alice in Borderland' (tmdbId:110316) to Jellyseerr
2025-02-14 15:39:19,992 - INFO - Request migration completed. Success: 2/2 (100.0%), Failures: 0/2 (0.0%)
```

#### Partial Migration with Errors
```
2025-02-14 14:54:04,208 - ERROR - Failed to migrate request for tv 'Some TV Show Name' (tmdbId:2176, seasons:[1,2,3]): 500 Server Error: Internal Server Error
```

### Debugging Logs
The detailed logs help you diagnose migration issues:
- Successful requests show the media name and TMDB ID
- Failed requests include:
  - Media type (tv/movie)
  - Media name
  - TMDB ID
  - Specific seasons (for TV shows)
  - Exact error message

This makes it easy to:
- Track which media was successfully migrated
- Identify which specific requests failed
- Understand the reason for migration failures
- Manually handle problematic requests if needed

## Example
```bash
python3 overseerr-migration-script.py \
  -s https://your-overseerr.example.com \
  -k YOUR_OVERSEERR_API_KEY \
  -t https://your-jellyseerr.example.com \
  -a YOUR_JELLYSEERR_API_KEY \
  -m YOUR_TMDB_API_KEY (Optional)
```

## Notes
- The TMDB API key is optional but recommended for retrieving media names
- Existing users and requests will be skipped to prevent duplicates
- Notifications are temporarily disabled during migration to prevent mass send of emails.
- Users in Jellyseerr will be created as local users by default. If you want to use the 'Emby Login' feature for your new users, make sure to import the Emby users manually in Jellyseer using the 'Import Emby Users' button beforehand. A match on the email will then be used to import their requests.
