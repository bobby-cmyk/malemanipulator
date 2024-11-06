import spotipy
from openai import OpenAI
from spotipy.oauth2 import SpotifyClientCredentials
import os
from dotenv import load_dotenv
import re
import json
from flask import Flask, request, render_template, flash, redirect
import random

# Load Spotify API credentials from environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
app.secret_key = os.getenv("APP_SECRET_KEY")

# Authenticate with Spotify API using Client Credentials Flow
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET))

load_dotenv()

client = OpenAI()

# Load the male manipulator artists with Spotify IDs from the JSON file
with open("male_manipulator_artists.json", "r") as f:
    male_manipulator_artists = json.load(f)

def get_playlist_id_from_url(url):
    """Extracts the playlist ID from a Spotify URL."""
    match = re.search(r"playlist/([a-zA-Z0-9]+)", url)
    if match:
        return match.group(1)
    else:
        raise ValueError("Invalid Spotify playlist URL")

def get_playlist_tracks(playlist_id):
    """Fetches all tracks from a public Spotify playlist."""
    try:
        results = sp.playlist_tracks(playlist_id)
    except spotipy.exceptions.SpotifyException:
        return None  # Return None if playlist ID is invalid

    tracks = results['items']
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])

    track_data = []
    for item in tracks:
        track = item.get('track')
        if track is None:
            continue
        track_info = {
            'name': track.get('name', 'Unknown Title'),
            'artist_id': track['artists'][0]['id'] if track['artists'] else None,
            'artist_name': track['artists'][0]['name'] if track['artists'] else 'Unknown Artist'
        }
        track_data.append(track_info)

    return track_data

def calculate_male_manipulator_score(tracks):
    """Calculates the male manipulator score and collects manipulator tracks based on matched artists by ID."""
    manipulator_tracks = []  # List to store manipulator track details
    manipulator_track_count = 0  # Counter for tracks by manipulator artists
    total_tracks = len(tracks)

    for track in tracks:
        artist_id = track['artist_id']
        track_name = track['name']
        artist_name = track['artist_name']
        
        if artist_id in male_manipulator_artists:
            # Track is a "Male Manipulator" match
            manipulator_track_count += 1
            manipulator_tracks.append(f"{track_name} by {artist_name}")

    # Calculate manipulator score as a percentage
    manipulator_score = round((manipulator_track_count / total_tracks) * 100) if total_tracks > 0 else 0

     # Randomly select up to 10 manipulator tracks if there are more than 10
    selected_manipulator_tracks = random.sample(manipulator_tracks, min(10, len(manipulator_tracks)))

    return manipulator_score, selected_manipulator_tracks

def get_gpt_comment(manipulator_score, manipulator_tracks):

    system_prompt = """
    You are a judgy and sassy female judging the spotify playlist of a guy. NSFW. 
    You will analyze at the male manipulator score of the playlist as well as the male manipulator tracks. 
    Give a comment to the girl interested in the guy about his playlist. 
    Be nicer if his score is low.
    Keep it under 100 words. 
    Avoid any formatting.
    """

    manipulator_tracks_string = ", ".join(manipulator_tracks)

    manipulator_tracks_with_score = f"Manipulator Score: {manipulator_score}%, " + manipulator_tracks_string

    user_prompt = manipulator_tracks_with_score

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )

    return completion.choices[0].message.content

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        playlist_url = request.form["playlist_url"]

        # Step 1: Validate URL format and extract playlist ID
        try:
            playlist_id = get_playlist_id_from_url(playlist_url)
        except ValueError as e:
            flash(str(e))  # Show error message if URL is invalid
            return redirect("/")

        # Step 2: Validate Playlist ID with Spotify API
        tracks = get_playlist_tracks(playlist_id)
        if tracks is None:
            flash("Could not retrieve playlist. Please ensure the Spotify playlist URL is correct.")
            return redirect("/")

        # Step 3: Calculate score and generate GPT comment (if playlist is valid)
        manipulator_score, manipulator_tracks = calculate_male_manipulator_score(tracks)
        comment = get_gpt_comment(manipulator_score, manipulator_tracks)

        return render_template("index.html", manipulator_score=manipulator_score, comment=comment)

    return render_template("index.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
