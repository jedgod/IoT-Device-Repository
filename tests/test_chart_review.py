from pathlib import Path
import sys
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from dashboard_charts import prepare_chart_data, metric_chart_data


def test_average_aligns_async_zones_without_weighting_fast_publishers():
    data = pd.DataFrame({'time': pd.to_datetime(['2026-09-22T12:00:01Z', '2026-09-22T12:00:02Z', '2026-09-22T12:02:03Z']),
                         'zone_id': ['a', 'a', 'b'], 'temperature_c': [10., 10., 30.], 'alert_flag': [0, 0, 1]})
    result = prepare_chart_data(data, ['temperature_c'], average=True)
    assert len(result) == 1
    assert result.iloc[0].temperature_c == 20
    assert result.iloc[0].alert_flag == 1


def test_missing_metric_does_not_hide_other_measurement():
    data = pd.DataFrame({'time': pd.date_range('2026-09-22', periods=2, freq='min', tz='UTC'),
                         'zone_id': ['a', 'a'], 'temperature_c': [20., 21.], 'humidity_pct': [None, 70.]})
    assert len(metric_chart_data(data, 'temperature_c')) == 2
    assert len(metric_chart_data(data, 'humidity_pct')) == 1


def test_sampling_preserves_endpoints_and_real_gap_segments():
    times = pd.date_range('2026-09-22', periods=5000, freq='s', tz='UTC').append(pd.date_range('2026-09-23', periods=2, freq='s', tz='UTC'))
    data = pd.DataFrame({'time': times, 'zone_id': 'a', 'temperature_c': 20.})
    result = metric_chart_data(data, 'temperature_c')
    assert len(result) <= 4000
    assert result.time.min() == times.min() and result.time.max() == times.max()
    assert result.series.nunique() == 2


def test_overview_large_history_and_analytics_specs():
    from dashboard_overview import reference_chart
    from dashboard_live import chart
    times = pd.date_range('2026-08-01', periods=4100, freq='5min', tz='UTC')
    data = pd.DataFrame({'time': times, 'zone_id': 'a', 'zone': 'Zone A', 'temperature_c': 20., 'humidity_pct': 70., 'alert_flag': 0})
    snapshot = {'zones': pd.DataFrame()}
    with patch('streamlit.altair_chart') as output, patch('streamlit.caption'):
        reference_chart(data, 'Temperature & Humidity', snapshot, data.tail(1))
        spec = output.call_args.args[0].to_dict()
        assert spec['resolve']['scale']['y'] == 'independent'
        for view in ['Compare zones', 'Overall average']:
            chart(data, 'Temperature & Humidity', view)
            spec = output.call_args.args[0].to_dict()
            assert spec['layer'][0]['encoding']['x']['title'] == 'Time (UTC)'
            assert spec['layer'][1]['encoding']['y']['axis']['orient'] == 'right'


def test_analytics_reset_after_changing_filters():
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / 'src/dashboard.py', default_timeout=30).run()
    app.switch_page('dashboard_pages/analytics.py').run()
    app.selectbox(key='analytics_window').select('All stored data').run()
    app.selectbox(key='analytics_metric').select('Light').run()
    app.button(key='analytics_reset').click().run()
    assert not app.exception
    assert app.selectbox(key='analytics_window').value == 'Last 24 hours'
    assert app.selectbox(key='analytics_metric').value == 'Temperature & Humidity'
