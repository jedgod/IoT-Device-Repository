"""Shared chart preparation; never changes the repository or exported rows."""
import numpy as np
import pandas as pd


def prepare_chart_data(frame, fields, average=False):
    """Average each reporting zone within UTC five-minute bins, then weight zones equally."""
    data = frame.copy().sort_values('time')
    if average:
        data['time'] = data.time.dt.floor('5min')
        aggregation = {field: 'mean' for field in fields}
        aggregation['alert_flag'] = 'max'
        data = data.groupby(['time', 'zone_id'], as_index=False).agg(aggregation)
        data = data.groupby('time', as_index=False).agg(aggregation)
        data['zone_id'] = 'average'
    return data


def metric_chart_data(frame, field, budget=4000):
    """Keep valid metric values and mark real gaps before sampling for display."""
    data = frame.dropna(subset=[field]).sort_values(['zone_id', 'time']).copy()
    if data.empty:
        return data
    gaps = data.groupby('zone_id').time.diff().gt(pd.Timedelta(minutes=20))
    data['gap_group'] = gaps.groupby(data.zone_id).cumsum()
    data['series'] = data.zone_id.astype(str) + '-' + data.gap_group.astype(str)
    data['time_utc'] = data.time.dt.tz_convert('UTC').dt.strftime('%Y-%m-%d %H:%M:%S')
    if len(data) > budget:
        # Stratify by zone, retaining both endpoints. Series IDs preserve gaps.
        per_zone = max(2, budget // data.zone_id.nunique())
        data = pd.concat([
            group.iloc[np.linspace(0, len(group)-1, min(len(group), per_zone), dtype=int)]
            for _, group in data.groupby('zone_id')
        ])
    return data
