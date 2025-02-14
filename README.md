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
2025-02-14 14:53:45,123 - INFO - Starting migration process...
2025-02-14 14:53:45,456 - INFO - Found 10 requests for user ID 123
2025-02-14 14:53:46,789 - INFO - Added request for tv 'The Mandalorian' (tmdbId:66732) to Jellyseerr
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
