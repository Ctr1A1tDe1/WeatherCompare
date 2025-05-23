/**
 * Weather Compare - Chart Generation Module
 * Handles the creation and rendering of weather comparison charts
 * 
 * Safely parses JSON data from an HTML script tag.
 * @param {string} elementId - The ID of the script tag containing JSON data.
 * @param {boolean} expectArray - Whether the parsed data is expected to be an array.
 * @returns {object|Array|null} Parsed JSON data or null if parsing fails, element not found, or type mismatch.
 */
function getJsonData(elementId, expectArray = false) {
    const element = document.getElementById(elementId);
    if (!element) {
        // This is expected during initial page load - no need for warning
        return expectArray ? [] : null;
    }
    if (element.textContent.trim() === "") {
        return expectArray ? [] : null;
    }
    try {
        const parsedData = JSON.parse(element.textContent);
        
        if (expectArray && !Array.isArray(parsedData)) {
            console.warn(`Data from element ID '${elementId}' was expected to be an array, but received:`, typeof parsedData, parsedData);
            return [];
        }
        return parsedData;
    } catch (e) {
        console.error(`Error parsing JSON from element ID '${elementId}':`, e, "\nContent was:", element.textContent);
        return expectArray ? [] : null;
    }
}

/**
 * Creates chart datasets for temperature and precipitation.
 * @param {Array} cityChartData - Array of city data objects.
 * @returns {object} Object containing { datasetsTemp, datasetsPrecip }.
 */
function prepareChartDatasets(cityChartData) {
    // Safeguard: Ensure cityChartData is an array before trying to use .forEach
    if (!Array.isArray(cityChartData)) {
        console.error("prepareChartDatasets was called with a non-array value for cityChartData:", cityChartData);
        return { datasetsTemp: [], datasetsPrecip: [] }; // Return empty datasets to prevent further errors
    }

    const datasetsTemp = [];
    const datasetsPrecip = [];
    
    // Enhanced color palette to support more cities
    const lineColors = [
        'rgba(255, 99, 132, 1)',   // Red
        'rgba(54, 162, 235, 1)',   // Blue
        'rgba(75, 192, 192, 1)',   // Green
        'rgba(255, 159, 64, 1)',   // Orange
        'rgba(153, 102, 255, 1)'   // Purple
    ];
    
    const backgroundColors = [
        'rgba(255, 99, 132, 0.2)',  // Red
        'rgba(54, 162, 235, 0.2)',  // Blue
        'rgba(75, 192, 192, 0.2)',  // Green
        'rgba(255, 159, 64, 0.2)',  // Orange
        'rgba(153, 102, 255, 0.2)'  // Purple
    ];

    // Filter out any disabled cities (handled by the form_controls.js)
    cityChartData.forEach((city, index) => {
        if (typeof city === 'object' && city?.temperatures && city?.precipitations) {
            // Add temperature dataset
            datasetsTemp.push({
                label: `${city.name ?? 'Unknown City'} Temp (${city.temp_unit ?? '°C'})`,
                data: city.temperatures,
                borderColor: lineColors[index % lineColors.length],
                backgroundColor: backgroundColors[index % backgroundColors.length],
                tension: 0.1,
                fill: false,
                spanGaps: true
            });
            
            // Add precipitation dataset
            datasetsPrecip.push({
                label: `${city.name ?? 'Unknown City'} Precip (${city.precip_unit ?? 'mm'})`,
                data: city.precipitations,
                borderColor: lineColors[index % lineColors.length],
                backgroundColor: lineColors[index % lineColors.length],
                type: 'bar'
            });
        } else {
            console.warn("Skipping city in chart dataset preparation due to missing or invalid data structure:", city);
        }
    });
    
    return { datasetsTemp, datasetsPrecip };
}

/**
 * Initializes a Chart.js chart.
 * @param {string} canvasId - The ID of the canvas element.
 * @param {string} chartType - Type of chart (e.g., 'line', 'bar').
 * @param {Array} labels - Labels for the X-axis.
 * @param {Array} datasets - Datasets for the chart.
 * @param {string} yAxisLabel - Label for the Y-axis.
 * @param {boolean} beginAtZeroY - Whether the Y-axis should start at zero.
 * @returns {Chart|null} The created Chart instance or null if canvas not found.
 */
function createChart(canvasId, chartType, labels, datasets, yAxisLabel, beginAtZeroY) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) {
        console.warn(`Canvas element with ID '${canvasId}' not found.`);
        return null;
    }

    // Destroy existing chart instance if it exists on this canvas
    const existingChart = Chart.getChart(ctx);
    if (existingChart) {
        existingChart.destroy();
    }

    return new Chart(ctx, {
        type: chartType,
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            animation: {
                duration: 500 // Faster animations
            },
            devicePixelRatio: 2, // Better rendering on high-DPI screens
            elements: {
                line: {
                    tension: 0.1 // Smoother lines without too much processing
                }
            },
            scales: {
                y: {
                    beginAtZero: beginAtZeroY,
                    title: { display: true, text: yAxisLabel }
                },
                x: {
                    title: { display: true, text: 'Month' }
                }
            },
            plugins: {
                legend: { 
                    position: 'top',
                    labels: {
                        // Improve legend readability for multiple cities
                        boxWidth: 12,
                        padding: 10
                    }
                },
                tooltip: { 
                    mode: 'index', 
                    intersect: false,
                    animation: {
                        duration: 100 // Faster tooltip animations
                    }
                }
            }
        }
    });
}

/**
 * Render weather charts with the provided data
 * @param {Array} monthLabels - Array of month labels
 * @param {Array} cityChartData - Array of city data objects
 */
function renderWeatherCharts(monthLabels, cityChartData) {
    if (!monthLabels || !cityChartData || !Array.isArray(monthLabels) || !Array.isArray(cityChartData)) {
        console.warn('Invalid data provided to renderWeatherCharts');
        return;
    }
    
    if (monthLabels.length === 0 || cityChartData.length === 0) {
        console.warn('Empty data provided to renderWeatherCharts');
        return;
    }
    
    const { datasetsTemp, datasetsPrecip } = prepareChartDatasets(cityChartData);
    
    if (datasetsTemp.length > 0) {
        createChart('temperatureChart', 'line', monthLabels, datasetsTemp, 'Average Temperature', false);
    }
    
    if (datasetsPrecip.length > 0) {
        createChart('precipitationChart', 'bar', monthLabels, datasetsPrecip, 'Total Precipitation', true);
    }
}

// Main logic execution
document.addEventListener('DOMContentLoaded', function () {
    // Try to get data from embedded script tags (server-side rendering)
    const monthLabels = getJsonData("monthLabelsData", true);
    const cityChartData = getJsonData("cityChartData", true);
    
    // Only try to render if we have data from server-side rendering
    if (monthLabels && monthLabels.length > 0 && cityChartData && cityChartData.length > 0) {
        renderWeatherCharts(monthLabels, cityChartData);
    }
    
    // Make the function available globally for client-side rendering
    window.renderWeatherCharts = renderWeatherCharts;
});
