/**
 * Safely parses JSON data from an HTML script tag.
 * @param {string} elementId - The ID of the script tag containing JSON data.
 * @param {boolean} expectArray - Whether the parsed data is expected to be an array.
 * @returns {object|Array|null} Parsed JSON data or null if parsing fails, element not found, or type mismatch.
 */
function getJsonData(elementId, expectArray = false) {
    const element = document.getElementById(elementId);
    if (!element) {
        console.warn(`Element with ID '${elementId}' not found.`);
        return null;
    }
    if (element.textContent.trim() === "") {
        console.warn(`Element with ID '${elementId}' has empty text content.`);
        return expectArray ? [] : null;
    }
    try {
        const parsedData = JSON.parse(element.textContent);
        
        if (expectArray && !Array.isArray(parsedData)) {
            console.warn(`Data from element ID '${elementId}' was expected to be an array, but received:`, typeof parsedData, parsedData);
            return [];
        }
        //console.log(`Successfully parsed data for ${elementId}:`, parsedData); // For debugging
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
    const lineColors = ['rgba(255, 99, 132, 1)', 'rgba(54, 162, 235, 1)', 'rgba(75, 192, 192, 1)'];
    const backgroundColors = ['rgba(255, 99, 132, 0.2)', 'rgba(54, 162, 235, 0.2)', 'rgba(75, 192, 192, 0.2)'];

    cityChartData.forEach((city, index) => { // This line should now be safe
        if (typeof city === 'object' && city?.temperatures && city?.precipitations) {
            datasetsTemp.push({
                label: `${city.name ?? 'Unknown City'} Temp (${city.temp_unit ?? '°C'})`,
                data: city.temperatures,
                borderColor: lineColors[index % lineColors.length],
                backgroundColor: backgroundColors[index % backgroundColors.length],
                tension: 0.1,
                fill: false,
                spanGaps: true
            });
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
                legend: { position: 'top' },
                tooltip: { mode: 'index', intersect: false }
            }
        }
    });
}

// Main logic execution
document.addEventListener('DOMContentLoaded', function () {
    const monthLabels = getJsonData("monthLabelsData", true);
    const cityChartData = getJsonData("cityChartData", true);

    //console.log("After getJsonData - monthLabels:", monthLabels);
    //console.log("After getJsonData - cityChartData:", cityChartData);
    //console.log("Is cityChartData an array?", Array.isArray(cityChartData));


    // The condition for proceeding is still good: we need actual data in the arrays.
    // An empty array from getJsonData will fail cityChartData.length > 0
    if (monthLabels && monthLabels.length > 0 &&
        cityChartData && cityChartData.length > 0) { // The Array.isArray check is now handled inside getJsonData if expectArray=true
        
        const { datasetsTemp, datasetsPrecip } = prepareChartDatasets(cityChartData); 

        if (datasetsTemp.length > 0) {
            createChart('temperatureChart', 'line', monthLabels, datasetsTemp, 'Average Temperature', false);
        } else {
            //console.log("No valid temperature datasets to plot after preparation.");
        }

        if (datasetsPrecip.length > 0) {
            createChart('precipitationChart', 'bar', monthLabels, datasetsPrecip, 'Total Precipitation', true);
        } else {
            //console.log("No valid precipitation datasets to plot after preparation.");
        }
    } else {
        //console.log("Conditions not met for chart rendering or data arrays are empty. monthLabels:", monthLabels, "cityChartData:", cityChartData);
    }
});