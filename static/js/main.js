document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('search-input');
    const searchButton = document.getElementById('search-button');
    const resultsContainer = document.getElementById('results-container');
    const resultsList = document.getElementById('results-list');
    
    // Map variables
    let map = null;
    let markers = [];
    let activeMarker = null;
    let markerLayerGroup = null;
    
    searchButton.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            performSearch();
        }
    });

    function initMap() {
        if (map) return; // Only initialize once
        
        // Create the map with default view of the US
        map = L.map('map').setView([39.8283, -98.5795], 4);
        
        // Add the tile layer (OpenStreetMap)
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 18
        }).addTo(map);
        
        // Create a layer group for markers
        markerLayerGroup = L.layerGroup().addTo(map);
    }

    function performSearch() {
        const query = searchInput.value.trim();
        if (!query) return;

        // Show loading indicator
        resultsList.innerHTML = '<div class="loading">Searching...</div>';
        resultsContainer.classList.remove('hidden');
        
        // Make API request to backend
        fetch('/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query: query }),
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Search request failed');
            }
            return response.json();
        })
        .then(data => {
            // Initialize map before displaying results
            initMap();
            
            // Clear existing markers
            if (markerLayerGroup) {
                markerLayerGroup.clearLayers();
                markers = [];
            }
            
            displayResults(data);
        })
        .catch(error => {
            resultsList.innerHTML = `<div class="no-results">None found: please ask about another clinical trial</div>`;
        });
    }

    function parseLatLon(latLonStr) {
        if (!latLonStr || latLonStr === "[]") return [];
        
        try {
            // Safely parse the string representation of arrays
            // Handle both single arrays and arrays of arrays
            const parsed = JSON.parse(latLonStr.replace(/'/g, '"'));
            
            // If it's a single [lat, lon] pair
            if (Array.isArray(parsed) && parsed.length === 2 && !Array.isArray(parsed[0])) {
                return [parsed];
            }
            
            // If it's an array of [lat, lon] pairs
            return parsed;
        } catch (e) {
            console.error('Error parsing lat_lon:', e);
            return [];
        }
    }

    function displayResults(results) {
        resultsList.innerHTML = '';
        
        if (results.length === 0) {
            resultsList.innerHTML = '<div class="no-results">None found: please ask about another clinical trial</div>';
            return;
        }

        // Sort by rank (descending)
        results.sort((a, b) => b.rank - a.rank);
        
        // Collect all locations for map bounds
        let allLocations = [];
        
        results.forEach((trial, index) => {
            const resultItem = document.createElement('div');
            resultItem.className = 'result-item';
            resultItem.dataset.trialId = trial.id;
            resultItem.id = `trial-${trial.id}`; // Add ID for scrolling
            
            // Format the result item
            resultItem.innerHTML = `
                <div class="result-header">
                    <span class="result-number">${index + 1}.</span>
                    <a href="https://clinicaltrials.gov/study/${trial.id}" target="_blank" class="result-title">${trial.brief_title}</a>
                </div>
                <div class="result-metadata">
                    <div class="result-field"><span class="field-label">Status:</span> ${trial.status}</div>
                    <div class="result-field"><span class="field-label">Condition Treated:</span> ${trial.conditions_treated}</div>
                    <div class="result-field"><span class="field-label">Type:</span> ${trial.type} ${trial.phase}</div>
                    <div class="result-field"><span class="field-label">Age Eligibility:</span> ${trial.criteria_age}</div>
                    <div class="result-field"><span class="field-label">Sex Eligibility:</span> ${trial.criteria_sex}</div>
                    <div class="result-field"><span class="field-label">Start Date:</span> ${trial.start_date}</div>
                    <div class="result-field"><span class="field-label">Sponsor:</span> ${trial.sponsor}</div>
                </div>
            `;
            
            resultsList.appendChild(resultItem);
            
            // Parse lat_lon data
            const locations = parseLatLon(trial.lat_lon);
            
            if (locations.length > 0) {
                allLocations = allLocations.concat(locations);
                
                // Add markers for each location
                locations.forEach(coords => {
                    if (coords.length === 2 && typeof coords[0] === 'number' && typeof coords[1] === 'number') {
                        const marker = L.marker(coords, {
                            icon: L.divIcon({
                                className: 'trial-marker',
                                iconSize: [12, 12]
                            })
                        }).addTo(markerLayerGroup);
                        
                        // Store reference to the trial and index
                        marker.trialId = trial.id;
                        marker.resultIndex = index + 1;
                        
                        // Create popup with just the title as a link
                        const popupContent = document.createElement('div');
                        popupContent.innerHTML = `<a href="#" class="popup-link" data-trial-id="${trial.id}"><strong>${marker.resultIndex}. ${trial.brief_title}</strong></a>`;
                        
                        // Add click event to the popup content
                        marker.bindPopup(popupContent);
                        
                        // Store the marker
                        markers.push(marker);
                    }
                });
            }
            
            // Add event listeners for hover effects
            resultItem.addEventListener('mouseenter', function() {
                highlightTrial(trial.id, true);
            });
            
            resultItem.addEventListener('mouseleave', function() {
                highlightTrial(trial.id, false);
            });
            
            resultItem.addEventListener('click', function() {
                focusOnTrial(trial.id);
            });
        });
        
        // Add event listener for popup links (using event delegation)
        map.on('popupopen', function(e) {
            const popup = e.popup;
            const container = popup.getContent();
            
            if (container instanceof HTMLElement) {
                const link = container.querySelector('.popup-link');
                if (link) {
                    link.addEventListener('click', function(e) {
                        e.preventDefault();
                        const trialId = this.getAttribute('data-trial-id');
                        scrollToResult(trialId);
                    });
                }
            }
        });
        
        // Set map bounds to fit all markers if we have locations
        if (allLocations.length > 0) {
            try {
                const bounds = L.latLngBounds(allLocations);
                map.fitBounds(bounds, { padding: [50, 50] });
            } catch (e) {
                console.error('Error setting bounds:', e);
                // Fallback to US view
                map.setView([39.8283, -98.5795], 4);
            }
        }
    }
    
    function scrollToResult(trialId) {
        const resultItem = document.getElementById(`trial-${trialId}`);
        if (resultItem) {
            // Highlight the item
            highlightTrial(trialId, true);
            
            // Scroll the item into view with smooth behavior
            resultItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
            
            // Add a temporary flash effect
            resultItem.classList.add('flash');
            setTimeout(() => {
                resultItem.classList.remove('flash');
            }, 1500);
        }
    }
    
    function highlightTrial(trialId, isHighlighted) {
        // Highlight/unhighlight result item
        const resultItems = document.querySelectorAll('.result-item');
        resultItems.forEach(item => {
            if (item.dataset.trialId === trialId) {
                if (isHighlighted) {
                    item.classList.add('active');
                } else {
                    item.classList.remove('active');
                }
            }
        });
        
        // Highlight/unhighlight markers
        markers.forEach(marker => {
            if (marker.trialId === trialId) {
                // Update marker style
                if (isHighlighted) {
                    marker._icon.classList.add('active');
                    // Remember active marker for zoom
                    activeMarker = marker;
                } else {
                    marker._icon.classList.remove('active');
                    activeMarker = null;
                }
            }
        });
    }
    
    function focusOnTrial(trialId) {
        // Find all markers for this trial
        const trialMarkers = markers.filter(marker => marker.trialId === trialId);
        
        if (trialMarkers.length > 0) {
            // If multiple markers, create bounds
            if (trialMarkers.length > 1) {
                const locations = trialMarkers.map(marker => marker.getLatLng());
                const bounds = L.latLngBounds(locations);
                map.fitBounds(bounds, { padding: [50, 50] });
            } else {
                // Single marker
                map.setView(trialMarkers[0].getLatLng(), 10);
            }
            
            // Open popup for the first marker
            trialMarkers[0].openPopup();
        }
    }
});