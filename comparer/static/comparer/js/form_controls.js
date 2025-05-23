/**
 * Form controls for the Weather Compare application
 * Handles dynamic city count selection, form validation, and loading states
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize the form state
    initializeFormState();
    
    // Set up dropdown event listener
    setupDropdownListener();
    
    // Set up form validation and loading states
    setupFormValidation();
    
    // Update weather cards container class based on city count
    updateWeatherCardsLayout();
});

/**
 * Set up dropdown change event listener
 */
function setupDropdownListener() {
    const dropdown = document.getElementById('city-count-dropdown');
    if (dropdown) {
        dropdown.addEventListener('change', function() {
            updateCityCount();
            updateWeatherCardsLayout();
        });
    }
}

/**
 * Initialize the form state based on submitted values
 */
function initializeFormState() {
    // Check if cities 2 and 3 have values and show them if they do
    const city2Input = document.getElementById('city_name_2');
    const city3Input = document.getElementById('city_name_3');
    const dropdown = document.getElementById('city-count-dropdown');
    
    let cityCount = 1;
    
    if (city2Input?.value.trim()) {
        showCity(2);
        cityCount = 2;
    }
    
    if (city3Input?.value.trim()) {
        showCity(3);
        cityCount = 3;
    }
    
    // Set the dropdown to reflect the current state
    if (dropdown) {
        dropdown.value = cityCount.toString();
    }
}

/**
 * Update city count based on dropdown selection
 */
function updateCityCount() {
    const dropdown = document.getElementById('city-count-dropdown');
    const selectedCount = parseInt(dropdown.value);
    
    // Show/hide cities based on selection
    for (let i = 2; i <= 3; i++) {
        if (i <= selectedCount) {
            showCity(i);
        } else {
            hideCity(i);
        }
    }
}

/**
 * Update weather cards container layout class
 */
function updateWeatherCardsLayout() {
    const dropdown = document.getElementById('city-count-dropdown');
    const weatherCardsContainer = document.querySelector('.weather-cards-container');
    
    if (dropdown && weatherCardsContainer) {
        const selectedCount = parseInt(dropdown.value);
        
        // Remove existing count classes
        weatherCardsContainer.classList.remove('one-card', 'two-cards', 'three-cards');
        
        // Add appropriate class
        if (selectedCount === 1) {
            weatherCardsContainer.classList.add('one-card');
        } else if (selectedCount === 2) {
            weatherCardsContainer.classList.add('two-cards');
        } else if (selectedCount === 3) {
            weatherCardsContainer.classList.add('three-cards');
        }
    }
}

/**
 * Show a specific city input
 * @param {number} cityNumber - The city number (2 or 3)
 */
function showCity(cityNumber) {
    const cityElement = document.getElementById(`city-${cityNumber}`);
    const cityInput = document.getElementById(`city_name_${cityNumber}`);
    
    if (cityElement) {
        cityElement.style.display = 'flex';
        if (cityInput) {
            cityInput.required = true;
        }
    }
}

/**
 * Hide a specific city input
 * @param {number} cityNumber - The city number (2 or 3)
 */
function hideCity(cityNumber) {
    const cityElement = document.getElementById(`city-${cityNumber}`);
    const cityInput = document.getElementById(`city_name_${cityNumber}`);
    
    if (cityElement) {
        cityElement.style.display = 'none';
        if (cityInput) {
            cityInput.value = '';
            cityInput.required = false;
        }
    }
}

/**
 * Show loading state
 */
function showLoadingState() {
    const submitButton = document.getElementById('submit-button');
    const processingIndicator = document.querySelector('.processing-indicator');
    
    if (submitButton) {
        submitButton.disabled = true;
        submitButton.classList.add('loading');
        submitButton.textContent = 'Processing...';
    }
    
    if (processingIndicator) {
        processingIndicator.classList.add('show');
    }
    
    // Create and show loading overlay
    const loadingOverlay = document.createElement('div');
    loadingOverlay.className = 'loading-overlay';
    loadingOverlay.innerHTML = `
        <div style="text-align: center;">
            <div class="loading-text">Fetching weather data...</div>
        </div>
    `;
    document.body.appendChild(loadingOverlay);
}

/**
 * Hide loading state
 */
function hideLoadingState() {
    const submitButton = document.getElementById('submit-button');
    const processingIndicator = document.querySelector('.processing-indicator');
    
    // Remove all loading overlays (in case there are multiple)
    document.querySelectorAll('.loading-overlay').forEach(overlay => {
        overlay.remove();
    });
    
    // Remove any "Fetching weather data..." text that might be in the DOM
    document.querySelectorAll('.loading-text').forEach(text => {
        text.remove();
    });
    
    if (submitButton) {
        submitButton.disabled = false;
        submitButton.classList.remove('loading');
        submitButton.textContent = 'Compare Weather';
    }
    
    if (processingIndicator) {
        processingIndicator.classList.remove('show');
    }
}

/**
 * Set up form validation and loading states
 */
function setupFormValidation() {
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function(event) {
            const dropdown = document.getElementById('city-count-dropdown');
            const selectedCount = parseInt(dropdown.value);
            
            // Validate that visible city inputs have values
            for (let i = 1; i <= selectedCount; i++) {
                const cityInput = document.getElementById(`city_name_${i}`);
                if (cityInput && !cityInput.value.trim()) {
                    event.preventDefault();
                    alert(`Please enter a name for City ${i}.`);
                    cityInput.focus();
                    return false;
                }
            }
            
            // Show loading state when form is submitted
            showLoadingState();
            
            return true;
        });
    }
}

// Make functions globally available for onclick handlers
window.updateCityCount = updateCityCount;
window.showLoadingState = showLoadingState;
window.hideLoadingState = hideLoadingState;
