mapboxgl.accessToken = '{mapbox_access_token}';

    const map = new mapboxgl.Map({
        container: 'map',
        style: 'mapbox://styles/mapbox/satellite-streets-v12',
        center: [{longitude}, {latitude}],
        zoom: 13,
        pitch: 45,
        bearing: 0,
        antialias: true
    });

    map.addControl(new mapboxgl.NavigationControl());
    map.addControl(new mapboxgl.FullscreenControl());

    map.dragRotate.enable();
    map.touchZoomRotate.enableRotation();

    const Draw = new MapboxDraw({
        displayControlsDefault: false,
        controls: {
            polygon: true,
            line_string: true,
            point: true,
            trash: true
        },
    });

    map.addControl(Draw);

    let landmarkCount = 0;
    let landmarks = [];
    let featureColors = {};
    let featureNames = {};
    let featureDetails = {}; // New object to store pressure, temperature, medium

    map.on('draw.create', updateMeasurements);
    map.on('draw.update', updateMeasurements);
    map.on('draw.delete', deleteFeature);

    function updateMeasurements(e) {
        const data = Draw.getAll();
        let sidebarContent = "";
        if (data.features.length > 0) {
            const features = data.features;
            features.forEach(function (feature, index) {
                if (feature.geometry.type === 'LineString') {
                    const length = turf.length(feature);
                    const startCoord = feature.geometry.coordinates[0];
                    const endCoord = feature.geometry.coordinates[feature.geometry.coordinates.length - 1];

                    let startLandmark = landmarks.find(lm => turf.distance(lm.geometry.coordinates, startCoord) < 0.01);
                    let endLandmark = landmarks.find(lm => turf.distance(lm.geometry.coordinates, endCoord) < 0.01);

                    if (!featureNames[feature.id]) {
                        const name = prompt("Enter a name for this line:");
                        featureNames[feature.id] = name || "Line " + (index + 1);
                    }

                    if (!featureColors[feature.id]) {
                        const lineColor = prompt("Enter a color for this line (e.g., red, purple, cyan, pink):");
                        featureColors[feature.id] = lineColor || 'blue';
                    }

                    map.getSource('line-' + feature.id)?.setData(feature);

                    map.addLayer({
                        id: 'line-' + feature.id,
                        type: 'line',
                        source: {
                            type: 'geojson',
                            data: feature
                        },
                        layout: {},
                        paint: {
                            'line-color': featureColors[feature.id],
                            'line-width': 4
                        }
                    });

                    let distanceUnit = length >= 1 ? 'km' : 'm';
                    let distanceValue = length >= 1 ? length.toFixed(2) : (length * 1000).toFixed(2);

                    sidebarContent += '<p>Line ' + featureNames[feature.id] + ' belongs to ' + (startLandmark?.properties.name || 'Unknown') + ' - ' + (endLandmark?.properties.name || 'Unknown') + ': ' + distanceValue + ' ' + distanceUnit + '</p>';
                
                } else if (feature.geometry.type === 'Polygon') {
                    if (!feature.properties.name) {
                        if (!featureNames[feature.id]) {
                            const name = prompt("Enter a name for this polygon:");
                            feature.properties.name = name || "Polygon " + (index + 1);
                            featureNames[feature.id] = feature.properties.name;
                        } else {
                            feature.properties.name = featureNames[feature.id];
                        }
                    }

                    if (!featureColors[feature.id]) {
                        const polygonColor = prompt("Enter a color for this polygon (e.g., green, yellow):");
                        featureColors[feature.id] = polygonColor || 'yellow';
                    }

                    map.getSource('polygon-' + feature.id)?.setData(feature);

                    map.addLayer({
                        id: 'polygon-' + feature.id,
                        type: 'fill',
                        source: {
                            type: 'geojson',
                            data: feature
                        },
                        paint: {
                            'fill-color': featureColors[feature.id],
                            'fill-opacity': 0.6
                        }
                    });

                    const bbox = turf.bbox(feature);
                    const width = turf.distance([bbox[0], bbox[1]], [bbox[2], bbox[1]]);
                    const height = turf.distance([bbox[0], bbox[1]], [bbox[0], bbox[3]]);

                    let widthUnit = width >= 1 ? 'km' : 'm';
                    let heightUnit = height >= 1 ? 'km' : 'm';
                    let widthValue = width >= 1 ? width.toFixed(2) : (width * 1000).toFixed(2);
                    let heightValue = height >= 1 ? height.toFixed(2) : (height * 1000).toFixed(2);

                    sidebarContent += '<p>Polygon ' + feature.properties.name + ': Width = ' + widthValue + ' ' + widthUnit + ', Height = ' + heightValue + ' ' + heightUnit + '</p>';
                
                } else if (feature.geometry.type === 'Point') {
                    if (!feature.properties.name) {
                        if (!featureNames[feature.id]) {
                            const name = prompt("Enter a name for this landmark:");
                            feature.properties.name = name || "Landmark " + (landmarkCount + 1);
                            featureNames[feature.id] = feature.properties.name;
                            landmarks.push(feature);
                            landmarkCount++;
                        } else {
                            feature.properties.name = featureNames[feature.id];
                        }
                    }

                    if (!featureColors[feature.id]) {
                        const markerColor = prompt("Enter a color for this landmark (e.g., black, white):");
                        featureColors[feature.id] = markerColor || 'black';
                    }

                    map.getSource('marker-' + feature.id)?.setData(feature);

                    map.addLayer({
                        id: 'marker-' + feature.id,
                        type: 'circle',
                        source: {
                            type: 'geojson',
                            data: feature
                        },
                        paint: {
                            'circle-radius': 8,
                            'circle-color': featureColors[feature.id]
                        }
                    });

                    sidebarContent += '<p>Landmark ' + feature.properties.name + '</p>';
                }

                // Show the modal for additional details input!! change to linestring if error
                if (feature.geometry.type === 'LineString' || feature.geometry.type === 'Polygon') {
                    document.getElementById('inputModal').style.display = 'block';
                }

                if (featureDetails[feature.id]) {
                    sidebarContent += `<p>Pressure: ${featureDetails[feature.id].pressure} bar</p>`;
                    sidebarContent += `<p>Temperature: ${featureDetails[feature.id].temperature} °C</p>`;
                    sidebarContent += `<p>Medium: ${featureDetails[feature.id].medium}</p>`;
                }
            });
        } else {
            sidebarContent = "<p>No features drawn yet.</p>";
        }
        document.getElementById('measurements').innerHTML = sidebarContent;
    }

    function saveFeatureDetails() {
        const pressure = document.getElementById('pressure').value;
        const temperature = document.getElementById('temperature').value;
        const medium = document.getElementById('medium').value;
        
        const currentFeatureId = Draw.getAll().features[Draw.getAll().features.length - 1].id;
        featureDetails[currentFeatureId] = {
            pressure: pressure || "Unknown",
            temperature: temperature || "Unknown",
            medium: medium || "Unknown"
        };

        document.getElementById('inputModal').style.display = 'none';

        updateMeasurements();
    }

    function toggleSidebar() {
        var sidebar = document.getElementById('sidebar');
        if (sidebar.classList.contains('collapsed')) {
            sidebar.classList.remove('collapsed');
            document.getElementById('toggleSidebar').innerText = "Close Sidebar";
        } else {
            sidebar.classList.add('collapsed');
            document.getElementById('toggleSidebar').innerText = "Open Sidebar";
        }
    }

    function deleteFeature(e) {
        const features = e.features;
        features.forEach(function (feature) {
            delete featureColors[feature.id];
            delete featureNames[feature.id];
            delete featureDetails[feature.id]; // Remove associated feature details

            map.removeLayer('line-' + feature.id);
            map.removeLayer('polygon-' + feature.id);
            map.removeLayer('marker-' + feature.id);
        });
        updateMeasurements();
    }
