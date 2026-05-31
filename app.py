# app.py
from flask import Flask, render_template, jsonify, Response
import json
import re
import requests
from dms2dec.dms_convert import dms2dec
import sqlite3
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

def fetch_remote_html(url, timeout=10):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'close'
    }
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.text, None
    except requests.exceptions.RequestException as exc:
        return None, str(exc)
    except Exception as exc:
        return None, str(exc)


def load_db_cache(cursor):
    cursor.execute('SELECT content, creation_time FROM history ORDER BY id DESC LIMIT 1')
    row = cursor.fetchone()
    if not row:
        return "", None
    return row[0], row[1]


def save_db_cache(cursor, html_content):
    cursor.execute('INSERT INTO history (content, creation_time) VALUES (?, ?)',
                   (html_content, datetime.now()))


def parse_history_html(html_content):
    pattern = r"dataList\[\d+\] ="
    matching_lines = [line.strip() for line in html_content.splitlines() if re.match(pattern, line)]

    data_list = []
    for line in matching_lines:
        matches = re.findall(r'(\w+):\"([^\"]+)\"', line)
        data_dict = dict(matches)
        data_list.append(data_dict)

    return [
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


def fetch_dataDB():
    historyFileMessage = ""
    url = 'https://www.yaesu.com/jp/en/wires-x/id/active_node.php'
    conn = sqlite3.connect('history.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS history
                      (id INTEGER PRIMARY KEY, content TEXT, creation_time TIMESTAMP)''')

    html_content, creation_time = load_db_cache(cursor)
    age_in_minutes = None
    if creation_time:
        age_in_minutes = (datetime.now() - datetime.fromisoformat(creation_time)).total_seconds() // 60

    if age_in_minutes is None or age_in_minutes > 19:
        remote_html, error = fetch_remote_html(url)
        if remote_html is not None:
            html_content = remote_html
            historyFileMessage = "This is the latest data from yaesu.com"
            save_db_cache(cursor, html_content)
            conn.commit()
        else:
            app.logger.warning("Remote data refresh failed: %s", error)
            if html_content:
                if age_in_minutes is not None:
                    historyFileMessage = f"Could not refresh data; showing cached content ({age_in_minutes:.0f} minutes old)."
                else:
                    historyFileMessage = "Could not refresh data; showing cached content."
            else:
                historyFileMessage = "Could not retrieve data from the remote service. Please try again later."
    else:
        remaining_seconds = (datetime.now() - datetime.fromisoformat(creation_time)).total_seconds() % 60
        historyFileMessage = f"This data is: {age_in_minutes:.0f} minutes and {remaining_seconds:.0f} seconds old."

    conn.close()

    if not html_content:
        return [], historyFileMessage

    return parse_history_html(html_content), historyFileMessage    

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
    payload = json.dumps(data_array, ensure_ascii=False)
    content_length = len(payload.encode('utf-8'))
    return Response(payload, mimetype='application/json', headers={'Content-Length': str(content_length)})

if __name__ == '__main__':
    app.run()