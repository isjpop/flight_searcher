"""Starting destination list. Edit it from the UI; this only seeds an empty database.

Regions drive which airlines are crawled for a destination (Southwest, for example,
only flies within the Americas), so keep them accurate when adding airports.
"""
from __future__ import annotations

REGIONS = (
    "domestic",
    "canada",
    "mexico_caribbean",
    "central_america",
    "south_america",
    "europe",
    "asia",
    "oceania",
    "middle_east_africa",
)

# (code, city, country, region, enabled)
DEFAULT_DESTINATIONS: list[tuple[str, str, str, str, bool]] = [
    # Domestic
    ("JFK", "New York", "United States", "domestic", True),
    ("BOS", "Boston", "United States", "domestic", True),
    ("DCA", "Washington", "United States", "domestic", True),
    ("ORD", "Chicago", "United States", "domestic", True),
    ("DEN", "Denver", "United States", "domestic", True),
    ("LAX", "Los Angeles", "United States", "domestic", True),
    ("SFO", "San Francisco", "United States", "domestic", True),
    ("SAN", "San Diego", "United States", "domestic", True),
    ("SEA", "Seattle", "United States", "domestic", True),
    ("LAS", "Las Vegas", "United States", "domestic", True),
    ("MIA", "Miami", "United States", "domestic", True),
    ("MCO", "Orlando", "United States", "domestic", True),
    ("MSY", "New Orleans", "United States", "domestic", True),
    ("HNL", "Honolulu", "United States", "domestic", True),
    ("PDX", "Portland", "United States", "domestic", False),
    ("SLC", "Salt Lake City", "United States", "domestic", False),
    # Canada
    ("YYZ", "Toronto", "Canada", "canada", True),
    ("YUL", "Montreal", "Canada", "canada", True),
    ("YVR", "Vancouver", "Canada", "canada", True),
    # Mexico & Caribbean
    ("CUN", "Cancun", "Mexico", "mexico_caribbean", True),
    ("SJD", "Los Cabos", "Mexico", "mexico_caribbean", True),
    ("PVR", "Puerto Vallarta", "Mexico", "mexico_caribbean", True),
    ("MEX", "Mexico City", "Mexico", "mexico_caribbean", True),
    ("SJU", "San Juan", "Puerto Rico", "mexico_caribbean", True),
    ("MBJ", "Montego Bay", "Jamaica", "mexico_caribbean", False),
    ("PUJ", "Punta Cana", "Dominican Republic", "mexico_caribbean", False),
    # Central America
    ("SJO", "San Jose", "Costa Rica", "central_america", True),
    ("LIR", "Liberia", "Costa Rica", "central_america", False),
    ("BZE", "Belize City", "Belize", "central_america", False),
    # South America
    ("BOG", "Bogota", "Colombia", "south_america", True),
    ("LIM", "Lima", "Peru", "south_america", True),
    ("GRU", "Sao Paulo", "Brazil", "south_america", False),
    ("EZE", "Buenos Aires", "Argentina", "south_america", False),
    # Europe
    ("LHR", "London", "United Kingdom", "europe", True),
    ("CDG", "Paris", "France", "europe", True),
    ("FCO", "Rome", "Italy", "europe", True),
    ("BCN", "Barcelona", "Spain", "europe", True),
    ("MAD", "Madrid", "Spain", "europe", True),
    ("LIS", "Lisbon", "Portugal", "europe", True),
    ("AMS", "Amsterdam", "Netherlands", "europe", True),
    ("FRA", "Frankfurt", "Germany", "europe", True),
    ("MUC", "Munich", "Germany", "europe", False),
    ("DUB", "Dublin", "Ireland", "europe", True),
    ("ATH", "Athens", "Greece", "europe", False),
    # Asia
    ("NRT", "Tokyo", "Japan", "asia", True),
    ("ICN", "Seoul", "South Korea", "asia", True),
    ("SIN", "Singapore", "Singapore", "asia", False),
    # Oceania
    ("SYD", "Sydney", "Australia", "oceania", False),
    ("AKL", "Auckland", "New Zealand", "oceania", False),
    # Middle East & Africa
    ("DXB", "Dubai", "United Arab Emirates", "middle_east_africa", False),
    ("CPT", "Cape Town", "South Africa", "middle_east_africa", False),
]
