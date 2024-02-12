# Python script to migrate Overseerr to Jellyseerr
# https://github.com/Quack6765/seerr-migration-script

import sys, argparse, requests

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
    
    testConnections()
    migrateUsers()

def testConnections():

    r = requests.get(url=SOURCE_URL+"/settings/main", headers={"X-Api-Key":SOURCE_APIKEY})
    if r.status_code != 200:
        print("ERROR: Couldn't connect to Overseerr ! HTTP error code: "+str(r.status_code))
        sys.exit(1)

    r = requests.get(url=TARGET_URL+"/settings/main", headers={"X-Api-Key":TARGET_APIKEY})
    if r.status_code != 200:
        print("ERROR: Couldn't connect to Jellyseerr ! HTTP error code: "+str(r.status_code))
        sys.exit(1)

    print("Connection Successfull !")
        
def migrateUsers():
    r = requests.get(url=SOURCE_URL+"/user/230", headers={"X-Api-Key":SOURCE_APIKEY})
    data = r.json()

    PAYLOAD = {
        "email": data["email"],
        "username": data["username"],
        "permissions": 4194464
    }
    
    # r = requests.post(url=TARGET_URL+"/user", headers={"X-Api-Key":TARGET_APIKEY}, json = PAYLOAD)
    # if r.status_code != 201:
    #     print("ERROR: Trouble migrating user 'bgendron' ! HTTP error code: "+str(r.status_code))
    #     sys.exit(1)

    migrateRequests()

def migrateRequests():
    r = requests.get(url=SOURCE_URL+"/request?take=500&filter=unavailable", headers={"X-Api-Key":SOURCE_APIKEY})
    data = r.json()

    for request in data["results"]:
        if request["requestedBy"]["id"] == 230:
            if request["media"]["mediaType"] == "tv" :
                PAYLOAD = {
                    "mediaType": request["media"]["mediaType"],
                    "mediaId": request["media"]["tvdbId"],
                    "tvdbId": request["media"]["tvdbId"],
                    "seasons": request["seasons"],
                    "userId": 6
                }           
            elif request["media"]["mediaType"] == "movie" :
                PAYLOAD = {
                    "mediaType": request["media"]["mediaType"],
                    "mediaId": request["media"]["tmdbId"],
                    "tmdbId": request["media"]["tmdbId"],
                    "userId": 6
                }
                
            print(PAYLOAD)
            r = requests.post(url=TARGET_URL+"/request", headers={"X-Api-Key":TARGET_APIKEY}, json = PAYLOAD)
            print(r.text)

if __name__ == '__main__':
    main()