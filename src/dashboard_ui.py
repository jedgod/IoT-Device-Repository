"""Shared presentation primitives for the greenhouse dashboard."""
from pathlib import Path
from functools import lru_cache
import base64
from html import escape

ASSETS = Path(__file__).parent / 'assets'

def svg_image(svg, css_class='ui-icon'):
    data = base64.b64encode(svg.encode()).decode()
    return f'<img class="{css_class}" src="data:image/svg+xml;base64,{data}" alt="" aria-hidden="true">'

def icon(name, color=None):
    paths = {
        'leaf': '<path d="M20 3C8 3 3 8 5 16c7 4 15-1 15-13Z" fill="currentColor" stroke="none"/><path d="M3 22C5 15 11 11 16 7"/>',
        'temperature': '<path d="M9 14.5V5a3 3 0 0 1 6 0v9.5a5 5 0 1 1-6 0Z"/><path d="M12 7v11"/><circle cx="12" cy="18" r="2" fill="currentColor"/>',
        'water': '<path d="M12 2C9 7 4 12 4 16a8 8 0 0 0 16 0c0-4-5-9-8-14Z" fill="currentColor" stroke="none"/><path d="M16 15c1 3-1 5-3 5" stroke="white" stroke-width="1.3"/>',
        'plant': '<path d="M12 21V9M12 14C4 15 2 10 3 6c6-1 9 3 9 8ZM12 10c0-7 5-8 9-8 0 6-3 9-9 8Z" fill="currentColor"/><path d="M8 21h8l2 2H6Z" fill="currentColor"/>',
        'bell': '<path d="M5 17h14l-2-3V9a5 5 0 0 0-10 0v5Z" fill="currentColor"/><path d="M10 21h4M12 2v2"/>',
        'warning': '<path d="M10 3a2 2 0 0 1 4 0l9 17a2 2 0 0 1-2 3H3a2 2 0 0 1-2-3Z" fill="currentColor" stroke="none"/><path d="M12 8v7" stroke="white"/><circle cx="12" cy="19" r="1" fill="white" stroke="none"/>',
    }
    color = color or {'leaf':'#158047','temperature':'#d92218','water':'#1265d5','plant':'#168052','bell':'#e52c42','warning':'#eda400'}[name]
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 26" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{paths[name].replace("currentColor", color)}</svg>'
    return svg_image(svg)

@lru_cache(maxsize=8)
def crop_image(name):
    for extension, media_type in (('jpg', 'image/jpeg'), ('svg', 'image/svg+xml')):
        asset = ASSETS / f'{name}.{extension}'
        if asset.exists():
            return f'data:{media_type};base64,' + base64.b64encode(asset.read_bytes()).decode()
    return 'data:image/jpeg;base64,' + base64.b64encode((ASSETS/'seedling.jpg').read_bytes()).decode()

def sparkline(values, color, key):
    low, high = min(values), max(values)
    points = ' '.join(f'{i*84/(len(values)-1):.1f},{30-(v-low)/max(high-low,.01)*23:.1f}' for i,v in enumerate(values))
    return svg_image(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 85 38"><defs><linearGradient id="{key}" x1="0" y1="0" x2="0" y2="1"><stop stop-color="{color}" stop-opacity=".25"/><stop offset="1" stop-color="{color}" stop-opacity="0"/></linearGradient></defs><polygon points="0,38 {points} 84,38" fill="url(#{key})"/><polyline points="{points}" fill="none" stroke="{color}" stroke-width="1.8"/></svg>', 'sparkline')

def metric_card(label,value,delta,kind,values,note=None):
    color,bg = {'temperature':('#db160f','#fff4e8'),'water':('#075dcc','#e6f2ff'),'leaf':('#08773c','#e3f4ec'),'bell':('#e52c42','#ffecef')}[kind]
    note = note or ('vs. previous period' if kind != 'bell' else 'in selected period')
    delta_html = f'<div class="metric-delta">{escape(delta)}</div>' if kind!='bell' else f'<div class="metric-note">{escape(delta)}</div>'
    return f'<div class="metric-card {"alerts" if kind=="bell" else ""}"><div class="metric-icon" style="background:{bg};color:{color}">{icon(kind)}</div><div><div class="metric-label">{escape(label)}</div><div class="metric-value">{escape(value)}</div>{delta_html}<div class="metric-note">{note}</div></div>{sparkline(values,color if kind in ("bell","water") else "#08773c",kind)}</div>'

def zone_card(z):
    attention = z['soil'] < z['target']
    status = 'Attention' if attention else 'Healthy'
    return f'<div class="zone-row"><img src="{crop_image(z["image"])}" alt="{escape(z["name"])} crop"><div><div class="zone-name">{escape(z["name"])}</div><div class="zone-status {"attention" if attention else ""}"><span class="dot"></span>{status}</div></div><div class="zone-values"><span>{icon("temperature", "#7b879c")}{z["temperature"]:.1f}°C</span><span class="water">{icon("water", "#719fde")}{z["humidity"]:.0f}%</span><span class="plant">{icon("plant", "#66a37e")}{z["soil"]:.0f}%</span></div><span class="zone-chevron">›</span></div>'
