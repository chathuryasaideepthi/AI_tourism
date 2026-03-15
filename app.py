from flask import Flask, render_template, request, jsonify
import requests
from math import radians, sin, cos, sqrt, atan2

app = Flask(__name__)

API_KEY = "  # Replace with your Geoapify API key"


# ---------- UTILS ----------
def haversine(coord1, coord2):
    R = 6371
    lat1, lon1 = radians(coord1[0]), radians(coord1[1])
    lat2, lon2 = radians(coord2[0]), radians(coord2[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def nearest_neighbor(user_location, places):
    if not places:
        return []
    path, current, unvisited = [], {"lat": user_location[0], "lon": user_location[1]}, places.copy()
    while unvisited:
        next_place = min(unvisited, key=lambda x: haversine((current["lat"], current["lon"]), (x["lat"], x["lon"])))
        path.append(next_place)
        current = next_place
        unvisited.remove(next_place)
    return path


# Pricing multipliers per transport type
TRANSPORT_MULTIPLIER = {
    "car": {"price_per_km": 5, "carbon_per_km": 0.12},
    "bus": {"price_per_km": 2, "carbon_per_km": 0.05},
    "train": {"price_per_km": 1.5, "carbon_per_km": 0.04},
    "flight": {"price_per_km": 10, "carbon_per_km": 0.25},
}


def calculate_dynamic_price(distance_km, num_places, transport_type):
    base_price = 50
    multiplier = TRANSPORT_MULTIPLIER.get(transport_type, TRANSPORT_MULTIPLIER["car"])
    price = base_price + distance_km * multiplier["price_per_km"] + num_places * 20
    return round(price, 2)


def calculate_carbon_footprint(distance_km, transport_type):
    multiplier = TRANSPORT_MULTIPLIER.get(transport_type, TRANSPORT_MULTIPLIER["car"])
    return round(distance_km * multiplier["carbon_per_km"], 2)


# ---------- ROUTES ----------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/get_places", methods=["POST"])
def get_places():
    data = request.json
    lat, lon, interest = data.get("lat"), data.get("lon"), data.get("interest", "tourism.attraction")
    url = "https://api.geoapify.com/v2/places"
    params = {
        "categories": interest,
        "filter": f"circle:{lon},{lat},50000",
        "limit": 20,
        "apiKey": API_KEY
    }
    resp = requests.get(url, params=params)
    results = []
    for f in resp.json().get("features", []):
        coords = f["geometry"]["coordinates"]
        results.append({
            "name": f["properties"].get("name"),
            "lat": coords[1],
            "lon": coords[0]
        })
    return jsonify(results)


@app.route("/search_places", methods=["POST"])
def search_places():
    data = request.json
    query, interest = data.get("query"), data.get("interest", "tourism.attraction")

    geo_url = "https://api.geoapify.com/v1/geocode/search"
    geo_params = {"text": query, "apiKey": API_KEY}
    geo_resp = requests.get(geo_url, params=geo_params).json()
    if not geo_resp["features"]:
        return jsonify({"error": "Place not found"}), 404
    coords = geo_resp["features"][0]["geometry"]["coordinates"]
    lon, lat = coords[0], coords[1]

    places_url = "https://api.geoapify.com/v2/places"
    params = {"categories": interest, "filter": f"circle:{lon},{lat},50000", "limit": 20, "apiKey": API_KEY}
    resp = requests.get(places_url, params=params)
    results = []
    for f in resp.json().get("features", []):
        coords = f["geometry"]["coordinates"]
        results.append({
            "name": f["properties"].get("name"),
            "lat": coords[1],
            "lon": coords[0]
        })
    return jsonify({"user_location": [lat, lon], "places": results})


@app.route("/route", methods=["POST"])
def route():
    data = request.json
    user_location = data.get("user_location")
    selected_places = data.get("selected", [])
    transport_type = data.get("transport", "car")  # New field for transport

    ordered = nearest_neighbor(user_location, selected_places)
    path_coords = [[user_location[0], user_location[1]]] + [[p["lat"], p["lon"]] for p in ordered]
    names_order = ["Start"] + [p["name"] for p in ordered]
    total_dist = sum(haversine(path_coords[i], path_coords[i + 1]) for i in range(len(path_coords) - 1))

    price = calculate_dynamic_price(total_dist, len(selected_places), transport_type)
    carbon = calculate_carbon_footprint(total_dist, transport_type)

    return jsonify({
        "coordinates": path_coords,
        "order": names_order,
        "distance_km": round(total_dist, 2),
        "estimated_time_hr": round(total_dist / 40.0, 2),
        "dynamic_price": price,
        "carbon_footprint_kg": carbon
    })


if __name__ == "__main__":
    app.run(debug=True)
