#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""Generates energy consumption JSON files from Enedis (ERDF) consumption data
collected via their  website (API).
"""

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import base64
import requests
import pickle
import os
import json

LOGIN_BASE_URI = 'https://espace-client-connexion.enedis.fr'
API_BASE_URI = 'https://espace-client-particuliers.enedis.fr/group/espace-particuliers'

API_ENDPOINT_LOGIN = '/auth/UI/Login'
API_ENDPOINT_HOME = '/accueil'
API_ENDPOINT_DATA = '/suivi-de-consommation'

DATA_NOT_REQUESTED = -1
DATA_NOT_AVAILABLE = -2

COOKIE_FILE_1 = './cookie1'
COOKIE_FILE_2 = './cookie2'

class LinkyLoginException(Exception):
    # Thrown if an error was encountered while retrieving energy consumption data.
    pass

def save_cookies(requests_cookiejar, filename):
    with open(filename, 'wb') as f:
        pickle.dump(requests_cookiejar, f)

def load_cookies(filename):
    with open(filename, 'rb') as f:
        return pickle.load(f)

def get_cookies():
    cookie1 = load_cookies(COOKIE_FILE_1)
    cookie2 = load_cookies(COOKIE_FILE_2)

    return {'iPlanetDirectoryPro': cookie1, 'JSESSIONID': cookie2}

def login(username, password):
    # Try to load cookie from file
    if os.path.isfile(COOKIE_FILE_1):
        return get_cookies()

    # Login the user into the Linky API.
    payload = {'IDToken1': username,
               'IDToken2': password,
               'SunQueryParamsString': base64.b64encode(b'realm=particuliers'),
               'encoded': 'true',
               'gx_charset': 'UTF-8'}

    req = requests.post(LOGIN_BASE_URI + API_ENDPOINT_LOGIN, data=payload, allow_redirects=False)
    session_cookie = req.cookies.get('iPlanetDirectoryPro')

    if session_cookie is None:
        raise LinkyLoginException("Login unsuccessful. Check your credentials.")

    # Get second cookie
    req = requests.get(API_BASE_URI + API_ENDPOINT_HOME, cookies={'iPlanetDirectoryPro': session_cookie}, allow_redirects=False)
    session_cookie2 = req.cookies.get('JSESSIONID')

    # Store cookies inside file
    save_cookies(session_cookie, COOKIE_FILE_1)
    save_cookies(session_cookie2, COOKIE_FILE_2)

    return get_cookies()


def get_data_per_hour(token, start_date, end_date):
    """Retreives hourly energy consumption data."""
    return _get_data(token, 'urlCdcHeure', start_date, end_date)


def get_data_per_day(token, start_date, end_date):
    """Retreives daily energy consumption data."""
    return _get_data(token, 'urlCdcJour', start_date, end_date)


def get_data_per_month(token, start_date, end_date):
    """Retreives monthly energy consumption data."""
    return _get_data(token, 'urlCdcMois', start_date, end_date)


def get_data_per_year(token):
    """Retreives yearly energy consumption data."""
    return _get_data(token, 'urlCdcAn')


def _get_data(token, resource_id, start_date=None, end_date=None):
    id = 'lincspartdisplaycdc_WAR_lincspartcdcportlet'
    prefix = '_' + id + '_'

    # We send the session token so that the server knows who we are
    cookies = {
        'iPlanetDirectoryPro': token['iPlanetDirectoryPro'],
        'JSESSIONID': token['JSESSIONID']
    }

    payload = {
        prefix + 'dateDebut': start_date,
        prefix + 'dateFin': end_date
    }

    params = {
        'p_p_id': id,
        'p_p_lifecycle': 2,
        'p_p_state': 'normal',
        'p_p_mode': 'view',
        'p_p_resource_id': resource_id,
        'p_p_cacheability': 'cacheLevelPage',
        'p_p_col_id': 'column-1',
        'p_p_col_pos': 1,
        'p_p_col_count': 3
    }

    req = requests.post(API_BASE_URI + API_ENDPOINT_DATA, allow_redirects=False, cookies=cookies, data=payload,
                        params=params)

    if req.status_code != 200:
        os.remove(COOKIE_FILE_1)
        os.remove(COOKIE_FILE_2)
        return None

    return json.loads(req.text)
