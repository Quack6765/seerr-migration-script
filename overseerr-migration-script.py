# Python script to migrate Overseerr to Jellyseerr
# https://github.com/Quack6765/seerr-migration-script

import sys, time, argparse, requests

def parse_args():
    parser = argparse.ArgumentParser()
    
    # Add source argument
    parser.add_argument('-s', '--source', help='The source from which to retrieve data')

    # Add source API key argument
    parser.add_argument('-k', '--source_api_key', help='The API Key for the source')

    # Add target argument
    parser.add_argument('-t', '--target', help='The target where to send data')
    
    # Add target API key argument
    parser.add_argument('-a', '--target_api_key', help='The API Key for the target')

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
        if user["email"] == "plex2@po-mail.com":
            migrateUser(user)

def testConnections():

    status = "Testing Jellyseerr connection ... "
    print(status, end="", flush=True)
    r = requests.get(url=SOURCE_URL+"/settings/main", headers={"X-Api-Key":SOURCE_APIKEY})
    if r.status_code != 200:
        print("ERROR: Couldn't connect to Overseerr ! HTTP error code: "+str(r.status_code))
        sys.exit(1)
    else:
        status = "OK"
        print(status)    

    status = "Testing Overseerr connection ... "
    print(status, end="", flush=True)
    r = requests.get(url=TARGET_URL+"/settings/main", headers={"X-Api-Key":TARGET_APIKEY})
    if r.status_code != 200:
        print("ERROR: Couldn't connect to Jellyseerr ! HTTP error code: "+str(r.status_code))
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
            userNewID=existingUser["id"]

    if user_found == False:
        PAYLOAD = {
            "email": user["email"],
            "username": user["username"],
            "permissions": 4194464
        }
        r = requests.post(url=TARGET_URL+"/user", headers={"X-Api-Key":TARGET_APIKEY}, json = PAYLOAD)
        if r.status_code != 201:
            print("ERROR: Trouble migrating user 'bgendron' ! HTTP error code: "+str(r.status_code))
            sys.exit(1)
        userNewID=r.text["id"]
        print("User '"+user["email"]+"' created in Jellyseerr")
    else:
        print("User '"+user["email"]+"' already in Jellyseer. Skipping")

    # Fetch user ID
    for oldUser in SOURCE_USERS:
        if oldUser["email"] == user["email"]:
            userOldID=oldUser["id"]
    
    migrateRequests(userOldID,userNewID)

def migrateRequests(userOldID,userNewID):

    for oldRequest in SOURCE_REQUESTS:
        if oldRequest["requestedBy"]["id"] == userOldID:
            request_found=False
            if oldRequest["media"]["mediaType"] == "tv" :
                for newRequest in TARGET_REQUESTS:
                    if oldRequest["media"]["tvdbId"] == newRequest["media"]["tvdbId"]:
                        request_found=True
                PAYLOAD_TYPE="tvdbId"
                PAYLOAD = {
                    "mediaType": oldRequest["media"]["mediaType"],
                    "mediaId": oldRequest["media"][PAYLOAD_TYPE],
                    PAYLOAD_TYPE: oldRequest["media"][PAYLOAD_TYPE],
                    "seasons": oldRequest["seasons"],
                    "userId": userNewID
                }           
            elif oldRequest["media"]["mediaType"] == "movie" :
                for newRequest in TARGET_REQUESTS:
                    if oldRequest["media"]["tmdbId"] == newRequest["media"]["tmdbId"]:
                        request_found=True
                PAYLOAD_TYPE="tmdbId"
                PAYLOAD = {
                    "mediaType": oldRequest["media"]["mediaType"],
                    "mediaId": oldRequest["media"][PAYLOAD_TYPE],
                    PAYLOAD_TYPE: oldRequest["media"][PAYLOAD_TYPE],
                    "userId": userNewID
                }
            if request_found == False:
                r = requests.post(url=TARGET_URL+"/request", headers={"X-Api-Key":TARGET_APIKEY}, json = PAYLOAD)
                if r.status_code != 201:
                    print("ERROR: Trouble adding request with ID '"++"' ! HTTP error code: "+str(r.status_code))
                    sys.exit(1)
                print("Added request for '"+PAYLOAD_TYPE+":"+str(PAYLOAD["mediaId"])+"' to Jellyseer")
            else:
                print("Request '"+PAYLOAD_TYPE+":"+str(PAYLOAD["mediaId"])+"' already in Jellyseer. Skipping")
            

if __name__ == '__main__':
    main()
