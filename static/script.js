let userLocation = null;
let places = [];

const map = L.map('map').setView([20.5937, 78.9629], 5);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(map);

function useLocation() {
  navigator.geolocation.getCurrentPosition(pos => {
    userLocation = [pos.coords.latitude, pos.coords.longitude];
    fetchPlaces(userLocation);
  });
}

function fetchPlaces(location) {
  const interest = document.getElementById("interest").value;
  fetch("/get_places", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({lat: location[0], lon: location[1], interest: interest})
  })
  .then(r => r.json())
  .then(data => {
    places = data;
    renderPlaces();
  });
}

function searchByText() {
  const query = document.getElementById("placeQuery").value;
  const interest = document.getElementById("interest").value;
  fetch("/search_places", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({query: query, interest: interest})
  })
  .then(r => r.json())
  .then(data => {
    userLocation = data.user_location;
    places = data.places;
    renderPlaces();
  });
}

function renderPlaces() {
  const container = document.getElementById("placesList");
  container.innerHTML = "";
  places.forEach((p, i) => {
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.value = i;
    container.appendChild(cb);
    container.appendChild(document.createTextNode(p.name));
    container.appendChild(document.createElement("br"));
  });
}

function getRoute() {
  const selected = [...document.querySelectorAll("#placesList input:checked")]
                  .map(cb => places[cb.value]);
  const transport = document.getElementById("transport").value;

  fetch("/route", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({user_location: userLocation, selected: selected, transport: transport})
  })
  .then(r => r.json())
  .then(data => {
    map.setView(userLocation, 12);
    L.marker(userLocation).addTo(map).bindPopup("Start");

    let latlngs = [userLocation];
    for (let i=1; i<data.coordinates.length; i++) {
      const coord = data.coordinates[i];
      latlngs.push(coord);
      L.marker(coord).addTo(map).bindPopup(data.order[i]);
    }
    L.polyline(latlngs, {color:"blue"}).addTo(map);

    // Show info in a div instead of alert
    const info = `
      <b>Order:</b> ${data.order.join(" → ")}<br>
      <b>Distance:</b> ${data.distance_km} km<br>
      <b>Estimated time:</b> ${data.estimated_time_hr} hrs<br>
      <b>Dynamic Price:</b> ₹${data.dynamic_price}<br>
      <b>Carbon Footprint:</b> ${data.carbon_footprint_kg} kg CO₂
    `;
    document.getElementById("routeInfo").innerHTML = info;
  });
}
