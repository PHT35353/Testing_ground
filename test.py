import streamlit as st
import streamlit_javascript as stjs
import pandas as pd
import math
import requests
import json
import streamlit.components.v1 as components
from streamlit_javascript import st_javascript as stjs 
import time
from fastapi import FastAPI
from pydantic import BaseModel
import threading
import uvicorn

# Set up a title for the app
st.title("Piping tool")

# Add instructions and explain color options
st.markdown("""
This tool allows you to:
1. Draw rectangles (polygons), lines, and markers (landmarks) on the map.
2. Assign names and choose specific colors for each feature individually upon creation.
3. Display distances for lines and dimensions for polygons both on the map and in the sidebar.
4. Show relationships between landmarks and lines (e.g., a line belongs to two landmarks).

**Available Colors**:
- Named colors: red, blue, green, yellow, purple, cyan, pink, orange, black, white, gray
- Hex colors: #FF0000 (red), #00FF00 (green), #0000FF (blue), #FFFF00 (yellow), #800080 (purple), #00FFFF (cyan), #FFC0CB (pink), #FFA500 (orange), #000000 (black), #FFFFFF (white), #808080 (gray)
""")

# Sidebar to manage the map interactions
st.sidebar.title("Map Controls")

# Add radio button to choose between total distance or individual lines
distance_mode = st.sidebar.radio("Distance Mode", options=["Total Distance", "Individual Lines"])


# Default location set to Amsterdam, Netherlands
default_location = [52.3676, 4.9041]

# Input fields for latitude and longitude
latitude = st.sidebar.number_input("Latitude", value=default_location[0])
longitude = st.sidebar.number_input("Longitude", value=default_location[1])

# Search bar for address search
address_search = st.sidebar.text_input("Search for address (requires internet connection)")

# Mapbox GL JS API token
mapbox_access_token = "pk.eyJ1IjoicGFyc2ExMzgzIiwiYSI6ImNtMWRqZmZreDB6MHMyaXNianJpYWNhcGQifQ.hot5D26TtggHFx9IFM-9Vw"


# Function to get the distance values from FastAPI with retries
def get_distances_value():
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get("https://fastapi-test-production-b351.up.railway.app/get-distances/")
            if response.status_code == 200:
                data = response.json()
                distances = data.get("distances", {})
                return distances
            else:
                st.error(f"Failed to fetch distances. Status code: {response.status_code}. Retrying...")
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching distances: {e}. Retrying...")
    st.error("Failed to fetch distances from FastAPI server after multiple attempts.")
    return {}

# HTML and JS for Mapbox with Mapbox Draw plugin to add drawing functionalities
mapbox_map_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <title>Mapbox GL JS Drawing Tool</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <script src="https://api.mapbox.com/mapbox-gl-js/v2.10.0/mapbox-gl.js"></script>
    <link href="https://api.mapbox.com/mapbox-gl-js/v2.10.0/mapbox-gl.css" rel="stylesheet" />
    <script src="https://api.mapbox.com/mapbox-gl-js/plugins/mapbox-gl-draw/v1.3.0/mapbox-gl-draw.js"></script>
    <link href="https://api.mapbox.com/mapbox-gl-js/plugins/mapbox-gl-draw/v1.3.0/mapbox-gl-draw.css" rel="stylesheet" />
    <script src="https://cdn.jsdelivr.net/npm/@turf/turf/turf.min.js"></script>
    <style>
        body {{
            margin: 0;
            padding: 0;
        }}
        #map {{
            position: absolute;
            top: 0;
            bottom: 0;
            width: 100%;
        }}
        .mapboxgl-ctrl {{
            margin: 10px;
        }}
        #sidebar {{
            position: absolute;
            top: 0;
            left: 0;
            width: 300px;
            height: 100%;
            background-color: white;
            border-right: 1px solid #ccc;
            z-index: 1;
            padding: 10px;
            transition: all 0.3s ease;
        }}
        #sidebar.collapsed {{
            width: 0;
            padding: 0;
            overflow: hidden;
        }}
        #toggleSidebar {{
            position: absolute;
            bottom: 290px;
            right: 10px;
            z-index: 2;
            background-color: white;
            color:black;
            border: 1px solid #ccc;
            padding: 10px 15px;
            cursor: pointer;
            margin-bottom: 10px;
        }}
        #sidebarContent {{
            max-height: 90%;
            overflow-y: auto;
        }}
        h3 {{
            margin-top: 0;
        }}
    </style>
</head>
<body>
<div id="sidebar" class="sidebar">
    <div id="sidebarContent">
        <h3>Measurements</h3>
        <div id="measurements"></div>
    </div>
</div>
<button id="toggleSidebar" onclick="toggleSidebar()">Collapse</button>
<div id="map"></div>
<script>
    let distanceListenerAdded = false;
    mapboxgl.accessToken = '{mapbox_access_token}';

    const map = new mapboxgl.Map({{
        container: 'map',
        style: 'mapbox://styles/mapbox/satellite-streets-v12',
        center: [{longitude}, {latitude}],
        zoom: 13,
        pitch: 45, // For 3D effect
        bearing: 0, // Rotation angle
        antialias: true
    }});

    // Add map controls for zoom, rotation, and fullscreen
    map.addControl(new mapboxgl.NavigationControl());
    map.addControl(new mapboxgl.FullscreenControl());

    // Enable rotation and pitch adjustments using right-click
    map.dragRotate.enable();
    map.touchZoomRotate.enableRotation();

    // Add the Draw control for drawing polygons, markers, lines, etc.
    const Draw = new MapboxDraw({{
        displayControlsDefault: false,
        controls: {{
            polygon: true,
            line_string: true,
            point: true,
            trash: true
        }},
    }});

    map.addControl(Draw);

    let landmarkCount = 0;
    let landmarks = [];
    let featureColors = {{}};
    let featureNames = {{}};

   // Attach the updateMeasurements function to Mapbox draw events
map.on('draw.create', (e) => {{
    const data = Draw.getAll();
    data.features.forEach((feature) => {{
        if (feature.geometry.type === 'LineString') {{
            const length = turf.length(feature, {{ units: 'kilometers' }});
            // Send the distance and feature ID to the backend API
            fetch("https://fastapi-test-production-b351.up.railway.app/send-distance/", {{
                method: "POST",
                headers: {{
                    "Content-Type": "application/json",
                }},
                body: JSON.stringify({{ line_id: feature.id, distance: length }}),
            }})
            .then(response => response.json())
            .then(data => console.log("Distance sent successfully", data))
            .catch((error) => console.error("Error sending distance", error));
        }}
    }});
    updateSidebarMeasurements(e);
}});


map.on('draw.update', (e) => {{
    updateSidebarMeasurements(e);
}});

// Handle deletion of features and update the backend
map.on('draw.delete', (e) => {{
    const features = e.features;
    features.forEach((feature) => {{
        if (feature.geometry.type === 'LineString') {{
            // Send delete request to FastAPI for this line
            fetch(`https://fastapi-test-production-b351.up.railway.app/delete-distance/${{feature.id}}`, {{
                method: "DELETE"
            }})
            .then(response => response.json())
            .then(data => console.log("Distance deleted successfully", data))
            .catch((error) => console.error("Error deleting distance", error));
        }}
    }});
    deleteFeature(e);
}});

map.on('load', () => {{
    // Fetch previously saved distances from FastAPI
    fetch("https://fastapi-test-production-b351.up.railway.app/get-distances/")
    .then(response => response.json())
    .then(data => {{
        const distances = data.distances;
        Object.keys(distances).forEach(line_id => {{
            const distance = distances[line_id];
            // Here, recreate the features with the distances received
            // This can be extended to recreate the full LineString if coordinates are also saved
            console.log(`Restored line ${{line_id}} with distance: ${{distance}}`);
            // Add your logic here to redraw lines if possible
        }});
    }})
    .catch((error) => console.error("Error loading saved distances", error));
    updateSidebarMeasurements(e);
}});



 function updateSidebarMeasurements(e) {{
        const data = Draw.getAll();
        let sidebarContent = "";
        let totalDistances = []; 
        if (data.features.length > 0) {{
            const features = data.features;
            features.forEach(function (feature, index) {{
                if (feature.geometry.type === 'LineString') {{
                    const length = turf.length(feature);
                    totalDistances.push(length);
                    const startCoord = feature.geometry.coordinates[0];
                    const endCoord = feature.geometry.coordinates[feature.geometry.coordinates.length - 1];

                    // Identify landmarks for the start and end points of the line
                    let startLandmark = landmarks.find(lm => turf.distance(lm.geometry.coordinates, startCoord) < 0.01);
                    let endLandmark = landmarks.find(lm => turf.distance(lm.geometry.coordinates, endCoord) < 0.01);

                    if (!featureNames[feature.id]) {{
                        const name = prompt("Enter a name for this line:");
                        featureNames[feature.id] = name || "Line " + (index + 1);
                    }}

                    if (!featureColors[feature.id]) {{
                        const lineColor = prompt("Enter a color for this line (e.g., red, purple, cyan, pink):");
                        featureColors[feature.id] = lineColor || 'blue';
                    }}

                    
                    // Update the feature's source when it's moved to ensure the color moves with it
                    map.getSource('line-' + feature.id)?.setData(feature);

                    map.addLayer({{
                        id: 'line-' + feature.id,
                        type: 'line',
                        source: {{
                            type: 'geojson',
                            data: feature
                        }},
                        layout: {{}},
                        paint: {{
                            'line-color': featureColors[feature.id],
                            'line-width': 4
                        }}
                    }});

                    let distanceUnit = length >= 1 ? 'km' : 'm';
                    let distanceValue = length >= 1 ? length.toFixed(2) : (length * 1000).toFixed(2);
                    

                    sidebarContent += '<p>Line ' + featureNames[feature.id] + ' belongs to ' + (startLandmark?.properties.name || 'Unknown') + ' - ' + (endLandmark?.properties.name || 'Unknown') + ': ' + distanceValue + ' ' + distanceUnit + '</p>';
                }} else if (feature.geometry.type === 'Polygon') {{
                    if (!feature.properties.name) {{
                        if (!featureNames[feature.id]) {{
                            const name = prompt("Enter a name for this polygon:");
                            feature.properties.name = name || "Polygon " + (index + 1);
                            featureNames[feature.id] = feature.properties.name;
                        }} else {{
                            feature.properties.name = featureNames[feature.id];
                        }}
                    }}

                    if (!featureColors[feature.id]) {{
                        const polygonColor = prompt("Enter a color for this polygon (e.g., green, yellow):");
                        featureColors[feature.id] = polygonColor || 'yellow';
                    }}

                    // Update the feature's source when it's moved to ensure the color moves with it
                    map.getSource('polygon-' + feature.id)?.setData(feature);

                    map.addLayer({{
                        id: 'polygon-' + feature.id,
                        type: 'fill',
                        source: {{
                            type: 'geojson',
                            data: feature
                        }},
                        paint: {{
                            'fill-color': featureColors[feature.id],
                            'fill-opacity': 0.6
                        }}
                    }});

                    const bbox = turf.bbox(feature);
                    const width = turf.distance([bbox[0], bbox[1]], [bbox[2], bbox[1]]);
                    const height = turf.distance([bbox[0], bbox[1]], [bbox[0], bbox[3]]);

                    let widthUnit = width >= 1 ? 'km' : 'm';
                    let heightUnit = height >= 1 ? 'km' : 'm';
                    let widthValue = width >= 1 ? width.toFixed(2) : (width * 1000).toFixed(2);
                    let heightValue = height >= 1 ? height.toFixed(2) : (height * 1000).toFixed(2);

                    sidebarContent += '<p>Polygon ' + feature.properties.name + ': Width = ' + widthValue + ' ' + widthUnit + ', Height = ' + heightValue + ' ' + heightUnit + '</p>';
                }} else if (feature.geometry.type === 'Point') {{
                    // Handle landmarks (points)
                    if (!feature.properties.name) {{
                        if (!featureNames[feature.id]) {{
                            const name = prompt("Enter a name for this landmark:");
                            feature.properties.name = name || "Landmark " + (landmarkCount + 1);
                            featureNames[feature.id] = feature.properties.name;
                            landmarks.push(feature);
                            landmarkCount++;
                        }} else {{
                            feature.properties.name = featureNames[feature.id];
                        }}
                    }}

                    if (!featureColors[feature.id]) {{
                        const markerColor = prompt("Enter a color for this landmark (e.g., black, white):");
                        featureColors[feature.id] = markerColor || 'black';
                    }}

                    map.getSource('marker-' + feature.id)?.setData(feature);

                    map.addLayer({{
                        id: 'marker-' + feature.id,
                        type: 'circle',
                        source: {{
                            type: 'geojson',
                            data: feature
                        }},
                        paint: {{
                            'circle-radius': 8,
                            'circle-color': featureColors[feature.id]
                        }}
                    }});

                    sidebarContent += '<p>Landmark ' + feature.properties.name + '</p>';
                }}
            }});
        }} else {{
            sidebarContent = "<p>No features drawn yet.</p>";
        }}
        document.getElementById('measurements').innerHTML = sidebarContent;
   }}
    
    function toggleSidebar() {{
        var sidebar = document.getElementById('sidebar');
        if (sidebar.classList.contains('collapsed')) {{
            sidebar.classList.remove('collapsed');
            document.getElementById('toggleSidebar').innerText = "Close Sidebar";
        }} else {{
            sidebar.classList.add('collapsed');
            document.getElementById('toggleSidebar').innerText = "Open Sidebar";
        }}
    }}

  // Function to handle deletion of features
function deleteFeature(e) {{
    const features = e.features;
    features.forEach(function (feature) {{
        const featureId = feature.id;

        // Remove the feature's associated color and name from dictionaries
        delete featureColors[featureId];
        delete featureNames[featureId];

        // Remove the layer associated with the feature, if it exists
        if (map.getLayer('line-' + featureId)) {{
            map.removeLayer('line-' + featureId);
            map.removeSource('line-' + featureId);
        }}

        if (map.getLayer('polygon-' + featureId)) {{
            map.removeLayer('polygon-' + featureId);
            map.removeSource('polygon-' + featureId);
        }}

        if (map.getLayer('marker-' + featureId)) {{
            map.removeLayer('marker-' + featureId);
            map.removeSource('marker-' + featureId);
        }}

        console.log(`Feature ${{featureId}} and its color have been removed.`);
    }});

   
    updateSidebarMeasurements(e)
}}

</script>
</body>
</html>
"""
components.html(mapbox_map_html, height=600)

if st.sidebar.button("Search Location"):
    geocode_url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{address_search}.json?access_token={mapbox_access_token}"
    try:
        response = requests.get(geocode_url)
        if response.status_code == 200:
            geo_data = response.json()
            if len(geo_data['features']) > 0:
                coordinates = geo_data['features'][0]['center']
                latitude, longitude = coordinates[1], coordinates[0]
                st.sidebar.success(f"Address found: {geo_data['features'][0]['place_name']}")
                st.sidebar.write(f"Coordinates: Latitude {latitude}, Longitude {longitude}")
                default_location = [latitude, longitude]
                # Set the new center for the map to zoom in closely
                mapbox_map_html = mapbox_map_html.replace("{latitude}", str(latitude)).replace("{longitude}", str(longitude)).replace("zoom: 13", "zoom: 18")
            else:
                st.sidebar.error("Address not found.")
        else:
            st.sidebar.error("Error connecting to the Mapbox API.")
    except Exception as e:
        st.sidebar.error(f"Error: {e}")


#Function to save a copy of the map and sidebar as an HTML file
def save_map():
    st.download_button(
        label="Download Map and Measurements",
        data=mapbox_map_html,
        file_name="saved_map_with_drawings.html",
        mime="text/html"
    )


#the pip price calculation par of the code:
# Pipe data dictionaries
B1001_data_dict = {
    'Nominal diameter (inches)': ['0.5', '0.75', '1', '1.5', '2', '3', '4', '5', '6', '8', '10', '12', '14', '16', '20'],
    'External diameter (mm)': ['21.3', '26.7', '33.4', '48.3', '60.3', '88.9', '114.3', '141.3', '168.3', '219.1', '273', '323.9', '355.6', '406.4', '508'],
    'Wall thickness (mm)': ['2.8', '2.9', '3.4', '3.7', '3.9', '5.5', '6', '6.6', '7.1', '8.2', '9.3', '9.5', '9.5', '9.5', '9.5'],
    'Weight (kg/m)': ['1.27', '1.68', '2.5', '4.05', '5.44', '11.3', '16.1', '21.8', '28.3', '42.5', '60.3', '73.8', '81.3', '93.3', '117'],
    'Cost per 100 m (Euro)': ['277', '338', '461', '707', '738', '1310', '1805', '2615', '3360', '5165', '7450', '9350', '11235', '13020', '16490'],
    'Pressure (bar)': ['215.59', '178.13', '166.95', '125.63', '106.07', '101.46', '86.09', '76.6', '69.19', '61.38', '55.87', '48.1', '43.81', '38.34', '30.67']
}

B1003_data_dict = {
    'Nominal diameter (inches)': ['0.5', '0.75', '1.0', '1.5', '2.0', '3.0', '4.0', '5.0', '6.0', '8.0', '10.0', '12.0', '14.0', '16.0', '20.0'],
    'External diameter (mm)': ['21.3', '26.7', '33.4', '48.3', '60.3', '88.9', '114.3', '141.3', '168.3', '219.1', '273.0', '323.9', '355.6', '406.4', '508.0'],
    'Wall thickness (mm)': ['3.7', '3.9', '4.5', '5.1', '5.5', '7.6', '8.6', '9.5', '11.0', '12.7', '12.7', '12.7', '12.7', '12.7', '12.7'],
    'Weight (kg/m)': ['1.62', '2.2', '3.24', '5.41', '7.48', '15.3', '22.3', '31.0', '42.6', '64.6', '81.6', '97.5', '107.0', '123.16', '155.0'],
    'Cost per 100 m (Euro)': ['315', '389', '536', '840', '1060', '1755', '2635', '3770', '4895', '8010', '10285', '12375', '14905', '17045', '21235'],
    'Pressure (bar)': ['158.27', '133.08', '122.75', '96.2', '83.1', '77.89', '68.55', '61.26', '59.55', '52.81', '42.39', '35.72', '32.54', '28.47', '22.78']
}

B1005_data_dict = {
    'Nominal diameter (inches)': ['0.5', '0.75', '1.0', '1.25', '1.5', '2.0', '2.5', '3.0', '4.0', '5.0', '6.0', '8.0', '10.0', '12.0'],
    'External diameter (mm)': ['21.34', '26.67', '33.4', '42.16', '48.26', '60.32', '73.02', '88.9', '114.3', '141.3', '168.27', '219.07', '273.05', '323.85'],
    'Wall thickness (mm)': ['2.11', '2.11', '2.77', '2.77', '2.77', '2.77', '3.05', '3.05', '3.05', '3.4', '3.4', '3.76', '4.19', '4.57'],
    'Weight (kg/m)': ['0.99', '1.27', '2.08', '2.69', '3.1', '3.92', '5.25', '6.44', '8.34', '11.56', '13.82', '19.92', '27.75', '35.96'],
    'Cost per m04 (Euro)': ['10.7', '14.0', '18.0', '22.2', '38.6', '24.0', '32.0', '40.0', '57.0', '75.0', '97.4', '104.0', '180.0', '194.0'],
    'Cost per m16 (Euro)': ['13.0', '18.0', '23.0', '26.0', '44.9', '34.0', '40.0', '49.0', '64.1', '93.0', '120.0', '133.0', '210.0', '228.0'],
    'Pressure (bar)': ['202.69', '162.19', '170.01', '134.69', '117.66', '94.14', '85.63', '70.33', '54.7', '49.33', '41.42', '35.19', '31.46', '28.93']
}

B1008_data_dict = {
    'External diameter (mm)': ['25', '32', '40', '50', '50', '63', '63', '75', '75', '90', '90', '110', '110', '125', '125', '160', '160', '200', '200', '250'],
    'Wall thickness (mm)': ['1.5', '1.8', '1.9', '1.8', '2.4', '1.8', '3.0', '2.6', '3.6', '2.7', '4.3', '3.2', '5.3', '3.7', '6.0', '4.7', '7.7', '5.4', '6.3', '7.3'],
    'Pressure (bar)': ['10', '10', '10', '6', '10', '6', '10', '6', '10', '6', '10', '6', '10', '6', '10', '6', '10', '6', '10', '6'],
    'Cost per 100 m (Euro)': ['208', '243', '312', '370', '445', '531', '658', '728', '959', '1180', '1365', '1500', '1985', '2170', '2770', '3475', '4475', '5475', '7450', '9250']
}

# Function to calculate pressure using Barlow's formula
def Barlow(S, D, t):
    P = (2 * S * t) / D
    return P

# Streamlit user inputs
def get_user_inputs1():
    pressure = st.number_input("Enter the pressure (bar):", min_value=0.0, format="%.2f")
    temperature = st.number_input("Enter the temperature (°C):", min_value=0.0, format="%.2f")
    medium = st.text_input("Enter the medium:")
    return pressure, temperature, medium

# Function to choose pipe material based on user input
def choose_pipe_material(P, T, M):
    if M.lower() in ('water glycol', 'water-glycol', 'pressurized water', 'pressurized-water'):
        if P > 10 and T > 425:
            return 'B1005'
        else:
            return 'B1008'

    if P <= 10:
        if T <= 60:
            return 'B1008'
        elif 60 <= T <= 425:
            return 'B1001'
        else:
            return 'B1008'
    else:
        if T <= 425:
            return 'B1001'
        else:
            return 'B1005'

# Pipe filter functions for each material type
def B1001_filter(P, distanceValue):
    B1001_data_dict['External diameter (mm)'] = list(map(float, B1001_data_dict['External diameter (mm)']))
    B1001_data_dict['Wall thickness (mm)'] = list(map(float, B1001_data_dict['Wall thickness (mm)']))
    B1001_data_dict['Cost per 100 m (Euro)'] = list(map(float, B1001_data_dict['Cost per 100 m (Euro)']))
    B1001_data_dict['Pressure (bar)'] = list(map(float, B1001_data_dict['Pressure (bar)']))

    B1001_data_dict['Cost per m (Euro)'] = [cost / 100 for cost in B1001_data_dict['Cost per 100 m (Euro)']]
    B1001_data_dict['Total Cost (Euro)'] = [p * distanceValue for p in B1001_data_dict['Cost per m (Euro)']]

    available_pipes = []
    for i in range(len(B1001_data_dict['Pressure (bar)'])):
        if B1001_data_dict['Pressure (bar)'][i] >= P:
            available_pipes.append({
                'External diameter (mm)': B1001_data_dict['External diameter (mm)'][i],
                'Wall thickness (mm)': B1001_data_dict['Wall thickness (mm)'][i],
                'Cost per m (Euro)': B1001_data_dict['Cost per m (Euro)'][i],
                'Total Cost (Euro)': B1001_data_dict['Total Cost (Euro)'][i] 
            })

    if not available_pipes:
        st.write(f"No pipes found for the pressure of {P} bar.")
    else:
        st.write(f"Available carbon steel pipes for {P} bar or higher pressure:")
        df = pd.DataFrame(available_pipes)
        st.dataframe(df)

# Similar filters for B1003, B1005, and B1008 (will follow the same pattern)
def B1003_filter(P, distanceValue):
    B1003_data_dict['External diameter (mm)'] = list(map(float, B1003_data_dict['External diameter (mm)']))
    B1003_data_dict['Wall thickness (mm)'] = list(map(float, B1003_data_dict['Wall thickness (mm)']))
    B1003_data_dict['Cost per 100 m (Euro)'] = list(map(float, B1003_data_dict['Cost per 100 m (Euro)']))
    B1003_data_dict['Pressure (bar)'] = list(map(float, B1003_data_dict['Pressure (bar)']))
    
    B1003_data_dict['Cost per m (Euro)'] = [cost / 100 for cost in B1003_data_dict['Cost per 100 m (Euro)']]
    B1003_data_dict['Total Cost (Euro)'] = [p * distanceValue for p in B1003_data_dict['Cost per m (Euro)']]
    
    available_pipes = []
    for i in range(len(B1003_data_dict['Pressure (bar)'])):
        if B1003_data_dict['Pressure (bar)'][i] >= P:
            available_pipes.append({
                'External diameter (mm)': B1003_data_dict['External diameter (mm)'][i],
                'Wall thickness (mm)': B1003_data_dict['Wall thickness (mm)'][i],
                'Cost per m (Euro)': B1003_data_dict['Cost per m (Euro)'][i],
                'Total Cost (Euro)': B1003_data_dict['Total Cost (Euro)'][i]
            })

    if not available_pipes:
        st.write(f"No pipes found for the pressure of {P} bar.")
    else:
        st.write(f"Available carbon steel extra strong pipes for {P} bar or higher pressure:")
        df = pd.DataFrame(available_pipes)
        st.dataframe(df)

def B1005_filter(P, distanceValue):
    B1005_data_dict['External diameter (mm)'] = list(map(float, B1005_data_dict['External diameter (mm)']))
    B1005_data_dict['Wall thickness (mm)'] = list(map(float, B1005_data_dict['Wall thickness (mm)']))
    B1005_data_dict['Cost per m04 (Euro)'] = list(map(float, B1005_data_dict['Cost per m04 (Euro)']))
    B1005_data_dict['Pressure (bar)'] = list(map(float, B1005_data_dict['Pressure (bar)']))

    B1005_data_dict['Cost per m (Euro)'] = B1005_data_dict['Cost per m04 (Euro)']
    B1005_data_dict['Total Cost (Euro)'] = [p * distanceValue for p in B1005_data_dict['Cost per m (Euro)']]

    available_pipes = []
    for i in range(len(B1005_data_dict['Pressure (bar)'])):
        if B1005_data_dict['Pressure (bar)'][i] >= P:
            available_pipes.append({
                'External diameter (mm)': B1005_data_dict['External diameter (mm)'][i],
                'Wall thickness (mm)': B1005_data_dict['Wall thickness (mm)'][i],
                'Cost per m (Euro)': B1005_data_dict['Cost per m (Euro)'][i],
                'Total Cost (Euro)': B1005_data_dict['Total Cost (Euro)'][i]
            })

    if not available_pipes:
        st.write(f"No pipes found for the pressure of {P} bar.")
    else:
        st.write(f"Available welded stainless steel pipes for {P} bar or higher pressure:")
        df = pd.DataFrame(available_pipes)
        st.dataframe(df)

def B1008_filter(P, distanceValue):
    B1008_data_dict['External diameter (mm)'] = list(map(float, B1008_data_dict['External diameter (mm)']))
    B1008_data_dict['Wall thickness (mm)'] = list(map(float, B1008_data_dict['Wall thickness (mm)']))
    B1008_data_dict['Pressure (bar)'] = list(map(float, B1008_data_dict['Pressure (bar)']))
    B1008_data_dict['Cost per 100 m (Euro)'] = list(map(float, B1008_data_dict['Cost per 100 m (Euro)']))

    B1008_data_dict['Cost per m (Euro)'] = [cost / 100 for cost in B1008_data_dict['Cost per 100 m (Euro)']]
    B1008_data_dict['Total Cost (Euro)'] = [p * distanceValue for p in B1008_data_dict['Cost per m (Euro)']]

    available_pipes = []
    for i in range(len(B1008_data_dict['Pressure (bar)'])):
        if B1008_data_dict['Pressure (bar)'][i] >= P:
            available_pipes.append({
                'External diameter (mm)': B1008_data_dict['External diameter (mm)'][i],
                'Wall thickness (mm)': B1008_data_dict['Wall thickness (mm)'][i],
                'Cost per m (Euro)': B1008_data_dict['Cost per m (Euro)'][i],
                'Total Cost (Euro)': B1008_data_dict['Total Cost (Euro)'][i]
            })

    if not available_pipes:
        st.write(f"No pipes found for the pressure of {P} bar.")
    else:
        st.write(f"Available PVC pipes for {P} bar or higher pressure:")
        df = pd.DataFrame(available_pipes)
        st.dataframe(df)

# Function to choose pipe and filter based on material
def Pipe_finder(material, P, distanceValue):
    if material == 'B1001':
        B1001_filter(P, distanceValue)
        st.write("")
        B1003_filter(P, distanceValue)

    elif material == 'B1005':
        B1005_filter(P, distanceValue)

    elif material == 'B1008':
        B1008_filter(P, distanceValue)

    else:
        st.write("Material not found")

# Function to get user inputs including pressure, temperature, medium
def get_user_inputs():
    # Get pressure from user
    pressure = st.number_input("Enter the pressure (bar):", min_value=0.0, format="%.2f")

    # Get temperature from user
    temperature = st.number_input("Enter the temperature (°C):", min_value=0.0, format="%.2f")

    # Get medium from user
    medium = st.text_input("Enter the medium:")

    return pressure, temperature, medium

# Function to check if FastAPI server is running
def check_server_status():
    try:
        response = requests.get("https://fastapi-test-production-b351.up.railway.app/")
        if response.status_code == 200:
            return True
        else:
            st.error(f"Server is not available. Status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to FastAPI server: {e}")
        return False

# Function to get the distance value from FastAPI with retries
def get_distance_value():
    max_retries = 3
    for attempt in range(max_retries):
        if not check_server_status():
            break
        try:
            response = requests.get("https://fastapi-test-production-b351.up.railway.app/get-distance/")
            if response.status_code == 200:
                data = response.json()
                distance = data.get("distance")
                if distance is not None:
                    return distance
                else:
                    st.warning("Distance value is not yet available.")
            else:
                st.error(f"Failed to fetch distance. Status code: {response.status_code}. Retrying...")
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching distance: {e}. Retrying...")
    st.error("Failed to fetch distance from FastAPI server after multiple attempts.")
    return None


# Main function to run the app
def pipe_main():
    st.title("Pipe Selection Tool")
    distance_data = get_distances_value()  # Fetch all line distances from the backend

    if not distance_data:
        st.warning("No line distances available yet. Please draw lines on the map to proceed.")
    else:
        st.write(f"Distances received: {distance_data}")

        # Handle selection between Total Distance and Individual Lines
        if distance_mode == "Total Distance":
            total_distance = sum(distance_data.values())  # Calculate total distance
            st.write(f"Total Distance: {total_distance:.2f} km")

            # Button to calculate pipes for total distance
            if st.button("Find Pipes for Total Distance"):
                pressure = st.number_input("Enter the pressure (bar):", min_value=0.0, format="%.2f")
                temperature = st.number_input("Enter the temperature (°C):", min_value=0.0, format="%.2f")
                medium = st.text_input("Enter the medium:")
                pipe_material = choose_pipe_material(pressure, temperature, medium)
                st.write(f"Selected Pipe Material: {pipe_material}")
                Pipe_finder(pipe_material, pressure, total_distance)

        elif distance_mode == "Individual Lines":
            # Loop through each individual line
            for line_id, distance in distance_data.items():
                st.write(f"Line ID {line_id}: {distance:.2f} km")
                if st.button(f"Find Pipes for Line {line_id}"):
                    # Get individual inputs for pressure, temperature, and medium
                    pressure = st.number_input("Enter the pressure (bar):", min_value=0.0, format="%.2f", key=f"pressure_{line_id}")
                    temperature = st.number_input("Enter the temperature (°C):", min_value=0.0, format="%.2f", key=f"temperature_{line_id}")
                    medium = st.text_input("Enter the medium:", key=f"medium_{line_id}")
                    pipe_material = choose_pipe_material(pressure, temperature, medium)
                    st.write(f"Selected Pipe Material: {pipe_material}")
                    Pipe_finder(pipe_material, pressure, distance)


# Run the main function
pipe_main()
