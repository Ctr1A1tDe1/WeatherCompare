/**
 * City Autocomplete Module - Optimized Version
 * Provides autocomplete functionality for city input fields with improved performance
 */

class CityAutocomplete {
    constructor() {
        this.cities = [];
        this.cache = new Map(); // Cache for search results
        this.debounceTimer = null;
    }

    /**
     * Initialize the autocomplete functionality
     * This method handles both setup and async city loading
     */
    async init() {
        try {
            this.setupAutocomplete();
            // Start with common cities immediately
            this.cities = this.getCommonCities();
            // Load full list in background
            this.loadCitiesInBackground();
        } catch (error) {
            console.error('Error initializing CityAutocomplete:', error);
            // Fallback to common cities if initialization fails
            this.cities = this.getCommonCities();
        }
    }

    /**
     * Load city data from the server in background
     */
    async loadCitiesInBackground() {
        try {
            // Use the optimized endpoint with query support
            const response = await fetch('/city-data/?limit=1000');
            
            if (!response.ok) {
                console.warn('Failed to load extended city data, using common cities');
                return;
            }
            
            const fullCityList = await response.json();
            if (Array.isArray(fullCityList) && fullCityList.length > 0) {
                console.log(`Loaded ${fullCityList.length} cities for autocomplete`);
                
                // Pre-process city names for faster searching
                this.cities = fullCityList.map(city => {
                    return {
                        ...city,
                        searchName: city.name.toLowerCase(),
                        displayName: `${city.name}${city.state ? ', ' + city.state : ''}, ${city.country}`
                    };
                });
                
                // Clear cache since we have new data
                this.cache.clear();
            }
        } catch (error) {
            console.warn('Error loading extended city data:', error);
            // Continue using common cities
        }
    }
    
    /**
     * Get a list of common cities for autocomplete
     * This is a fallback method that doesn't require loading the full city.list.json
     */
    getCommonCities() {
        const commonCities = [
            { id: 1, name: "London", country: "GB", state: "" },
            { id: 2, name: "New York", country: "US", state: "NY" },
            { id: 3, name: "Tokyo", country: "JP", state: "" },
            { id: 4, name: "Paris", country: "FR", state: "" },
            { id: 5, name: "Berlin", country: "DE", state: "" },
            { id: 6, name: "Rome", country: "IT", state: "" },
            { id: 7, name: "Madrid", country: "ES", state: "" },
            { id: 8, name: "Moscow", country: "RU", state: "" },
            { id: 9, name: "Beijing", country: "CN", state: "" },
            { id: 10, name: "Sydney", country: "AU", state: "" },
            { id: 11, name: "Bangkok", country: "TH", state: "" },
            { id: 12, name: "Singapore", country: "SG", state: "" },
            { id: 13, name: "Dubai", country: "AE", state: "" },
            { id: 14, name: "Istanbul", country: "TR", state: "" },
            { id: 15, name: "Amsterdam", country: "NL", state: "" },
            { id: 16, name: "Hong Kong", country: "HK", state: "" },
            { id: 17, name: "Seoul", country: "KR", state: "" },
            { id: 18, name: "Chicago", country: "US", state: "IL" },
            { id: 19, name: "Los Angeles", country: "US", state: "CA" },
            { id: 20, name: "San Francisco", country: "US", state: "CA" },
            { id: 21, name: "Mumbai", country: "IN", state: "" },
            { id: 22, name: "Delhi", country: "IN", state: "" },
            { id: 23, name: "Shanghai", country: "CN", state: "" },
            { id: 24, name: "São Paulo", country: "BR", state: "" },
            { id: 25, name: "Mexico City", country: "MX", state: "" },
            { id: 26, name: "Cairo", country: "EG", state: "" },
            { id: 27, name: "Lagos", country: "NG", state: "" },
            { id: 28, name: "Buenos Aires", country: "AR", state: "" },
            { id: 29, name: "Toronto", country: "CA", state: "" },
            { id: 30, name: "Vancouver", country: "CA", state: "" }
        ];
        
        return commonCities.map(city => ({
            ...city,
            searchName: city.name.toLowerCase(),
            displayName: `${city.name}${city.state ? ', ' + city.state : ''}, ${city.country}`
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
        
        // Add event listeners with debouncing for better performance
        inputElement.addEventListener('input', () => {
            this.debouncedShowSuggestions(inputElement, autocompleteContainer);
        });
        
        inputElement.addEventListener('focus', () => {
            this.showSuggestions(inputElement, autocompleteContainer);
        });
        
        // Handle keyboard navigation
        inputElement.addEventListener('keydown', (e) => {
            this.handleKeyNavigation(e, autocompleteContainer);
        });
        
        // Close autocomplete when clicking outside
        document.addEventListener('click', (e) => {
            if (e.target !== inputElement && !autocompleteContainer.contains(e.target)) {
                autocompleteContainer.style.display = 'none';
            }
        });
    }

    /**
     * Debounced version of showSuggestions for better performance
     */
    debouncedShowSuggestions(inputElement, container) {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => {
            this.showSuggestions(inputElement, container);
        }, 150); // 150ms debounce
    }

    /**
     * Handle keyboard navigation in autocomplete
     */
    handleKeyNavigation(event, container) {
        const items = container.querySelectorAll('.autocomplete-item');
        const currentActive = container.querySelector('.autocomplete-item.active');
        
        if (event.key === 'ArrowDown') {
            event.preventDefault();
            const nextItem = currentActive ? currentActive.nextElementSibling : items[0];
            this.setActiveItem(nextItem, container);
        } else if (event.key === 'ArrowUp') {
            event.preventDefault();
            const prevItem = currentActive ? currentActive.previousElementSibling : items[items.length - 1];
            this.setActiveItem(prevItem, container);
        } else if (event.key === 'Enter' && currentActive) {
            event.preventDefault();
            currentActive.click();
        } else if (event.key === 'Escape') {
            container.style.display = 'none';
        }
    }

    /**
     * Set active item in autocomplete list
     */
    setActiveItem(item, container) {
        // Remove active class from all items
        container.querySelectorAll('.autocomplete-item').forEach(i => i.classList.remove('active'));
        // Add active class to selected item
        if (item) {
            item.classList.add('active');
            item.scrollIntoView({ block: 'nearest' });
        }
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
        
        // Hide container if input is empty or too short
        if (!value || value.length < 2) {
            container.style.display = 'none';
            return;
        }
        
        // Check cache first
        const cacheKey = value;
        let matches;
        
        if (this.cache.has(cacheKey)) {
            matches = this.cache.get(cacheKey);
        } else {
            // Find matching cities (limit to 8 results for performance)
            matches = this.findMatches(value, 8);
            // Cache the results
            this.cache.set(cacheKey, matches);
            
            // Limit cache size
            if (this.cache.size > 100) {
                const firstKey = this.cache.keys().next().value;
                this.cache.delete(firstKey);
            }
        }
        
        if (matches.length === 0) {
            container.style.display = 'none';
            return;
        }
        
        // Create suggestion elements
        matches.forEach((city, index) => {
            const item = document.createElement('div');
            item.className = 'autocomplete-item';
            item.textContent = city.displayName;
            
            // Handle click on suggestion
            item.addEventListener('click', () => {
                inputElement.value = city.name;
                container.style.display = 'none';
                inputElement.focus();
            });
            
            container.appendChild(item);
        });
        
        // Show the container
        container.style.display = 'block';
    }

    /**
     * Find exact and prefix matches for a query
     * @param {string} queryLower - Lowercase search query
     * @param {number} limit - Maximum results to return
     * @returns {Array} - Array of matching city objects
     */
    findExactAndPrefixMatches(queryLower, limit) {
        const results = [];
        
        for (const city of this.cities) {
            if (results.length >= limit) break;
            
            if (city.searchName === queryLower) {
                results.unshift(city); // Exact matches first
            } else if (city.searchName.startsWith(queryLower)) {
                results.push(city);
            }
        }
        
        return results;
    }
    
    /**
     * Find substring matches for a query
     * @param {string} queryLower - Lowercase search query
     * @param {number} limit - Maximum results to return
     * @param {Array} existingResults - Results already found
     * @returns {Array} - Array of matching city objects
     */
    findSubstringMatches(queryLower, limit, existingResults) {
        const results = [...existingResults];
        
        for (const city of this.cities) {
            if (results.length >= limit) break;
            
            if (!city.searchName.startsWith(queryLower) && city.searchName.includes(queryLower)) {
                results.push(city);
            }
        }
        
        return results;
    }
    
    /**
     * Find matching cities based on input value
     * @param {string} query - The search query
     * @param {number} limit - Maximum number of results to return
     * @returns {Array} - Array of matching city objects
     */
    findMatches(query, limit) {
        if (!this.cities.length) return [];
        
        const queryLower = query.toLowerCase();
        
        // First pass: exact matches and starts with
        const initialResults = this.findExactAndPrefixMatches(queryLower, limit);
        
        // Second pass: contains matches (if we need more results)
        const finalResults = initialResults.length < limit 
            ? this.findSubstringMatches(queryLower, limit, initialResults)
            : initialResults;
        
        return finalResults.slice(0, limit);
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
