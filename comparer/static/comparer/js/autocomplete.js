/**
 * City Autocomplete Module
 * Provides autocomplete functionality for city input fields
 */

class CityAutocomplete {
    constructor() {
        this.cities = [];
    }

    /**
     * Initialize the autocomplete functionality
     * This method handles both setup and async city loading
     */
    async init() {
        try {
            this.setupAutocomplete();
            await this.loadCities();
        } catch (error) {
            console.error('Error initializing CityAutocomplete:', error);
            // Fallback to common cities if initialization fails
            this.cities = this.getCommonCities();
        }
    }

    /**
     * Load city data from the server
     */
    async loadCities() {
        try {
            // Start with a basic list of cities while waiting for the full list
            this.cities = this.getCommonCities();
            
            // Try to load the full list from the server
            let response = await fetch('/static/city-data/');
            
            // If that fails, try the alternative URL
            if (!response.ok) {
                console.log('First URL failed, trying alternative URL...');
                response = await fetch('/city-data/');
                if (!response.ok) {
                    throw new Error(`Failed to load city data: ${response.status}`);
                }
            }
            
            const fullCityList = await response.json();
            if (Array.isArray(fullCityList) && fullCityList.length > 0) {
                console.log(`Loaded ${fullCityList.length} cities for autocomplete`);
                
                // Pre-process city names for faster searching
                this.cities = fullCityList.map(city => {
                    return {
                        ...city,
                        searchName: city.name.toLowerCase()
                    };
                });
            }
        } catch (error) {
            console.error('Error loading city data:', error);
            // Already using fallback list from getCommonCities()
        }
    }
    
    /**
     * Get a list of common cities for autocomplete
     * This is a fallback method that doesn't require loading the full city.list.json
     */
    getCommonCities() {
        return [
            { id: 1, name: "London", country: "GB" },
            { id: 2, name: "New York", country: "US" },
            { id: 3, name: "Tokyo", country: "JP" },
            { id: 4, name: "Paris", country: "FR" },
            { id: 5, name: "Berlin", country: "DE" },
            { id: 6, name: "Rome", country: "IT" },
            { id: 7, name: "Madrid", country: "ES" },
            { id: 8, name: "Moscow", country: "RU" },
            { id: 9, name: "Beijing", country: "CN" },
            { id: 10, name: "Sydney", country: "AU" },
            { id: 11, name: "Bangkok", country: "TH" },
            { id: 12, name: "Singapore", country: "SG" },
            { id: 13, name: "Dubai", country: "AE" },
            { id: 14, name: "Istanbul", country: "TR" },
            { id: 15, name: "Amsterdam", country: "NL" },
            { id: 16, name: "Hong Kong", country: "HK" },
            { id: 17, name: "Seoul", country: "KR" },
            { id: 18, name: "Chicago", country: "US" },
            { id: 19, name: "Los Angeles", country: "US" },
            { id: 20, name: "San Francisco", country: "US" }
        ].map(city => ({
            ...city,
            searchName: city.name.toLowerCase()
        }));
    }

    /**
     * Set up autocomplete for all city input fields
     */
    setupAutocomplete() {
        // Function to initialize autocomplete
        const initAutocomplete = () => {
            console.log('Setting up autocomplete for city inputs');
            // Find all city input fields
            const cityInputs = document.querySelectorAll('input[id^="city_name_"]');
            console.log(`Found ${cityInputs.length} city input fields`);
            
            // Set up autocomplete for each input
            cityInputs.forEach(input => {
                console.log(`Setting up autocomplete for: ${input.id}`);
                this.attachAutocomplete(input);
            });
        };
        
        // Try to initialize immediately if DOM is already loaded
        if (document.readyState === 'complete' || document.readyState === 'interactive') {
            setTimeout(initAutocomplete, 1);
        } else {
            // Otherwise wait for DOM to be fully loaded
            document.addEventListener('DOMContentLoaded', initAutocomplete);
        }
        
        // Also set up a fallback to ensure it runs
        window.addEventListener('load', initAutocomplete);
    }

    /**
     * Attach autocomplete functionality to a specific input element
     * @param {HTMLInputElement} inputElement - The input element to attach autocomplete to
     */
    attachAutocomplete(inputElement) {
        // Create autocomplete container
        const autocompleteContainer = document.createElement('div');
        autocompleteContainer.className = 'autocomplete-items';
        autocompleteContainer.style.display = 'none';
        inputElement.parentNode.appendChild(autocompleteContainer);
        
        // Add event listeners
        inputElement.addEventListener('input', () => {
            this.showSuggestions(inputElement, autocompleteContainer);
        });
        
        inputElement.addEventListener('focus', () => {
            this.showSuggestions(inputElement, autocompleteContainer);
        });
        
        // Close autocomplete when clicking outside
        document.addEventListener('click', (e) => {
            if (e.target !== inputElement) {
                autocompleteContainer.style.display = 'none';
            }
        });
    }

    /**
     * Show suggestions based on input value
     * @param {HTMLInputElement} inputElement - The input element
     * @param {HTMLElement} container - The container for suggestions
     */
    showSuggestions(inputElement, container) {
        const value = inputElement.value.trim().toLowerCase();
        
        // Clear previous suggestions
        container.innerHTML = '';
        
        // Hide container if input is empty
        if (!value) {
            container.style.display = 'none';
            return;
        }
        
        // Find matching cities (limit to 10 results for performance)
        const matches = this.findMatches(value, 10);
        
        if (matches.length === 0) {
            container.style.display = 'none';
            return;
        }
        
        // Create suggestion elements
        matches.forEach(city => {
            const item = document.createElement('div');
            item.className = 'autocomplete-item';
            
            // Format city name with country
            const displayName = `${city.name}${city.state ? ', ' + city.state : ''}, ${city.country}`;
            item.textContent = displayName;
            
            // Handle click on suggestion
            item.addEventListener('click', () => {
                inputElement.value = city.name;
                container.style.display = 'none';
            });
            
            container.appendChild(item);
        });
        
        // Show the container
        container.style.display = 'block';
    }

    /**
     * Find matching cities based on input value
     * @param {string} query - The search query
     * @param {number} limit - Maximum number of results to return
     * @returns {Array} - Array of matching city objects
     */
    findMatches(query, limit) {
        if (!this.cities.length) return [];
        
        // Improved matching algorithm with better performance
        // First check for starts with (higher priority)
        const startsWithMatches = this.cities
            .filter(city => city.searchName.startsWith(query))
            .slice(0, limit);
            
        // If we have enough matches that start with the query, return those
        if (startsWithMatches.length >= limit) {
            return startsWithMatches;
        }
        
        // Otherwise, add matches that include the query anywhere in the name
        const containsMatches = this.cities
            .filter(city => !city.searchName.startsWith(query) && city.searchName.includes(query))
            .slice(0, limit - startsWithMatches.length);
            
        return [...startsWithMatches, ...containsMatches];
    }
}

// Initialize autocomplete when the script loads
(async () => {
    try {
        const cityAutocomplete = new CityAutocomplete();
        await cityAutocomplete.init();
        console.log('CityAutocomplete initialized successfully');
    } catch (error) {
        console.error('Failed to initialize CityAutocomplete:', error);
    }
})();
