import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
from dotenv import load_dotenv
import re
import json

# Load Spotify API credentials from environment variables
load_dotenv()
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

# Authenticate with Spotify API using Client Credentials Flow
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET))

def get_playlist_id_from_url(url):
    """Extracts the playlist ID from a Spotify URL."""
    match = re.search(r"playlist/([a-zA-Z0-9]+)", url)
    if match:
        return match.group(1)
    else:
        raise ValueError("Invalid Spotify playlist URL")

def extract_artists_from_playlists(playlist_urls):
    """Extracts unique artists from multiple Spotify playlists and saves them to a JSON file."""
    # Dictionary to hold unique artists with their ID and name
    artists = {}

    for playlist_url in playlist_urls:
        playlist_id = get_playlist_id_from_url(playlist_url)
        tracks = []
        results = sp.playlist_tracks(playlist_id)
        
        # Collect initial batch of tracks
        tracks.extend(results['items'])

        # Keep fetching tracks as long as there are more to retrieve
        while results['next']:
            results = sp.next(results)
            tracks.extend(results['items'])

        # Extract artist information for each track
        for item in tracks:
            track = item.get('track')
            if track is None:
                continue

            # Loop through each artist on the track to ensure all are included
            for artist in track['artists']:
                artist_id = artist['id']
                artist_name = artist['name']

                # Only add if the artist is not already in the dictionary
                if artist_id not in artists:
                    artists[artist_id] = {
                        "name": artist_name
                    }

    # Save the artist information to a JSON file
    with open("male_manipulator_artists.json", "w") as f:
        json.dump(artists, f, indent=2)

    print("Artist data saved to 'male_manipulator_artists.json'.")

# Example usage
# Replace these URLs with the actual Spotify URLs of the playlists you want to analyze
playlist_urls = [
    'https://open.spotify.com/playlist/0oHtOZP0NPXQwrwfQqGDXQ?si=6aefe9d5c4bf44b8',
    'https://open.spotify.com/playlist/5iEQua9YVa0oSqgEXRt2Ed?si=c770c5fd6bf14fe2',
    'https://open.spotify.com/playlist/0Yd12zlpaTooMGS4yEKgZd?si=6559c9c06f294d19'  # Add more playlist URLs as needed
    # More playlist URLs...
]
extract_artists_from_playlists(playlist_urls)
