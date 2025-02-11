#!/usr/bin/env python3
# Python script to migrate Overseerr to Jellyseerr
# https://github.com/Quack6765/seerr-migration-script

import sys, time, argparse, requests, json

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

    return parser.parse_args()

def main():
    args = parse_args()

    if not args.source or not args.source_api_key or not args.target or not args.target_api_key:
        print("All arguments must be provided and cannot be empty.")
        return 1

    global SOURCE_URL
    global SOURCE_APIKEY
    global TARGET_URL
    global TARGET_APIKEY

    SOURCE_URL=args.source+"/api/v1"
    SOURCE_APIKEY=args.source_api_key
    TARGET_URL=args.target+"/api/v1"
    TARGET_APIKEY=args.target_api_key
    
    migration()
    print("All done !")

def migration():
    testConnections()

    # Get list of current Overseerr users
    global SOURCE_USERS
    r = requests.get(url=SOURCE_URL+"/user", headers={"X-Api-Key":SOURCE_APIKEY}, params={"take":500})
    SOURCE_USERS = r.json()["results"]

    # Get list of current Jellyseerr users
    global TARGET_USERS
    r = requests.get(url=TARGET_URL+"/user", headers={"X-Api-Key":TARGET_APIKEY}, params={"take":500})
    TARGET_USERS = r.json()["results"]

    # Get all current unfulfilled requests in Overseer
    global SOURCE_REQUESTS
    r = requests.get(url=SOURCE_URL+"/request", headers={"X-Api-Key":SOURCE_APIKEY}, params={"take":1000,"filter":"unavailable"})
    SOURCE_REQUESTS = r.json()["results"]

    # Get all current unfulfilled requests in Jellyseerr
    global TARGET_REQUESTS
    r = requests.get(url=TARGET_URL+"/request", headers={"X-Api-Key":TARGET_APIKEY}, params={"take":1000,"filter":"unavailable"})
    TARGET_REQUESTS = r.json()["results"]

    # Migrate users
    r = requests.get(url=SOURCE_URL+"/user", headers={"X-Api-Key":SOURCE_APIKEY},params={"take":500})
    source_data = r.json()
    for user in source_data["results"]:
        # Single user for debugging
        if user["email"] == "test@example.com":
            migrateUser(user)

def testConnections():

    status = "Testing Jellyseerr connection ... "
    print(status, end="", flush=True)
    r = requests.get(url=SOURCE_URL+"/settings/main", headers={"X-Api-Key":SOURCE_APIKEY})
    if not r.ok:
        print("ERROR: Couldn't connect to Overseerr ! HTTP error: "+str(r.status_code)+" - "+str(r.text))
        sys.exit(1)
    else:
        status = "OK"
        print(status)    

    status = "Testing Overseerr connection ... "
    print(status, end="", flush=True)
    r = requests.get(url=TARGET_URL+"/settings/main", headers={"X-Api-Key":TARGET_APIKEY})
    if not r.ok:
        print("ERROR: Couldn't connect to Jellyseerr ! HTTP error: "+str(r.status_code)+" - "+str(r.text))
        sys.exit(1)
    else:
        status = "OK"
        print(status)    
        
def migrateUser(user):

    # Check if user already exist on Jellyseerr
    user_found = False
    for existingUser in TARGET_USERS:
        if existingUser["email"] == user["email"]:
            user_found = True
            userNewID = existingUser["id"]

    if user_found == False:
        if user["username"] == None:
            newUsername = user["plexUsername"]
        else:
            newUsername = user["username"]
        PAYLOAD = {
            "email": user["email"],
            "username": newUsername,
            "permissions": user["permissions"]
        }
        r = requests.post(url=TARGET_URL+"/user", headers={"X-Api-Key":TARGET_APIKEY}, json = PAYLOAD)
        if not r.ok:
            print("ERROR: Trouble migrating user '"+user["email"]+"' ! HTTP error: "+str(r.status_code)+" - "+str(r.text))
            sys.exit(1)
        userNewID=r.json()["id"]

        # Fix for permissions
        r = requests.put(url=TARGET_URL+"/user/"+str(userNewID), headers={"X-Api-Key":TARGET_APIKEY}, json = {"permissions": user["permissions"]})
        if not r.ok:
            print("ERROR: Trouble changing permissions for user '"+user["email"]+"' ! HTTP error: "+str(r.status_code)+" - "+str(r.text))
            sys.exit(1)

        print("User '"+user["email"]+"' created in Jellyseerr")

    else:
        print("User '"+user["email"]+"' already in Jellyseer. Skipping")

    # Fetch user ID
    for oldUser in SOURCE_USERS:
        if oldUser["email"] == user["email"]:
            userOldID=oldUser["id"]

    # Disable notifications for the user
    change_jellyseerr_user_notifications(TARGET_URL, TARGET_APIKEY, userNewID, "disable")
    print(f"Disabled notifications for user '{user['email']}' in Jellyseerr")

    migrateRequests(userOldID,userNewID)

    # Enable notifications for the user
    change_jellyseerr_user_notifications(TARGET_URL, TARGET_APIKEY, userNewID, "enable")
    print(f"Enabled notifications for user '{user['email']}' in Jellyseerr")

def change_jellyseerr_user_notifications(jellyseerr_url, jellyseerr_api_key, user_id, change_type):

    headers = {
        "X-Api-Key": jellyseerr_api_key,
        "Content-Type": "application/json"
    }
    url = f"{jellyseerr_url}/user/{user_id}/settings/notifications"

    if change_type == "disable":
        notification_payload_value = 0
    elif change_type == "enable":
        notification_payload_value = 3661

    jellyseerr_notification_payload = {
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
        response = requests.post(url, headers=headers, data=json.dumps(jellyseerr_notification_payload))
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error disabling Jellyseerr user notifications for user ID {user_id}: {e}")
        return None

def migrateRequests(userOldID,userNewID):

    for oldRequest in SOURCE_REQUESTS:
        if oldRequest["requestedBy"]["id"] == userOldID:
            request_found = False
            if oldRequest["is4k"] == True:
                request4K = True
            else:
                request4K = False
            if oldRequest["media"]["mediaType"] == "tv" :
                seasonRequested=[]
                for season in oldRequest["seasons"]:
                    seasonRequested.append(season["seasonNumber"])
                for newRequest in TARGET_REQUESTS:
                    if oldRequest["media"]["tmdbId"] == newRequest["media"]["tmdbId"] and oldRequest["is4k"] == newRequest["is4k"]:
                        for season in newRequest["seasons"]:
                            if season["seasonNumber"] in seasonRequested:
                                request_found=True
                PAYLOAD = {
                    "mediaType": oldRequest["media"]["mediaType"],
                    "mediaId": oldRequest["media"]["tmdbId"],
                    "tmdbId": oldRequest["media"]["tmdbId"],
                    "is4k": request4K,
                    "seasons": seasonRequested,
                    "userId": userNewID,
                    "sendNotification": False
                }

            elif oldRequest["media"]["mediaType"] == "movie" :
                for newRequest in TARGET_REQUESTS:
                    if oldRequest["media"]["tmdbId"] == newRequest["media"]["tmdbId"] and oldRequest["is4k"] == newRequest["is4k"]:
                        request_found = True
                PAYLOAD = {
                    "mediaType": oldRequest["media"]["mediaType"],
                    "mediaId": oldRequest["media"]["tmdbId"],
                    "tmdbId": oldRequest["media"]["tmdbId"],
                    "is4k": request4K,
                    "userId": userNewID,
                    "sendNotification": False
                }
            if request_found == False:
                r = requests.post(url=TARGET_URL+"/request", headers={"X-Api-Key":TARGET_APIKEY}, json = PAYLOAD)
                if not r.ok:
                    print("ERROR: Trouble adding request with ID 'tmdbId:"+str(PAYLOAD["mediaId"])+"' ! HTTP error: "+str(r.status_code)+" - "+str(r.text))
                    continue
                print("Added request for 'tmdbId:"+str(PAYLOAD["mediaId"])+"' to Jellyseer")
            else:
                print("Request 'tmdbId:"+str(PAYLOAD["mediaId"])+"' already in Jellyseer. Skipping")

if __name__ == '__main__':
    main()
