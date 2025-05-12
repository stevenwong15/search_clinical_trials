document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('search-input');
    const searchButton = document.getElementById('search-button');
    const resultsContainer = document.getElementById('results-container');
    const resultsList = document.getElementById('results-list');

    searchButton.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            performSearch();
        }
    });

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
            displayResults(data);
        })
        .catch(error => {
            resultsList.innerHTML = `<div class="error">Error: ${error.message}</div>`;
        });
    }

    function displayResults(results) {
        resultsList.innerHTML = '';
        
        if (results.length === 0) {
            resultsList.innerHTML = '<div class="no-results">No clinical trials found matching your query.</div>';
            return;
        }

        // Sort by rank (descending)
        results.sort((a, b) => b.rank - a.rank);
        
        results.forEach((trial, index) => {
            const resultItem = document.createElement('div');
            resultItem.className = 'result-item';
            
            // Format the result item
            resultItem.innerHTML = `
                <div class="result-number">${index + 1}.</div>
                <a href="https://clinicaltrials.gov/study/${trial.id}" target="_blank" class="result-title">${trial.title}</a>
                <div class="result-metadata">
                    <div class="result-field"><span class="field-label">Purpose:</span> ${trial.purpose}</div>
                    <div class="result-field"><span class="field-label">Status:</span> ${trial.status}</div>
                    <div class="result-field"><span class="field-label">Type:</span> ${trial.type}</div>
                    <div class="result-field"><span class="field-label">Sponsor:</span> ${trial.sponsor}</div>
                </div>
            `;
            
            resultsList.appendChild(resultItem);
        });
    }
}); 