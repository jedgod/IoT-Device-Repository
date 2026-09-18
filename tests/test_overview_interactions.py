"""Exercise the reference overview without touching production telemetry."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from streamlit.testing.v1 import AppTest
from dashboard_demo import reference_history, filter_history
APP=Path(__file__).resolve().parents[1]/'src/dashboard.py'

def test_reference_filter_windows_and_zone_isolation():
    data=reference_history()
    day=filter_history(data,'Tomato zone','Last 24 hours')
    week=filter_history(data,'All zones','Last 7 days')
    assert len(day)==96
    assert set(day.zone)=={'Tomato zone'}
    assert len(week)==7*96*3
    assert len(filter_history(data,'All zones','Last 30 days'))==30*96*3

def test_overview_filters_dismissal_and_simulated_irrigation():
    app=AppTest.from_file(APP,default_timeout=30).run()
    assert not app.exception
    app.selectbox(key='overview_zone').select('Lettuce zone').run()
    assert not app.exception
    assert not any(b.label=='View zone' for b in app.button)
    app.selectbox(key='overview_window').select('Last 7 days').run()
    app.selectbox(key='trend_metric').select('Soil moisture').run()
    assert not app.exception
    app.selectbox(key='irrigation_zone').select('Lettuce zone').run()
    assert app.button(key='start_irrigation').disabled
    app.selectbox(key='irrigation_zone').select('Tomato zone').run()
    app.selectbox(key='irrigation_duration').select(15).run()
    app.button(key='start_irrigation').click().run()
    assert app.session_state.demo_irrigations[0]['minutes']==15
    assert app.session_state.demo_irrigations[0]['zone']=='Tomato zone'
    app.selectbox(key='overview_zone').select('All zones').run()
    app.button(key='dismiss_alert').click().run()
    assert app.session_state.dismissed_soil_alert
    assert not app.exception

def test_all_navigation_pages_render():
    app=AppTest.from_file(APP,default_timeout=30).run()
    for page in ['zones','analytics','forecast','controls','data_explorer']:
        app.switch_page(f'dashboard_pages/{page}.py').run()
        assert not app.exception, page
