document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('search-input');
    const searchButton = document.getElementById('search-button');
    const resultsContainer = document.getElementById('results-container');
    const resultsList = document.getElementById('results-list');
    const searchSuggestions = document.getElementById('search-suggestions');
    
    // Map variables
    let map = null;
    let markers = [];
    let activeMarker = null;
    let markerLayerGroup = null;
    let searchLocationMarker = null;
    let searchRadiusCircle = null;
    
    // Pool of search suggestions
    const suggestionPool = [
        {
            query: "breast cancer trials within 25 miles of Boston",
            label: "Breast cancer trials in Boston",
            icon: "🔬"
        },
        {
            query: "diabetes studies for adults in New York City",
            label: "Diabetes studies in NYC",
            icon: "💉"
        },
        {
            query: "pediatric asthma clinical trials recruiting now",
            label: "Pediatric asthma trials",
            icon: "👶"
        },
        {
            query: "phase 3 depression trials for women",
            label: "Depression trials for women",
            icon: "🧠"
        },
        {
            query: "observational studies for heart disease within 50 miles of Chicago",
            label: "Heart disease in Chicago",
            icon: "❤️"
        },
        {
            query: "alzheimer's trials for older adults",
            label: "Alzheimer's trials",
            icon: "🧓"
        },
        {
            query: "lung cancer immunotherapy trials phase 2",
            label: "Lung cancer immunotherapy",
            icon: "🫁"
        },
        {
            query: "rheumatoid arthritis studies in Los Angeles",
            label: "Arthritis studies in LA",
            icon: "🦴"
        },
        {
            query: "migraine prevention trials recruiting",
            label: "Migraine prevention trials",
            icon: "🤕"
        },
        {
            query: "COPD clinical trials for men over 60",
            label: "COPD trials for older men",
            icon: "🫁"
        },
        {
            query: "autism spectrum disorder studies for children",
            label: "Autism studies for children",
            icon: "🧩"
        },
        {
            query: "multiple sclerosis trials within 100 miles of Seattle",
            label: "MS trials in Seattle area",
            icon: "🧠"
        },
        {
            query: "type 2 diabetes prevention studies",
            label: "Diabetes prevention studies",
            icon: "🩺"
        },
        {
            query: "breast cancer vaccine trials phase 1",
            label: "Breast cancer vaccine trials",
            icon: "💊"
        },
        {
            query: "parkinson's disease observational studies",
            label: "Parkinson's studies",
            icon: "🧠"
        },
        {
            query: "prostate cancer trials for men over 50",
            label: "Prostate cancer trials",
            icon: "🔬"
        },
        {
            query: "anxiety disorder studies recruiting in Houston",
            label: "Anxiety studies in Houston",
            icon: "😰"
        },
        {
            query: "kidney disease trials phase 2 or 3",
            label: "Kidney disease trials",
            icon: "🩺"
        },
        {
            query: "lupus clinical trials for young adults",
            label: "Lupus trials for young adults",
            icon: "🦴"
        },
        {
            query: "stroke prevention studies in Philadelphia",
            label: "Stroke prevention in Philly",
            icon: "🧠"
        },
        {
            query: "ovarian cancer early detection trials",
            label: "Ovarian cancer detection",
            icon: "🔬"
        },
        {
            query: "sleep apnea device trials recruiting",
            label: "Sleep apnea device trials",
            icon: "😴"
        },
        {
            query: "IBS clinical trials in San Diego",
            label: "IBS trials in San Diego",
            icon: "🩺"
        },
        {
            query: "psoriasis treatment studies phase 3",
            label: "Psoriasis treatment studies",
            icon: "🩹"
        },
        {
            query: "epilepsy medication trials for children",
            label: "Epilepsy trials for children",
            icon: "⚡"
        },
        {
            query: "COVID-19 vaccine trials in Miami",
            label: "COVID vaccine in Miami",
            icon: "💉"
        },
        {
            query: "melanoma immunotherapy trials in Denver",
            label: "Melanoma trials in Denver",
            icon: "🔬"
        },
        {
            query: "fibromyalgia studies within 50 miles of Atlanta",
            label: "Fibromyalgia in Atlanta",
            icon: "🩺"
        },
        {
            query: "macular degeneration trials in Phoenix",
            label: "Eye disease in Phoenix",
            icon: "👁️"
        },
        {
            query: "obesity intervention studies in Dallas",
            label: "Obesity studies in Dallas",
            icon: "⚖️"
        },
        {
            query: "PTSD clinical trials for veterans in San Antonio",
            label: "PTSD trials in San Antonio",
            icon: "🎖️"
        }
    ];
    
    // Function to get random suggestions
    function getRandomSuggestions(count = 3) {
        const shuffled = [...suggestionPool].sort(() => 0.5 - Math.random());
        return shuffled.slice(0, count);
    }
    
    // Display random suggestions on page load
    function displaySuggestions() {
        const suggestionsContainer = document.querySelector('.suggestion-chips');
        suggestionsContainer.innerHTML = ''; // Clear existing suggestions
        
        const randomSuggestions = getRandomSuggestions(3);
        
        randomSuggestions.forEach(suggestion => {
            const chip = document.createElement('button');
            chip.className = 'suggestion-chip';
            chip.setAttribute('data-query', suggestion.query);
            chip.innerHTML = `<span class="chip-icon">${suggestion.icon}</span> ${suggestion.label}`;
            chip.addEventListener('click', function() {
                searchInput.value = suggestion.query;
                performSearch();
            });
            suggestionsContainer.appendChild(chip);
        });
    }
    
    // Display suggestions on page load
    displaySuggestions();
    
    // Smart autocomplete suggestions
    const conditionKeywords = [
        'cancer', 'diabetes', 'heart disease', 'alzheimer', 'parkinson', 'asthma', 
        'COPD', 'arthritis', 'depression', 'anxiety', 'autism', 'epilepsy',
        'stroke', 'kidney disease', 'liver disease', 'lupus', 'multiple sclerosis',
        'cystic fibrosis', 'sickle cell', 'HIV', 'hepatitis', 'migraine'
    ];
    
    const trialTypes = [
        'phase 1', 'phase 2', 'phase 3', 'phase 4', 'observational', 'interventional',
        'recruiting', 'enrolling', 'pediatric', 'adult', 'older adult'
    ];
    
    const locations = [
        'near me', 'within 10 miles', 'within 25 miles', 'within 50 miles', 'within 100 miles',
        'in New York', 'in Los Angeles', 'in Chicago', 'in Houston', 'in Phoenix',
        'in Philadelphia', 'in San Antonio', 'in San Diego', 'in Dallas', 'in Boston'
    ];
    
    // Add input event listener for smart suggestions
    let typingTimer;
    searchInput.addEventListener('input', function() {
        clearTimeout(typingTimer);
        const value = this.value.toLowerCase();
        
        // Don't show suggestions if query is too short
        if (value.length < 3) return;
        
        typingTimer = setTimeout(() => {
            // This is where you could show inline suggestions
            // For now, we'll just log what could be suggested
            const possibleCompletions = [];
            
            // Check for condition matches
            conditionKeywords.forEach(condition => {
                if (condition.startsWith(value) || value.includes(condition.substring(0, 3))) {
                    possibleCompletions.push(condition);
                }
            });
            
            // Check for location patterns
            if (value.includes('near') || value.includes('in') || value.includes('within')) {
                locations.forEach(location => {
                    if (!value.includes(location) && location.includes(value.split(' ').pop())) {
                        possibleCompletions.push(value + ' ' + location);
                    }
                });
            }
            
            console.log('Possible completions:', possibleCompletions);
        }, 300);
    });
    
    // Display recent searches
    function displayRecentSearches() {
        const recentSearches = JSON.parse(localStorage.getItem('recentSearches') || '[]');
        const recentSearchesContainer = document.getElementById('recent-searches');
        const recentSearchesList = document.getElementById('recent-searches-list');
        
        if (recentSearches.length > 0) {
            recentSearchesContainer.classList.remove('hidden');
            recentSearchesList.innerHTML = '';
            
            recentSearches.forEach(search => {
                const chip = document.createElement('button');
                chip.className = 'suggestion-chip';
                chip.setAttribute('data-query', search);
                chip.innerHTML = `<span class="chip-icon">🕐</span> ${search}`;
                chip.addEventListener('click', function() {
                    searchInput.value = search;
                    performSearch();
                });
                recentSearchesList.appendChild(chip);
            });
        }
    }
    
    // Display recent searches on page load
    displayRecentSearches();
    
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

    // Function to calculate zoom level based on radius in miles
    function getZoomLevelFromRadius(radiusMiles) {
        // Approximate zoom levels for different radii
        if (radiusMiles <= 5) return 12;
        if (radiusMiles <= 10) return 11;
        if (radiusMiles <= 25) return 10;
        if (radiusMiles <= 50) return 9;
        if (radiusMiles <= 100) return 8;
        if (radiusMiles <= 200) return 7;
        if (radiusMiles <= 300) return 6;
        if (radiusMiles <= 400) return 5;
        if (radiusMiles <= 500) return 4;
        return 4;
    }

    // Function to geocode location using Nominatim
    function geocodeLocation(locationQuery) {
        const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(locationQuery)}&format=json&limit=1`;
        const headers = {"User-Agent": "ClinicalTrialsSearchApp/1.0"};
        
        return fetch(url, { headers })
            .then(response => response.json())
            .then(results => {
                if (results && results.length > 0) {
                    return [parseFloat(results[0].lat), parseFloat(results[0].lon)];
                }
                return null;
            })
            .catch(error => {
                console.error('Geocoding error:', error);
                return null;
            });
    }

    // Handle recent searches
    function saveRecentSearch(query) {
        let recentSearches = JSON.parse(localStorage.getItem('recentSearches') || '[]');
        
        // Remove duplicates and limit to 5 recent searches
        recentSearches = recentSearches.filter(search => search !== query);
        recentSearches.unshift(query);
        recentSearches = recentSearches.slice(0, 5);
        
        localStorage.setItem('recentSearches', JSON.stringify(recentSearches));
    }
    
    function performSearch() {
        const query = searchInput.value.trim();
        if (!query) return;

        // Save to recent searches
        saveRecentSearch(query);
        
        // Hide search suggestions
        searchSuggestions.style.display = 'none';
        
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
            
            // Clear existing markers and overlays
            if (markerLayerGroup) {
                markerLayerGroup.clearLayers();
                markers = [];
            }
            if (searchLocationMarker) {
                map.removeLayer(searchLocationMarker);
                searchLocationMarker = null;
            }
            if (searchRadiusCircle) {
                map.removeLayer(searchRadiusCircle);
                searchRadiusCircle = null;
            }
            
            displayResults(data);
            
            // Update recent searches display
            displayRecentSearches();
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

    async function displayResults(results) {
        resultsList.innerHTML = '';
        
        if (results.length === 0) {
            resultsList.innerHTML = '<div class="no-results">None found: please ask about another clinical trial</div>';
            document.getElementById('search-summary-banner').classList.add('hidden');
            return;
        }

        // Sort by rank (descending)
        results.sort((a, b) => b.rank - a.rank);
        
        // Get search parameters from the first result
        const searchParams = results.length > 0 ? results[0].search_params : null;
        
        // Handle map centering based on search location
        if (searchParams && searchParams.location && searchParams.distance_miles > 0) {
            // Geocode the search location
            const searchCoords = await geocodeLocation(searchParams.location);
            
            if (searchCoords) {
                // Center map on search location with appropriate zoom
                const zoomLevel = getZoomLevelFromRadius(searchParams.distance_miles);
                map.setView(searchCoords, zoomLevel);
                
                // Add a marker for the search location
                searchLocationMarker = L.marker(searchCoords, {
                    icon: L.icon({
                        iconUrl: 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9ImN1cnJlbnRDb2xvciIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxwYXRoIGQ9Ik0yMSAxMGMwIDctOSAxMy05IDEzcy05LTYtOS0xM2E5IDkgMCAwIDEgMTggMHoiLz48Y2lyY2xlIGN4PSIxMiIgY3k9IjEwIiByPSIzIi8+PC9zdmc+',
                        iconSize: [30, 30],
                        iconAnchor: [15, 30],
                        popupAnchor: [0, -30]
                    })
                }).addTo(map);
                
                searchLocationMarker.bindPopup(`<strong>Search Location:</strong><br>${searchParams.location}`);
                
                // Add a circle to show the search radius
                searchRadiusCircle = L.circle(searchCoords, {
                    radius: searchParams.distance_miles * 1609.34, // Convert miles to meters
                    color: '#2962ff',
                    fillColor: '#2962ff',
                    fillOpacity: 0.1,
                    weight: 2
                }).addTo(map);
            }
        }
        
        // Show search summary banner
        if (searchParams) {
            // Build a human-readable summary
            let summary = `Showing the top ${results.length} matching `;
            
            // Trial type
            if (searchParams.type) {
                summary += searchParams.type.toLowerCase() + " ";
            }
            
            // Disease/condition - UPDATED to include the original query
            if (searchParams.semantic_phrases) {
                summary += `trials on ${searchParams.semantic_phrases}`;
            } else {
                summary += "trials";
            }
            
            // Patient criteria - UPDATED to properly show in summary
            let patientCriteria = [];
            if (searchParams.criteria_sex === 'FEMALE') {
                patientCriteria.push("for women");
            } else if (searchParams.criteria_sex === 'MALE') {
                patientCriteria.push("for men");
            }
            
            if (searchParams.criteria_age === 'CHILD') {
                patientCriteria.push("for children");
            } else if (searchParams.criteria_age === 'ADULT') {
                patientCriteria.push("for adults");
            } else if (searchParams.criteria_age === 'OLDER_ADULT') {
                patientCriteria.push("for older adults");
            }
            
            // Add patient criteria to summary
            if (patientCriteria.length > 0) {
                summary += " " + patientCriteria.join(" ");
            }
            
            // Location and distance
            if (searchParams.location) {
                summary += ` that are within ${searchParams.distance_miles} miles of ${searchParams.location}`;
            }
            
            // Display the summary
            const summaryBanner = document.getElementById('search-summary-banner');
            document.getElementById('search-summary-text').textContent = summary;
            summaryBanner.classList.remove('hidden');
        } else {
            document.getElementById('search-summary-banner').classList.add('hidden');
        }
        
        // Add trial markers
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
        
        // If no search location was specified, fit bounds to all markers
        if (!searchParams || !searchParams.location || searchParams.distance_miles === 0) {
            const allLocations = [];
            markers.forEach(marker => {
                allLocations.push(marker.getLatLng());
            });
            
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
                    // Bring marker to front
                    marker.setZIndexOffset(1000);
                    // Remember active marker for zoom
                    activeMarker = marker;
                } else {
                    marker._icon.classList.remove('active');
                    marker.setZIndexOffset(0);
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
                // Single marker - zoom in closer
                map.setView(trialMarkers[0].getLatLng(), 12);
            }
            
            // Open popup for the first marker
            trialMarkers[0].openPopup();
        }
    }
});