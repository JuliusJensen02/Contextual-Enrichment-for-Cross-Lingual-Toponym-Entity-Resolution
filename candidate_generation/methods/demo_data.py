"""Tiny semi-structured toponym demo (A = historical gazetteer, B = modern gazetteer)."""
A = [
    {"id": "a1", "name": "Constantinople", "alt": ["Konstantiniyye"], "geo": {"lat": 41.0, "lon": 28.98}, "country": "Turkey"},
    {"id": "a2", "name": "Baghdad", "alt": ["Bagdad"], "geo": {"lat": 33.31, "lon": 44.37}, "country": "Iraq"},
    {"id": "a3", "name": "Alexandria", "alt": [], "geo": {"lat": 31.2, "lon": 29.92}, "country": "Egypt"},
    {"id": "a4", "name": "Antioch", "alt": ["Antakya"], "geo": {"lat": 36.2, "lon": 36.16}, "country": "Turkey"},
    {"id": "a5", "name": "Damascus", "alt": ["Dimashq"], "geo": {"lat": 33.51, "lon": 36.29}, "country": "Syria"},
    {"id": "a6", "name": "York", "alt": [], "geo": {"lat": 53.96, "lon": -1.08}, "country": "England"},
]
B = [
    {"id": "b1", "name": "Istanbul", "alt": ["Konstantinopel", "Constantinople"], "geo": {"lat": 41.01, "lon": 28.97}, "country": "Turkey"},
    {"id": "b2", "name": "Bagdad", "alt": ["Baghdād"], "geo": {"lat": 33.3, "lon": 44.4}, "country": "Iraq"},
    {"id": "b3", "name": "Alexandrie", "alt": ["Al-Iskandariyah"], "geo": {"lat": 31.2, "lon": 29.9}, "country": "Egypt"},
    {"id": "b4", "name": "Antakya", "alt": ["Antioche"], "geo": {"lat": 36.2, "lon": 36.17}, "country": "Turkey"},
    {"id": "b5", "name": "Dimashq", "alt": ["Damas"], "geo": {"lat": 33.5, "lon": 36.3}, "country": "Syria"},
    {"id": "b6", "name": "Cairo", "alt": ["Al-Qahira"], "geo": {"lat": 30.04, "lon": 31.24}, "country": "Egypt"},
    {"id": "b7", "name": "New York", "alt": [], "geo": {"lat": 40.7, "lon": -74.0}, "country": "USA"},
]
GOLD = [("a1", "b1"), ("a2", "b2"), ("a3", "b3"), ("a4", "b4"), ("a5", "b5")]
