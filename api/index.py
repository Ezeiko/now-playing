import base64
import json
import re
import time
from typing import Dict
from urllib.parse import quote

import flask
import requests

from utils import load_users

app = flask.Flask(__name__)
users = load_users()

CLIENT_ID = '2996cf26fcbc4ebc9c30b4b9fbe826d8'
CLIENT_SECRET = '0337d221d0474fd5982368cc3ad9d332'

AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'

BASE_URL = 'https://api.spotify.com'
API_VERSION = 'v1'
API_URL = '{}/{}'.format(BASE_URL, API_VERSION)

SERVER_URL = 'https://127.0.0.1'
PORT = 8080
# REDIRECT_URL = 'https://readme-now-playing/callback/q'
REDIRECT_URL = 'https://localhost:8080/callback/q'
SCOPES = 'user-read-playback-state user-read-currently-playing user-read-recently-played user-top-read'


def save_users(*args: Dict[str, Dict[str, str]]):
    for user in args:
        users.update(user)
    with open('users.json', 'w', encoding='utf-8') as file:
        json.dump(users, file)


@app.route('/')
def home():
    return flask.render_template('index.html')


@app.route('/login')
def login():
    auth_headers = {
        "response_type": "code",
        "redirect_uri": REDIRECT_URL,
        "scope": SCOPES,
        "client_id": CLIENT_ID
    }

    auth_headers = '&'.join(['{}={}' .format(param, quote(val))
                            for param, val in auth_headers.items()])
    auth_url = "{}/?{}".format(AUTH_URL, auth_headers)
    print(auth_url)
    return flask.redirect(auth_url)


@app.route('/callback/q')
def callback():
    auth_token = flask.request.args['code']
    code_payload = {
        "grant_type": "authorization_code",
        "code": str(auth_token),
        "redirect_uri": REDIRECT_URL,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
    }

    post_request = requests.post(TOKEN_URL, data=code_payload)

    response_data = json.loads(post_request.text)

    access_token = response_data['access_token']
    refresh_token = response_data['refresh_token']
    token_type = response_data['token_type']
    expires_in = response_data['expires_in']
    expires_at = int(time.time() + expires_in)

    auth_header = {"Authorization": "Bearer {}".format(access_token)}
    user_profile_endpoint = '{}/me'.format(API_URL)
    data = requests.get(user_profile_endpoint, headers=auth_header)
    data = json.loads(data.text)

    if not data['id'] in users:
        users[data['id']] = {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_in': expires_in,
            'expires_at': expires_at
        }
        save_users()

    return flask.render_template('success.html', page_result='Login Successful', user_id=data.get('id'))


def token_refresh(refresh_token: str):
    refresh_payload = {
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token'
    }

    headers = base64.b64encode(
        (CLIENT_ID + ":" + CLIENT_SECRET).encode("ascii"))
    headers = {"Authorization": "Basic %s" % headers.decode("ascii")}

    response = requests.post(
        TOKEN_URL,
        data=refresh_payload,
        headers=headers
    ).json()

    return response


def build_medium_card(track, output):
    image = str(base64.b64encode(requests.get(
        track['album']['images'][1]['url']).content))[2: -1]
    output = re.sub(r"{{ image }}", image, output)

    duration = str(int(track['duration_ms'] / 1000))
    output = re.sub(r"{{ duration }}", duration, output)

    animation = "unset"
    if len(track['name']) <= 20:
        font_size = "24"
    else:
        animation = "text-scroll infinite linear 20s"
        font_size = "22"
    output = re.sub(r"{{ title_animation }}", animation, output)
    output = re.sub(r"{{ title_font_size }}", font_size, output)
    output = re.sub(r"{{ title }}", track['name'], output)

    animation = "unset"
    artists = ' & '.join([artist['name'] for artist in track['artists']])
    if len(artists) <= 29:
        font_size = "16"
    else:
        animation = "text-scroll infinite linear 20s"
        font_size = "12"
    ouptut = re.sub(r"{{ artist_animation }}", animation, output)
    output = re.sub(r"{{ artist_font_size }}", font_size, output)
    output = re.sub(r"{{ artist }}", artists, output)

    animation = "unset"
    album = track['album']
    if len(album['name']) <= 28:
        subtitle = album['name'] + ' • ' + album['release_date'].split('-')[0]
        font_size = "14"
    elif len(album['name']) <= 36:
        subtitle = album['name']
        font_size = "14"
    elif len(album['name']) <= 33:
        font_size = "12"
        subtitle = album['name'] + ' • ' + album['release_date'].split('-')[0]
    elif len(album['name']) <= 40:
        font_size = "12"
        subtitle = album['name']
    else:
        font_size = "12"
        subtitle = album['name']
        animation = "text-scroll infinite linear 20s"
    output = re.sub(r"{{ sub_animation }}", animation, output)
    output = re.sub(r"{{ sub_font_size }}", font_size, output)
    output = re.sub(r"{{ subtitle }}", subtitle, output)

    return output


def build_large_card(track, output):
    image = str(base64.b64encode(requests.get(
        track['album']['images'][1]['url']).content))[2: -1]
    output = re.sub(r"{{ image }}", image, output)

    duration = str(int(track['duration_ms'] / 1000))
    output = re.sub(r"{{ duration }}", duration, output)

    output = re.sub(r"{{ title }}", track['name'], output)

    artists = ' & '.join([artist['name'] for artist in track['artists']])
    output = re.sub(r"{{ artist }}", artists, output)

    album = track['album']
    subtitle = album['name'] + ' • ' + album['release_date'].split('-')[0]
    output = re.sub(r"{{ subtitle }}", subtitle, output)

    return output

def build_small_card(track, template):
    image = str(base64.b64encode(requests.get(
        track['album']['images'][1]['url']).content))[2: -1]
    template = re.sub(r"{{ image }}", image, template)

    duration = str(int(track['duration_ms'] / 1000))
    template = re.sub(r"{{ duration }}", duration, template)

    animation = "unset"
    if len(track['name']) <= 16:
        font_size = "18"
    elif len(track['name']) <= 18:
        font_size = "16"
    else:
        font_size = "16"
        animation = "text-scroll infinite linear 20s"
    template = re.sub(r"{{ title_font_size }}", font_size, template)
    template = re.sub(r"{{ title_animation }}", animation, template)
    template = re.sub(r"{{ title }}", track['name'], template)

    animation = "unset"
    artists = ' & '.join([artist['name'] for artist in track['artists']])
    font_size = "14"
    if len(artists) > 23:
        animation = "text-scroll infinite linear 20s"
    template = re.sub(r"{{ artist_font_size }}", font_size, template)
    template = re.sub(r"{{ artist_animation }}", animation, template)
    template = re.sub(r"{{ artist }}", artists, template)

    animation = "unset"
    album = track['album']
    font_size = "12"
    if len(album['name']) <= 13:
        subtitle = album['name'] + ' • ' + album['release_date'].split('-')[0]
    elif len(album['name']) <= 20:
        subtitle = album['name']
    else:
        animation = "text-scroll infinite linear 20s"
    template = re.sub(r"{{ sub_font_size }}", font_size, template)
    template = re.sub(r"{{ sub_animation }}", animation, template)
    template = re.sub(r"{{ subtitle }}", subtitle, template)

    return template

@app.route('/now-playing/q')
def now_playing():
    params = flask.request.args

    size = params.get('size', 'med')
    if size not in ['default', 'small', 'med', 'large']:
        size = 'med'

    user_id = params.get('uid')
    if user_id not in users:
        return 'please login before usage'
    user_tokens = users.get(user_id)

    if int(time.time()) >= user_tokens['expires_at'] - 60:
        user_tokens = token_refresh(user_tokens['refresh_token'])
        user_tokens['expires_at'] = int(
            time.time()) + user_tokens['expires_in']
        users[user_id] = user_tokens

    access_token = user_tokens['access_token']
    auth_header = {"Authorization": "Bearer {}".format(access_token)}
    now_playing_endpoint = '{}/me/player/currently-playing'.format(API_URL)

    data = requests.get(now_playing_endpoint, headers=auth_header).json()

    with open(f'cards/card_{size}.svg', 'r', encoding='utf-8') as file:
        svg_template = str(file.read())

    track = data['item']
    if track is None:
        print(f":::getting recently played tracks")
        recently_played_endpoint = '{}/me/player/recently-played'.format(
            API_URL)
        data = requests.get(recently_played_endpoint,
                            headers=auth_header).json()
        # actual format of data['items'] - dict_keys(['track', 'played_at', 'context'])
        track = data['items'][0]['track']
        print(f":::track-keys: {track.keys()}")

    if size == 'large':
        return build_large_card(track, svg_template)
    elif size == 'med':
        return build_medium_card(track, svg_template)
    else:
        return build_small_card(track, svg_template)


@app.route('/users')
def get_users():
    return flask.jsonify(users)


if __name__ == '__main__':
    app.run(debug=True, host='localhost', port=PORT, ssl_context='adhoc')