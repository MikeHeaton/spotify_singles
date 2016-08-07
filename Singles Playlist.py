# -*- coding: utf-8 -*-
"""
@author: Mike Heaton
www.mike-heaton.com

A small script to make a useful Spotify playlist, aggregating any songs which
are the only ones in your library by that artist AND in that album.

This means that all those random songs you saved off of Discover Weekly but
didn't investigate further are now in one place!
"""

import time
import requests
import json
from collections import Counter
from datetime import datetime


def build_auth_url(auth_url_base, client_id,
                   response_url="https://example.com/callback", scope=""):
    # Takes data for generating an authorisation URL and returns
    # a formatted URL for the API.
    response_url = response_url.replace("/", "%2F")
    response_url = response_url.replace(":", "%3A")
    return (auth_url_base + "?client_id=" + client_id +
            "&response_type=code&redirect_uri=" + response_url +
            "&scope=" + scope)


def auth(scopes):
    # Talks to the Spotify API and gets an access token, with the given scopes.

    auth_url = build_auth_url(auth_url_base, clientid, scope=scopes)
    print(auth_url)

    # The user logs in to Spotify via web browser and is redirected to a URI.
    # The 'code=' part of that URI is the response code needed by the API.
    response_uri = input("Paste the above url into a browser, log in if "
                         "necessary,and enter the url given in response:\n")
    loc = response_uri.find("code=")
    response_code = response_uri[loc+5:]

    bodydict = {
                "code": response_code,
                "grant_type": "authorization_code",
                "redirect_uri": "https://example.com/callback",
                "client_id": clientid,
                "client_secret": clientsecret,
                "scope": "playlist-modify-private playlist-read-private"
                         " user-library-read"
                }

    response_auth = requests.post("https://accounts.spotify.com/api/token",
                                  data=bodydict)

    access_token = "Bearer " + response_auth.json()['access_token']
    return access_token

# Details for the Spotify application.
# In OAuth2 it's declared a Bad Idea to make the client secret public.
# However the Spotify app keeps no data, has no special privileges and
# can't incur any charges or anything like that, so for now I'm relaxed.
# Think of the Spotify app as just a sandbox.
# If I can implement this as a web app on www.mike-heaton.com, then I'll
# do this more securely I guess. But I want people to be able to run
# the script easily, for which they need access to the client details!
clientid = "0ab11486a90c497fa34304c0dfef42c6"
clientsecret = "b7c183c5dfcb42f097e72b03919a15b2"
nec_scopes = ("playlist-modify-private%20playlist-read-private%20"
              "user-library-read")

auth_url_base = "https://accounts.spotify.com/authorize/"
access_token = auth(nec_scopes)
userdata_raw = requests.get("https://api.spotify.com/v1/me",
                            headers={"Authorization": access_token})

userdata = userdata_raw.json()
username = userdata['id']

# Scrape all of the user's tracks from the API into a list.
# The Spotify API can only grab 50 tracks per request, annoyingly, so this
# takes a bit of time.

get_url = "https://api.spotify.com/v1/me/tracks?limit=50"
track_library = []

# The get_url is updated with each request, and points to the URl to call
# to grab the next set of tracks. When there are no more tracks to grab,
# the get_url is set to None and we break.
while get_url is not None:
    libdata = requests.get(get_url, headers={"Authorization": access_token})
    response = libdata.json()

    try:
        # The try/except loop is to compensate for 502 errors.
        # In case of a 502 error, response won't have a 'next' key
        # and so exit the 'try' with a KeyError (and try again).
        get_url = response['next']
        track_library = track_library + response['items']
        print("Reading your library: " +
              str(len(track_library)) + " songs...")

    except KeyError:
        print(response, " retrying...")
        time.sleep(2)

print("\nLibrary read. Analysing...")
# Pick out those artists with only one track in the library.
artists = Counter([t['track']['artists'][0]['name'] for t in track_library])
single_artists = [a for a in artists if artists[a] == 1]

# Pick out those albums with only one track in the library.
albums = Counter([t['track']['album']['id'] for t in track_library])
single_albums = [a for a in albums if albums[a] == 1]

# Add tracks by those artists and in those albums
print("Constructing playlist...")
singlesongplaylist_data = []

for t in track_library:
    if (t['track']['artists'][0]['name'] in single_artists and
            t['track']['album']['id'] in single_albums):
        singlesongplaylist_data.append(t['track']['uri'])

makeplaylist_uri = ("https://api.spotify.com/v1/users/" + username +
                    "/playlists")
makeplaylist_data = json.dumps({
                                "name": ("Single tracks " +
                                         datetime.today().isoformat()[:10]),
                                "public": False
                              })

print("Creating playlist on Spotify...")
singlesongplaylist = requests.post(makeplaylist_uri,
                                   headers={"Authorization": access_token,
                                           "Content-Type": "application/json"},
                                   data=makeplaylist_data)

n = 0

while n < len(singlesongplaylist_data):
    addtoplaylist_uri = ("https://api.spotify.com/v1/users/" + username +
                         "/playlists/" + singlesongplaylist.json()['id'] +
                         "/tracks")

    m = min(n+100, len(singlesongplaylist_data))
    addtoplaylist_data = json.dumps({"uris": singlesongplaylist_data[n:m]})
    dump = requests.post(addtoplaylist_uri,
                         headers={
                                  "Authorization": access_token,
                                  "Content-Type": "application/json"
                                 },
                         data=addtoplaylist_data)
    print("Populating playlist on Spotify: " + str(m+1) + " tracks added...")
    n = m

print("Complete! " + str(len(singlesongplaylist_data)+1) +
      " songs were found.")
