from pathlib import Path
import sys
from urllib.error import HTTPError
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import weather_service as weather
from streamlit.testing.v1 import AppTest

CURRENT = {'main': {'temp': 21.5, 'humidity': 67}, 'dt': 1700000000,
           'timezone': 7200, 'wind': {'speed': 3.2}, 'weather': [{'description': 'clear sky'}]}
FORECAST = {'city': {'timezone': 7200}, 'list': [
    {'dt': 1700000000 + i * 10800, 'main': {'temp': 20 + i, 'humidity': 65},
     'pop': 0.42, 'rain': {'3h': 1.2}, 'wind': {'speed': 2.1}} for i in range(3)]}

def test_credentials_never_appear_in_errors(monkeypatch):
    def reject(*args, **kwargs):
        raise HTTPError('https://example.test?appid=secret-test-key', 401, 'rejected', {}, None)
    monkeypatch.setattr(weather, 'urlopen', reject)
    with pytest.raises(weather.WeatherError) as error:
        weather.weather_at(0, 0, 'secret-test-key')
    assert '401' in str(error.value)
    assert 'secret-test-key' not in str(error.value)

def test_forecast_units_and_local_time():
    rows = weather.forecast_records(FORECAST)
    assert rows[0]['Rain probability (%)'] == 42
    assert rows[0]['Rain (mm / 3h)'] == 1.2
    assert rows[0]['Temperature (°C)'] == 20
    assert rows[0]['Time'].hour == 0
    assert (rows[1]['Time'] - rows[0]['Time']).total_seconds() == 10800

def test_weather_ui_and_partial_failure(monkeypatch):
    monkeypatch.setenv('OPENWEATHER_API_KEY', 'test-weather-key')
    monkeypatch.setattr(weather, 'search_locations', lambda *a: [{'name': 'Test City', 'country': 'GB', 'lat': 1., 'lon': 2.}])
    monkeypatch.setattr(weather, 'weather_at', lambda *a, forecast=False: FORECAST if forecast else CURRENT)
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / 'src/dashboard.py', default_timeout=30).run()
    app.switch_page('dashboard_pages/forecast.py').run()
    app.text_input(key='weather_query').set_value('Test City, GB')
    next(b for b in app.button if b.label == 'Find location').click().run()
    assert not app.exception
    assert app.metric[0].value == '21.5 °C'
    assert len(app.dataframe[0].value) == 3
    def unavailable(*a, forecast=False):
        if forecast:
            raise weather.WeatherError('Forecast temporarily unavailable')
        return CURRENT
    monkeypatch.setattr(weather, 'weather_at', unavailable)
    next(b for b in app.button if b.label == 'Refresh weather').click().run()
    assert not app.exception
    assert app.metric[0].value == '21.5 °C'
    assert any('temporarily unavailable' in w.value for w in app.warning)
