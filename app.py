# app.py
from flask import Flask, render_template, jsonify
import os
import json 
import time 
import re
import requests
from bs4 import BeautifulSoup
from dms2dec.dms_convert import dms2dec
import sqlite3
import requests
from datetime import datetime

app = Flask(__name__)

def parse_dms(dms_str):
    direction, dms = dms_str.split(':')
    degrees, minutes, seconds = map(float, dms.replace("'", "").replace('"', '').split())
    return (degrees, minutes, seconds, direction)

def dms_to_geo_tag(lat_dms=None, lon_dms=None):
    if not lat_dms or not lon_dms:
        return ""
    lat_dms = parse_dms(lat_dms)
    lon_dms = parse_dms(lon_dms)

    def dms_to_decimal(degrees, minutes, seconds, direction):
        decimal = degrees + minutes / 60 + seconds / 3600
        if direction in ['S', 'W']:
            decimal *= -1
        return decimal

    lat_deg, lat_min, lat_sec, lat_dir = lat_dms
    lon_deg, lon_min, lon_sec, lon_dir = lon_dms
    
    lat_decimal = dms_to_decimal(lat_deg, lat_min, lat_sec, lat_dir)
    lon_decimal = dms_to_decimal(lon_deg, lon_min, lon_sec, lon_dir)
    
    return f"{lat_decimal},{lon_decimal}"

def dms2decConversion(myValue):
    if not myValue:
        return ""
    
    dms_str = myValue.split(":")[1]  # Get the part after the colon

    # Extract degrees, minutes, and seconds
    deg, min_str, sec_str = map(str.strip, dms_str.split(" "))
    min_val = float(min_str.strip("'"))
    sec_val = float(sec_str.strip('"'))

    # Create a tuple with degrees, minutes, and seconds
    dms_tuple = (float(deg), min_val, sec_val)

    # Now let's convert to decimal degrees
    #decimal_degrees = dms2dec(dms_tuple)  # Pass the tuple as a single argument
    return dms2dec(f"{deg} {min_val}' {sec_val}\"")  # Create a formatted string 

def get_file_age(filename):
    try:
        # Get the last modified timestamp of the file
        return time.time() - os.path.getmtime(filename)
    except FileNotFoundError:
        # Handle the case when the file doesn't exist
        return 99 * 60 #Gives the illusion of a file that is 99 minutes old.


def fetch_dataDB():
    historyFileMessage = ""
    url = 'https://www.yaesu.com/jp/en/wires-x/id/active_node.php'
    
    # Connect to SQLite database
    conn = sqlite3.connect('history.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS history
                      (id INTEGER PRIMARY KEY, content TEXT, creation_time TIMESTAMP)''')
    
    # Retrieve the last inserted row
    cursor.execute('SELECT content, creation_time FROM history ORDER BY id DESC LIMIT 1')
    row = cursor.fetchone()
    
    if row:
        html_content, creation_time = row
        age_in_minutes = (datetime.now() - datetime.fromisoformat(creation_time)).total_seconds() // 60
    else:
        html_content = ""
        age_in_minutes = None

    if age_in_minutes is None or age_in_minutes > 19:  # WiresX refresh the page every 20 minutes
        response = requests.get(url)
        if response.status_code == 200:
            html_content = response.text
            historyFileMessage = "This is the latest data from yaesu.com"
            cursor.execute('INSERT INTO history (content, creation_time) VALUES (?, ?)',
                           (html_content, datetime.now()))
            conn.commit()
        else:
            historyFileMessage = f"Failed to retrieve content from {url}"
    else:
        remaining_seconds = (datetime.now() - datetime.fromisoformat(creation_time)).total_seconds() % 60
        historyFileMessage = f"This data is: {age_in_minutes:.0f} minutes and {remaining_seconds:.0f} seconds old."

    conn.close()
    
    pattern = r"dataList\[\d+\] ="
    matching_lines = [line.strip() for line in html_content.splitlines() if re.match(pattern, line)]
    
    data_list = []
    for line in matching_lines:
        matches = re.findall(r'(\w+):\"([^\"]+)\"', line)
        data_dict = dict(matches)
        data_list.append(data_dict)

    data_array = [
        {
            'dtmf_id': item.get('dtmf_id', ''),
            'call_sign': item.get('call_sign', ''),
            'ana_dig': item.get('ana_dig', ''),
            'city': item.get('city', ''),
            'state': item.get('state', ''),
            'country': item.get('country', ''),
            'freq': item.get('freq', ''),
            'sql': item.get('sql', ''),
            'lat': item.get('lat', '').replace('&quot;', '"'),
            'lon': item.get('lon', '').replace('&quot;', '"'),
            'latConverted': dms2decConversion(item.get('lat', '').replace('&quot;', '"')),
            'lonConverted': dms2decConversion(item.get('lon', '').replace('&quot;', '"')),
            'geotag': dms_to_geo_tag(item.get('lat', '').replace('&quot;', '"'), item.get('lon', '').replace('&quot;', '"')),
            'comment': item.get('comment', '')
        }
        for item in data_list
    ]
    
    return data_array, historyFileMessage     



def fetch_data():
    historyFileMessage = ""
    url = 'https://www.yaesu.com/jp/en/wires-x/id/active_node.php'
    history_file = 'history.html'
    age_in_minutes = get_file_age(history_file) / 60
    age_in_seconds = get_file_age(history_file)
    
    if age_in_seconds is not None:
        age_in_minutes = age_in_seconds // 60
        remaining_seconds = age_in_seconds % 60

    if age_in_minutes > 19:  # WiresX refresh the page every 20 minutes
        response = requests.get(url)
        if response.status_code == 200:
            with open(history_file, "w") as file:
                file.write(response.text)
                historyFileMessage = "This is the latest data from yaesu.com"
        else:
            historyFileMessage = f"Failed to retrieve content from {url}"
    else:
        historyFileMessage = f"This data is: {age_in_minutes:.0f} minutes and {remaining_seconds:.0f} seconds old."

    with open(history_file, 'r') as file:
        html_content = file.read()
        
        pattern = r"dataList\[\d+\] ="
        matching_lines = [line.strip() for line in html_content.splitlines() if re.match(pattern, line)]

        data_list = []
        for line in matching_lines:
            matches = re.findall(r'(\w+):\"([^\"]+)\"', line)
            data_dict = dict(matches)
            data_list.append(data_dict)

        data_array = [
            {
                'dtmf_id': item.get('dtmf_id', ''),
                'call_sign': item.get('call_sign', ''),
                'ana_dig': item.get('ana_dig', ''),
                'city': item.get('city', ''),
                'state': item.get('state', ''),
                'country': item.get('country', ''),
                'freq': item.get('freq', ''),
                'sql': item.get('sql', ''),
                'lat': item.get('lat', '').replace('&quot;', '"'),
                'lon': item.get('lon', '').replace('&quot;', '"'),
                'latConverted': dms2decConversion(item.get('lat', '').replace('&quot;', '"')),
                'lonConverted': dms2decConversion(item.get('lon', '').replace('&quot;', '"')),
                'geotag': dms_to_geo_tag(item.get('lat', '').replace('&quot;', '"'), item.get('lon', '').replace('&quot;', '"')),
                'comment': item.get('comment', '')
            }
            for item in data_list
        ]
    
    return data_array, historyFileMessage    

@app.route('/')
def homePage():
    data_array, historyFileMessage = fetch_dataDB()
    return render_template('index.html', data_array=data_array, historyFileMessage=historyFileMessage)

@app.route('/data')
def dataPage():
    data_array, historyFileMessage = fetch_dataDB()
    return render_template('data.html', data_array=data_array, historyFileMessage=historyFileMessage)

@app.route('/map')
def mapPage():
    data_array, historyFileMessage = fetch_dataDB()
    return render_template('map.html', data_array=data_array, historyFileMessage=historyFileMessage)

@app.route('/jsonView')
def jsonView():
    data_array, historyFileMessage = fetch_dataDB()
    json_string = json.dumps(data_array)
    return json_string

if __name__ == '__main__':
    app.run()
