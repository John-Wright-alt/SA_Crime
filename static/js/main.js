let map;
let crimeLayer;
let currentYear = '2019';
let provinceEvolutionChart;
let provinceBarChart;

// Initialize the map
function initializeMap() {
    map = L.map('map').setView([-28.5, 25], 5);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
    
    loadMapData();
}

// Load crime data for the heat map
function loadMapData() {
    console.log('Loading map data...');
    
    fetch('/api/map-data')
        .then(response => {
            console.log('Response status:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Raw data received:', data);
            
            if (crimeLayer) {
                map.removeLayer(crimeLayer);
            }
            
            if (data.features && data.features.length > 0) {
                console.log(`Processing ${data.features.length} features`);
                
                // Calculate crime value range for color scaling
                const crimeValues = data.features
                    .map(f => {
                        const crimeCount = f.properties.Crimes_11years || 0;
                        console.log(`Feature crime count: ${crimeCount}`);
                        return crimeCount;
                    })
                    .filter(v => v > 0);
                
                console.log('Crime values array:', crimeValues);
                
                if (crimeValues.length === 0) {
                    console.warn('No crime data found in features');
                    // Still show the map but with default styling
                    crimeLayer = L.geoJSON(data, {
                        style: function(feature) {
                            return {
                                fillColor: '#cccccc',
                                weight: 1,
                                opacity: 1,
                                color: 'black',
                                fillOpacity: 0.5
                            };
                        },
                        onEachFeature: function(feature, layer) {
                            const props = feature.properties;
                            const stationName = props.COMPNT_NM || props.STATION || props.NAME || props.Station_Na || 'Unknown';
                            
                            layer.bindPopup(`
                                <div style="font-family: Arial; min-width: 200px;">
                                    <strong style="color: #2c3e50; font-size: 14px;">${stationName}</strong><br>
                                    <hr style="margin: 5px 0;">
                                    <span style="color: #999;">No crime data available</span><br>
                                </div>
                            `);
                        }
                    }).addTo(map);
                    
                    // Fit map to data bounds
                    if (crimeLayer.getBounds().isValid()) {
                        map.fitBounds(crimeLayer.getBounds(), {padding: [20, 20]});
                    }
                    return;
                }
                
                const maxCrime = Math.max(...crimeValues);
                const minCrime = Math.min(...crimeValues);
                
                console.log(`Crime values range: ${minCrime} - ${maxCrime}`);
                
                crimeLayer = L.geoJSON(data, {
                    style: function(feature) {
                        const crimeCount = feature.properties.Crimes_11years || 0;
                        const color = getCrimeColor(crimeCount, maxCrime);
                        console.log(`Feature ${feature.properties.COMPNT_NM || 'Unknown'}: crime=${crimeCount}, color=${color}`);
                        
                        return {
                            fillColor: color,
                            weight: 0.5,
                            opacity: 1,
                            color: 'black',
                            fillOpacity: 0.8
                        };
                    },
                    onEachFeature: function(feature, layer) {
                        const props = feature.properties;
                        const crimeCount = props.Crimes_11years || 0;
                        const stationName = props.COMPNT_NM || props.STATION || props.NAME || props.Station_Na || 'Unknown';
                        
                        layer.bindPopup(`
                            <div style="font-family: Arial; min-width: 200px;">
                                <strong style="color: #2c3e50; font-size: 14px;">${stationName}</strong><br>
                                <hr style="margin: 5px 0;">
                                <span style="color: #e74c3c; font-weight: bold;">Weighted Crime Score: ${crimeCount.toFixed(1)}</span><br>
                                <small style="color: #7f8c8d;">Severity and time weighted</small>
                            </div>
                        `);
                        
                        // Add hover effects
                        layer.on('mouseover', function(e) {
                            this.setStyle({
                                weight: 2,
                                fillOpacity: 0.9
                            });
                        });
                        
                        layer.on('mouseout', function(e) {
                            this.setStyle({
                                weight: 0.5,
                                fillOpacity: 0.8
                            });
                        });
                    }
                }).addTo(map);
                
                // Fit map to data bounds
                if (crimeLayer.getBounds().isValid()) {
                    map.fitBounds(crimeLayer.getBounds(), {padding: [20, 20]});
                }
                
                // Add legend
                addLegend(maxCrime);
                
                console.log(`Heat map loaded successfully with ${data.features.length} features`);
                console.log(`Features with crime data: ${crimeValues.length}`);
                
            } else {
                console.error('No geographic features found in data');
                console.log('Data structure:', data);
                
                // Show error message
                const errorDiv = document.createElement('div');
                errorDiv.innerHTML = `
                    <div style="background: #f8d7da; color: #721c24; padding: 10px; margin: 10px; border-radius: 5px;">
                        <strong>Map Data Error:</strong> No geographic features found. 
                        Check if the shapefile is properly loaded and contains valid geometry data.
                    </div>
                `;
                document.body.appendChild(errorDiv);
            }
        })
        .catch(error => {
            console.error('Error loading map data:', error);
            
            // Show detailed error message
            const errorDiv = document.createElement('div');
            errorDiv.innerHTML = `
                <div style="background: #f8d7da; color: #721c24; padding: 15px; margin: 10px; border-radius: 5px; border: 1px solid #f5c6cb;">
                    <strong>Map Loading Error:</strong><br>
                    ${error.message}<br><br>
                    <small>Please check:</small><br>
                    <small>• Data files are in the correct location</small><br>
                    <small>• Flask server is running</small><br>
                    <small>• Network connection is working</small>
                </div>
            `;
            document.body.appendChild(errorDiv);
            
            // Also show error popup on map
            L.popup()
                .setLatLng([-28.5, 25])
                .setContent(`Error loading crime data: ${error.message}`)
                .openOn(map);
        });
}

// Get color based on crime count (heat map colors)
function getCrimeColor(crimeCount, maxCrime) {
    if (crimeCount === 0) return '#ffffff';
    
    const intensity = crimeCount / maxCrime;
    
    // Create a red heat map similar to your Python visualization
    if (intensity < 0.1) return '#fff5f5';
    if (intensity < 0.2) return '#fed7d7';
    if (intensity < 0.3) return '#feb2b2';
    if (intensity < 0.4) return '#fc8181';
    if (intensity < 0.5) return '#f56565';
    if (intensity < 0.6) return '#e53e3e';
    if (intensity < 0.7) return '#c53030';
    if (intensity < 0.8) return '#9b2c2c';
    if (intensity < 0.9) return '#822727';
    return '#63171b';
}

// Add legend to map
function addLegend(maxCrime) {
    const legend = L.control({position: 'bottomright'});
    
    legend.onAdd = function(map) {
        const div = L.DomUtil.create('div', 'legend');
        div.style.backgroundColor = 'white';
        div.style.padding = '10px';
        div.style.border = '2px solid #ccc';
        div.style.borderRadius = '5px';
        div.style.boxShadow = '0 2px 5px rgba(0,0,0,0.2)';
        
        const ranges = [0, 0.1, 0.2, 0.4, 0.6, 0.8, 1.0];
        const labels = [];
        
        labels.push('<strong>Crime Rate</strong><br>');
        
        for (let i = 0; i < ranges.length - 1; i++) {
            const from = (ranges[i] * maxCrime).toFixed(0);
            const to = (ranges[i + 1] * maxCrime).toFixed(0);
            const color = getCrimeColor(ranges[i + 1] * maxCrime, maxCrime);
            
            labels.push(
                `<div style="display: flex; align-items: center; margin: 2px 0;">
                    <div style="width: 18px; height: 18px; background-color: ${color}; border: 1px solid #000; margin-right: 5px;"></div>
                    <span style="font-size: 12px;">${from}–${to}</span>
                </div>`
            );
        }
        
        div.innerHTML = labels.join('');
        return div;
    };
    
    legend.addTo(map);
}

// Initialize charts
function initializeCharts() {
    createProvinceEvolutionChart();
    createProvinceBarChart();
}

// Create province evolution chart
function createProvinceEvolutionChart() {
    const ctx = document.getElementById('provinceEvolutionChart').getContext('2d');
    
    fetch('/api/province-evolution')
        .then(response => response.json())
        .then(data => {
            const datasets = [];
            const colors = [
                '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
                '#FF9F40', '#C9CBCF', '#4BC0C0', '#36A2EB'
            ];
            
            data.provinces.forEach((province, index) => {
                const provinceData = data.data[index];
                datasets.push({
                    label: province,
                    data: data.years.map(year => provinceData[year] || 0),
                    borderColor: colors[index % colors.length],
                    backgroundColor: colors[index % colors.length] + '20',
                    tension: 0.4,
                    fill: false
                });
            });
            
            provinceEvolutionChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.years,
                    datasets: datasets
                },
                options: {
                    responsive: true,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Crime Evolution by Province Over Time'
                        },
                        legend: {
                            position: 'top'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Crime Count'
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: 'Year'
                            }
                        }
                    }
                }
            });
        })
        .catch(error => console.error('Error creating province evolution chart:', error));
}

// Create province bar chart
function createProvinceBarChart() {
    const ctx = document.getElementById('provinceBarChart').getContext('2d');
    
    fetch(`/api/province-data/${currentYear}`)
        .then(response => response.json())
        .then(data => {
            const provinces = Object.keys(data);
            const counts = provinces.map(province => {
                const provinceData = data[province];
                return provinceData[currentYear] || 0;
            });
            
            provinceBarChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: provinces,
                    datasets: [{
                        label: 'Total Crimes',
                        data: counts,
                        backgroundColor: [
                            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
                            '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF', '#4BC0C0'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        title: {
                            display: true,
                            text: `Total Crimes by Province (${currentYear})`
                        },
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Crime Count'
                            }
                        },
                        x: {
                            ticks: {
                                maxRotation: 45
                            }
                        }
                    }
                }
            });
        })
        .catch(error => console.error('Error creating province bar chart:', error));
}

// Setup event listeners
function setupEventListeners() {
    const yearSelect = document.getElementById('yearSelect');
    const provinceFilter = document.getElementById('provinceFilter');
    const categoryFilter = document.getElementById('categoryFilter');
    
    if (yearSelect) {
        yearSelect.addEventListener('change', function() {
            currentYear = this.value;
            updateDashboard();
        });
    }
    
    if (provinceFilter) {
        provinceFilter.addEventListener('change', function() {
            filterByProvince(this.value);
        });
    }
    
    if (categoryFilter) {
        categoryFilter.addEventListener('change', function() {
            filterByCategory(this.value);
        });
    }
}

// Update entire dashboard
function updateDashboard() {
    updateCategoryList();
    updateProvinceBarChart();
}

// Update category list
function updateCategoryList() {
    fetch(`/api/category-data/${currentYear}`)
        .then(response => response.json())
        .then(data => {
            const categoryList = document.getElementById('categoryList');
            if (categoryList) {
                categoryList.innerHTML = '';
                
                Object.entries(data).forEach(([category, count]) => {
                    const item = document.createElement('div');
                    item.className = 'category-item';
                    item.innerHTML = `
                        <span class="category-name">${category}</span>
                        <span class="category-count">${Math.round(count)}</span>
                    `;
                    categoryList.appendChild(item);
                });
            }
        })
        .catch(error => console.error('Error updating categories:', error));
}

// Update province bar chart
function updateProvinceBarChart() {
    if (provinceBarChart) {
        fetch(`/api/province-data/${currentYear}`)
            .then(response => response.json())
            .then(data => {
                const provinces = Object.keys(data);
                const counts = provinces.map(province => {
                    const provinceData = data[province];
                    return provinceData[currentYear] || 0;
                });
                
                provinceBarChart.data.labels = provinces;
                provinceBarChart.data.datasets[0].data = counts;
                provinceBarChart.options.plugins.title.text = `Total Crimes by Province (${currentYear})`;
                provinceBarChart.update();
            })
            .catch(error => console.error('Error updating bar chart:', error));
    }
}

// Filter functions (to be implemented based on your needs)
function filterByProvince(province) {
    console.log('Filtering by province:', province);
    // Add filtering logic here
}

function filterByCategory(category) {
    console.log('Filtering by category:', category);
    // Add filtering logic here
}
