/**
 * Form controls for the Weather Compare application
 * Handles toggling of city inputs, year restrictions, and form validation
 */

document.addEventListener('DOMContentLoaded', function() {
    // Get toggle checkboxes
    const enableCity2Checkbox = document.getElementById('enable-city2');
    const enableCity3Checkbox = document.getElementById('enable-city3');
    
    // Get city input elements
    const city2Input = document.getElementById('city_name_2');
    const city3Input = document.getElementById('city_name_3');
    const year1Input = document.getElementById('year_1');
    const year2Input = document.getElementById('year_2');
    const year3Input = document.getElementById('year_3');
    
    // Get all city2 and city3 related elements
    const city2Elements = document.querySelectorAll('.city2-input');
    const city3Elements = document.querySelectorAll('.city3-input');
    
    // Set up year restrictions
    setupYearRestrictions();
    
    // Function to toggle city 2 inputs
    function toggleCity2() {
        const isEnabled = enableCity2Checkbox.checked;
        
        // Toggle required attribute
        city2Input.required = isEnabled;
        year2Input.required = isEnabled;
        
        // Toggle disabled state
        city2Input.disabled = !isEnabled;
        year2Input.disabled = !isEnabled;
        
        // Toggle visibility of related elements
        city2Elements.forEach(element => {
            element.style.opacity = isEnabled ? '1' : '0.5';
            element.style.pointerEvents = isEnabled ? 'auto' : 'none';
        });
        
        // If city 2 is disabled, also disable city 3
        if (!isEnabled && enableCity3Checkbox.checked) {
            enableCity3Checkbox.checked = false;
            toggleCity3();
        }
    }
    
    // Function to toggle city 3 inputs
    function toggleCity3() {
        const isEnabled = enableCity3Checkbox.checked;
        
        // Toggle required attribute
        city3Input.required = isEnabled;
        year3Input.required = isEnabled;
        
        // Toggle disabled state
        city3Input.disabled = !isEnabled;
        year3Input.disabled = !isEnabled;
        
        // Toggle visibility of related elements
        city3Elements.forEach(element => {
            element.style.opacity = isEnabled ? '1' : '0.5';
            element.style.pointerEvents = isEnabled ? 'auto' : 'none';
        });
        
        // City 3 can only be enabled if city 2 is enabled
        if (isEnabled && !enableCity2Checkbox.checked) {
            enableCity2Checkbox.checked = true;
            toggleCity2();
        }
    }
    
    // Add event listeners to checkboxes
    if (enableCity2Checkbox) {
        enableCity2Checkbox.addEventListener('change', toggleCity2);
        // Initialize state
        toggleCity2();
    }
    
    if (enableCity3Checkbox) {
        enableCity3Checkbox.addEventListener('change', toggleCity3);
        // Initialize state
        toggleCity3();
    }
    
    /**
     * Set up year input restrictions
     * Ensures years cannot be greater than current year - 1
     */
    function setupYearRestrictions() {
        const currentYear = new Date().getFullYear();
        const maxYear = currentYear - 1;
        
        // Set max attribute for all year inputs
        [year1Input, year2Input, year3Input].forEach(input => {
            if (input) {
                input.setAttribute('max', maxYear);
                
                // Add event listener to enforce max year
                input.addEventListener('change', function() {
                    if (parseInt(this.value) > maxYear) {
                        this.value = maxYear;
                    }
                });
            }
        });
    }
    
    // Form validation
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function(event) {
            // Validate that if city 3 is enabled, city 2 must also be enabled
            if (enableCity3Checkbox && enableCity3Checkbox.checked && 
                enableCity2Checkbox && !enableCity2Checkbox.checked) {
                event.preventDefault();
                alert('City 3 can only be enabled if City 2 is also enabled.');
                return false;
            }
            
            // Validate that required fields are filled
            if (enableCity2Checkbox && enableCity2Checkbox.checked) {
                if (!city2Input.value.trim()) {
                    event.preventDefault();
                    alert('Please enter a name for City 2.');
                    city2Input.focus();
                    return false;
                }
            }
            
            if (enableCity3Checkbox && enableCity3Checkbox.checked) {
                if (!city3Input.value.trim()) {
                    event.preventDefault();
                    alert('Please enter a name for City 3.');
                    city3Input.focus();
                    return false;
                }
            }
            
            // Validate year inputs
            const currentYear = new Date().getFullYear();
            const maxYear = currentYear - 1;
            
            const validateYear = (input) => {
                if (input && input.value) {
                    const yearValue = parseInt(input.value);
                    if (yearValue > maxYear) {
                        event.preventDefault();
                        alert(`Year cannot be greater than ${maxYear}.`);
                        input.focus();
                        return false;
                    }
                }
                return true;
            };
            
            // Check all year inputs
            if (!validateYear(year1Input) || 
                (enableCity2Checkbox.checked && !validateYear(year2Input)) ||
                (enableCity3Checkbox.checked && !validateYear(year3Input))) {
                return false;
            }
            
            return true;
        });
    }
});
