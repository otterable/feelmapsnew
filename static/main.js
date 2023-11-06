// Initialize Leaflet map
let mymap = L.map('map').setView([51.505, -0.09], 13);

// Base layers
let osmLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
}).addTo(mymap);

let satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    attribution: '© Esri'
});

// Layer control
let baseLayers = {
    "OpenStreetMap": osmLayer,
    "Satellite": satelliteLayer
};
L.control.layers(baseLayers).addTo(mymap);

let drawnItems = L.featureGroup().addTo(mymap);
let drawControl = new L.Control.Draw({
    draw: {
        polyline: false,
        polygon: true,
        circle: true,
        rectangle: true,
        marker: true
    },
    edit: {
        featureGroup: drawnItems
    }
});
mymap.addControl(drawControl);

mymap.on(L.Draw.Event.CREATED, function (event) {
    let layer = event.layer;
    let categorySelect = document.getElementById('categorySelect');
    let selectedOption = categorySelect.options[categorySelect.selectedIndex];
    let color = selectedOption.dataset.color;
    let categoryId = selectedOption.value;
    
    if (layer instanceof L.Marker) {
        layer.options.icon = new L.Icon.Default({className: 'leaflet-div-icon', iconUrl: getPinUrl(color)});
    } else {
        layer.setStyle({color: color});
    }

    drawnItems.addLayer(layer);

    let geojson = layer.toGeoJSON();
    let description = prompt("Enter a description for this shape:");
    geojson.properties = {
        description: description,
        category: selectedOption.text,
        shape: layer instanceof L.Marker ? 'pin' : layer instanceof L.Circle ? 'circle' : layer instanceof L.Rectangle ? 'rectangle' : 'polygon',
        color: color,
        category_id: categoryId
    };

    // Save to server
    fetch('/add_pin', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(geojson)
    }).then(response => response.json()).then(data => {
        console.log('Shape saved:', data);
    });
});

function getPinUrl(color) {
    let canvas = document.createElement('canvas');
    canvas.width = 32;
    canvas.height = 32;
    let ctx = canvas.getContext('2d');
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(16, 16, 16, 0, Math.PI * 2);
    ctx.closePath();
    ctx.fill();
    return canvas.toDataURL();
}

function startDrawing(shape) {
    drawControl._toolbars.draw._modes[shape].handler.enable();
}



let currentShape = null;

function startDrawing(shape) {
    currentShape = shape;
}

mymap.on('click', function (e) {
    if (!currentShape) return;

    let categorySelect = document.getElementById('categorySelect');
    let selectedOption = categorySelect.options[categorySelect.selectedIndex];
    let color = selectedOption.dataset.color;
    let categoryId = selectedOption.value;

    if (currentShape === 'marker') {
        let popupContent = '<label>Write a note:</label><br><textarea id="noteText"></textarea><br><button onclick="postNote()">Post Note</button><button onclick="cancelDrawing()">Cancel</button>';
        let popup = L.popup()
            .setLatLng(e.latlng)
            .setContent(popupContent)
            .openOn(mymap);
        
        mymap.once('popupclose', function() {
            if (note) {
                L.circleMarker(e.latlng, {radius: 12, color: color, fillColor: color, fillOpacity: 1})
                    .bindPopup(note)
                    .addTo(drawnItems);
                saveShape('marker', e.latlng, color, categoryId, note);
                currentShape = null;
                note = null;
            }
        });
    } else if (['rectangle', 'circle', 'polygon'].includes(currentShape)) {
        if (!tempShape) {
            tempShape = L.featureGroup().addTo(mymap);
            tempShape.addLayer(L.marker(e.latlng));
        } else {
            tempShape.addLayer(L.marker(e.latlng));
            if (currentShape === 'rectangle') {
                let bounds = [tempShape.getLayers()[0].getLatLng(), e.latlng];
                drawShapeAndShowPopup('rectangle', L.rectangle(bounds, {color: color}), color, categoryId);
            } else if (currentShape === 'circle') {
                let radius = tempShape.getLayers()[0].getLatLng().distanceTo(e.latlng);
                drawShapeAndShowPopup('circle', L.circle(tempShape.getLayers()[0].getLatLng(), {radius: radius, color: color}), color, categoryId);
            } else if (currentShape === 'polygon') {
                let latlngs = tempShape.getLayers().map(layer => layer.getLatLng());
                latlngs.push(e.latlng);
                drawShapeAndShowPopup('polygon', L.polygon(latlngs, {color: color}), color, categoryId);
            }
            tempShape.clearLayers();
            tempShape = null;
        }
    }
});

function drawShapeAndShowPopup(shapeType, shape, color, categoryId) {
    let popupContent = '<label>Write a note:</label><br><textarea id="noteText"></textarea><br><button onclick="postNote()">Post Note</button><button onclick="cancelDrawing()">Cancel</button>';
    shape.bindPopup(popupContent).addTo(drawnItems).openPopup();

    drawnItems.once('popupclose', function() {
        if (note) {
            shape.setStyle({color: color}).bindPopup(note).addTo(drawnItems);
            saveShape(shapeType, shape.toGeoJSON().geometry, color, categoryId, note);
            currentShape = null;
            note = null;
        }
    });
}

function saveShape(shapeType, geometry, color, categoryId, note) {
    let data = {
        shape: shapeType,
        geometry: geometry,
        color: color,
        category_id: categoryId,
        description: note
    };

    fetch('/add_pin', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    }).then(response => response.json()).then(responseData => {
        console.log('Shape saved:', responseData);
    });
}

function cancelDrawing() {
    if (tempShape) {
        tempShape.clearLayers();
        tempShape = null;
    }
    currentShape = null;
    mymap.closePopup();
}

function postNote() {
    note = document.getElementById('noteText').value;
    mymap.closePopup();
}
