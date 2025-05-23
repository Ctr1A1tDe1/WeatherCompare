/**
 * Form controls for the Weather Compare application
 * Handles dynamic city count selection and form validation
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize the form state
    initializeFormState();
    
    // Set up dropdown event listener
    setupDropdownListener();
    
    // Set up form validation
    setupFormValidation();
});

/**
 * Set up dropdown change event listener
 */
function setupDropdownListener() {
    const dropdown = document.getElementById('city-count-dropdown');
    if (dropdown) {
        dropdown.addEventListener('change', updateCityCount);
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
    
    if (city2Input && city2Input.value.trim()) {
        showCity(2);
        cityCount = 2;
    }
    
    if (city3Input && city3Input.value.trim()) {
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
 * Set up form validation
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
            
            return true;
        });
    }
}

// Make functions globally available for onclick handlers
window.updateCityCount = updateCityCount;
