# https://leaflet-extras.github.io/leaflet-providers/preview/

import os


CARTO_API_KEY = os.getenv('CARTO_API_KEY')

CartoVoyager=dict(
    url='https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png?key='+CARTO_API_KEY,
    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>, &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains='abcd'
)

CartoPositron=dict(
    url='https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png?key='+CARTO_API_KEY,
    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>, &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains='abcd'
)

CartoDarkMatter=dict(
    url='https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png?key='+CARTO_API_KEY,
    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>, &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains='abcd'
)

OpenStreet=dict(
    url='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
)

WikimediaMaps=dict(
    url='https://maps.wikimedia.org/osm-intl/{z}/{x}/{y}.png',
    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
)

GoogleMaps=dict(
    url='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', 
    attribution='&copy; Google'
)


