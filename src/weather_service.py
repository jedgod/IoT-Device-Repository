"""OpenWeather API access. Credentials and request URLs never enter UI errors."""
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
import json
import math
import socket

BASE_URL = 'https://api.openweathermap.org'

class WeatherError(Exception):
    """A safe, user-facing weather service error."""

def request_json(path, params, api_key):
    if not api_key or not api_key.strip():
        raise WeatherError('OpenWeatherMap API key is not configured.')
    query = urlencode({**params, 'appid': api_key.strip()})
    try:
        with urlopen(f'{BASE_URL}{path}?{query}', timeout=12) as response:
            result = json.load(response)
    except HTTPError as exc:
        messages = {
            401: 'OpenWeatherMap rejected the API key (401). Check that the key is copied completely, activated, and permitted for this endpoint.',
            403: 'Your OpenWeatherMap account does not have access to this endpoint (403).',
            404: 'OpenWeatherMap could not find the requested weather resource (404).',
            429: 'OpenWeatherMap request limit reached (429). Please wait before refreshing.',
        }
        raise WeatherError(messages.get(exc.code, f'OpenWeatherMap is unavailable (HTTP {exc.code}). Try again later.')) from None
    except (URLError, TimeoutError, socket.timeout, OSError):
        raise WeatherError('Unable to reach OpenWeatherMap. Check your internet connection and try again.') from None
    except (ValueError, UnicodeError):
        raise WeatherError('OpenWeatherMap returned an unreadable response. Try again later.') from None
    return result

def search_locations(query, api_key):
    if not query.strip():
        return []
    result = request_json('/geo/1.0/direct', {'q':query.strip(), 'limit':5}, api_key)
    if not isinstance(result, list):
        raise WeatherError('OpenWeatherMap returned an unexpected location response.')
    return [r for r in result if isinstance(r,dict) and all(k in r for k in ('name','lat','lon','country'))]

def location_label(location):
    return ', '.join(str(location[k]) for k in ('name','state','country') if location.get(k))

def weather_at(latitude, longitude, api_key, forecast=False):
    if not (math.isfinite(latitude) and math.isfinite(longitude) and -90<=latitude<=90 and -180<=longitude<=180):
        raise WeatherError('The selected location has invalid coordinates.')
    result=request_json('/data/2.5/forecast' if forecast else '/data/2.5/weather', {'lat':latitude,'lon':longitude,'units':'metric'},api_key)
    if not isinstance(result,dict):
        raise WeatherError('OpenWeatherMap returned an unexpected weather response.')
    required=('list','city') if forecast else ('main','dt')
    if any(k not in result for k in required):
        raise WeatherError('OpenWeatherMap returned incomplete weather data.')
    if forecast and (not isinstance(result['list'],list) or not isinstance(result['city'],dict)):
        raise WeatherError('OpenWeatherMap returned an unexpected forecast response.')
    if not forecast and (not isinstance(result['main'],dict) or not all(k in result['main'] for k in ('temp','humidity'))):
        raise WeatherError('OpenWeatherMap returned incomplete current conditions.')
    return result

def local_time(timestamp, offset=0):
    return datetime.fromtimestamp(timestamp,timezone(timedelta(seconds=offset)))

def forecast_records(payload):
    """Metric units, location-local timestamps, and true three-hour intervals."""
    offset=payload.get('city',{}).get('timezone',0)
    records=[]
    for item in payload.get('list',[]):
        try:
            main=item['main']
            records.append({
                'Time':local_time(item['dt'],offset).replace(tzinfo=None),
                'Temperature (°C)':float(main['temp']),
                'Humidity (%)':float(main['humidity']),
                'Wind (m/s)':float(item.get('wind',{}).get('speed',0)),
                'Rain probability (%)':round(float(item.get('pop',0))*100),
                'Rain (mm / 3h)':float(item.get('rain',{}).get('3h',0)),
                'Conditions':(item.get('weather') or [{}])[0].get('description','Unavailable'),
            })
        except (KeyError,TypeError,ValueError,OverflowError):
            raise WeatherError('OpenWeatherMap returned incomplete forecast intervals.') from None
    return records
