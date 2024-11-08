import spotipy
from openai import OpenAI
from spotipy.oauth2 import SpotifyClientCredentials
import os
from dotenv import load_dotenv
import re
import json
from flask import Flask, request, render_template, flash, redirect
import random
import requests
import time

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Get credentials and API keys from environment
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
app.secret_key = os.getenv("APP_SECRET_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")
RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY")
RECAPTCHA_SITE_KEY = os.getenv("RECAPTCHA_SITE_KEY")

# Debugging: Check that the API keys are loading correctly
print("SPOTIFY_CLIENT_ID:", SPOTIFY_CLIENT_ID)
print("SPOTIFY_CLIENT_SECRET:", "Loaded" if SPOTIFY_CLIENT_SECRET else "Missing")
print("APP_SECRET_KEY:", "Loaded" if app.secret_key else "Missing")
print("OPENAI_API_KEY:", "Loaded" if openai_api_key else "Missing")

# Authenticate with Spotify API
try:
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET))
    print("Successfully authenticated to spotify")
except Exception as e:
    print("Error initializing Spotify client:", e)

# Authenticate with OpenAI
try:
    client = OpenAI(api_key=openai_api_key)
    print("Successfully authenticated to openai")
except Exception as e:
    print("Error initializing OpenAI client:", e)

# Load male manipulator artists from JSON file
try:
    with open("male_manipulator_artists.json", "r") as f:
        male_manipulator_artists = json.load(f)
        print("Loaded male manipulator artists")
except FileNotFoundError:
    print("male_manipulator_artists.json file not found.")
    male_manipulator_artists = {}

# Define utility functions
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
        print("Received back playlist tracks")
    except spotipy.exceptions.SpotifyException as e:
        print(f"Error fetching playlist: {e}")
        return None  # Return None if playlist ID is invalid

    tracks = results['items']
    while results['next']:
        time.sleep(0.1)  # Rate limiting
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
    manipulator_tracks = []
    manipulator_track_count = 0
    total_tracks = len(tracks)

    for track in tracks:
        artist_id = track['artist_id']
        track_name = track['name']
        artist_name = track['artist_name']
        
        if artist_id in male_manipulator_artists:
            manipulator_track_count += 1
            manipulator_tracks.append(f"{track_name} by {artist_name}")

    manipulator_score = round((manipulator_track_count / total_tracks) * 100) if total_tracks > 0 else 0
    selected_manipulator_tracks = random.sample(manipulator_tracks, min(10, len(manipulator_tracks)))

    return manipulator_score, selected_manipulator_tracks

def get_gpt_comment(manipulator_score, manipulator_tracks):
    """Generates a comment from OpenAI GPT based on the score and track list."""
    system_prompt = """
    You are a judgy and sassy female judging the spotify playlist of a guy. 
    You will analyze at the male manipulator score of the playlist as well as the male manipulator tracks. 
    Give a comment to the girl interested in the guy about his playlist. 
    Keep it under 100 words. 
    Avoid any formatting.
    """

    manipulator_tracks_string = ", ".join(manipulator_tracks)
    user_prompt = f"Manipulator Score: {manipulator_score}%, " + manipulator_tracks_string

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        print("Received back gpt completion")
        return completion.choices[0].message.content
    except Exception as e:
        print("Error generating GPT comment:", e)
        return "Error generating comment. Please try again."

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":

        # Print the entire form data
        print("Form data received:", request.form)

        recaptcha_response = request.form.get("g-recaptcha-response")

        if not recaptcha_response:
            flash("CAPTCHA token missing. Please try again.")
            return redirect("/")

        verification_response = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={
                "secret": RECAPTCHA_SECRET_KEY,
                "response": recaptcha_response
            }
        )
        result = verification_response.json()
        print("Verification result:", result)

        if not result.get("success"):
            flash("CAPTCHA validation failed. Please try again.")
            return redirect("/")

        if result.get("action") != "submit" or result.get("score", 0) < 0.5:
            flash("CAPTCHA validation failed due to action mismatch or low score.")
            return redirect("/")
        
        playlist_url = request.form.get("playlist_url")

        # Step 1: Validate URL format and extract playlist ID
        try:
            playlist_id = get_playlist_id_from_url(playlist_url)
        except ValueError as e:
            flash(str(e))
            return redirect("/")

        # Step 2: Validate Playlist ID with Spotify API
        tracks = get_playlist_tracks(playlist_id)
        if tracks is None:
            flash("Could not retrieve playlist. Please ensure the Spotify playlist URL is correct.")
            return redirect("/")

        # Step 3: Calculate score and generate GPT comment (if playlist is valid)
        manipulator_score, manipulator_tracks = calculate_male_manipulator_score(tracks)
        comment = get_gpt_comment(manipulator_score, manipulator_tracks)

        return render_template("index.html", manipulator_score=manipulator_score, comment=comment, recaptcha_site_key=RECAPTCHA_SITE_KEY)

    return render_template("index.html", recaptcha_site_key=RECAPTCHA_SITE_KEY)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 12345))
    app.run(host="0.0.0.0", port=port)
