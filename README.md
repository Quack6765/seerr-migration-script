# Overseerr to Jellyseerr Migration Script

This Python script migrates users and their media requests from Overseerr to Jellyseerr.

## Prerequisites
- Python 3.x with `requests` library
- API access to both Overseerr and Jellyseerr instances
- **IMPORTANT:** To maintain Jellyfin/Emby login functionality, you MUST import users from Jellyfin/Emby into Jellyseerr BEFORE running this script. Otherwise, users will be created as local accounts.
- **IMPORTANT:** Jellyseerr requires email notifications to be enabled in global settings. You can enable this with dummy SMTP settings if you don't need actual email functionality.

## Usage
```bash
python3 overseerr-migration-script.py -s SOURCE_URL -k SOURCE_API_KEY -t TARGET_URL -a TARGET_API_KEY [-m TMDB_API_KEY] [-d]
```

### Arguments
- `-s` or `--source`: URL of the source Overseerr instance
- `-k` or `--source_api_key`: API key for the source Overseerr instance
- `-t` or `--target`: URL of the target Jellyseerr instance
- `-a` or `--target_api_key`: API key for the target Jellyseerr instance
- `-m` or `--tmdb_api_key`: (Optional) TMDB API key for fetching media names
- `-d` or `--debug`: (Optional) Enable debug logging for troubleshooting

### Example
```bash
python3 overseerr-migration-script.py \
  -s https://your-overseerr.example.com \
  -k YOUR_OVERSEERR_API_KEY \
  -t https://your-jellyseerr.example.com \
  -a YOUR_JELLYSEERR_API_KEY \
  -m YOUR_TMDB_API_KEY
```

## Features
- 👥 Migrates user accounts and their unfulfilled media requests
- 🔄 Detects and uses existing Jellyfin/Emby users with matching emails
- 🎬 Preserves request details including seasons for TV shows
- 🚫 Skips existing users and requests to prevent duplicates
- 📧 Temporarily disables notifications during migration
- 🐞 Debug mode for troubleshooting issues

## Troubleshooting
- Use the `-d` flag to enable detailed debug logging
- Check the `migration.log` file for detailed information
