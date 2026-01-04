document.addEventListener('DOMContentLoaded', function() {
    
    // ================= NEW: UPDATE DATE LABEL =================
    const dateElement = document.querySelector('.date');

    if (dateElement && logs.length > 0) {
        // 1. Extract all timestamps (in milliseconds) from the logs
        // row[1] is the date string based on your previous screenshot
        const timestamps = logs.map(row => new Date(row[1]).getTime());

        // 2. Find the maximum timestamp (the most recent date)
        const newestTimestamp = Math.max(...timestamps);
        const newestDate = new Date(newestTimestamp);

        // 3. Format it nicely (e.g., "04/01/2026 10:24:00")
        // We use 'ca-ES' (Catalan) to match your text
        const dateString = newestDate.toLocaleString('ca-ES', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });

        // 4. Update the HTML
        dateElement.textContent = `Última actualització: ${dateString}`;
    }


    // ================= CONFIGURATION =================
    // 1. How many days back do you want to see?
    const TOTAL_DAYS_TO_SHOW = 30; 
    
    // 2. How many days to smooth over? (7 = weekly average, 1 = no smoothing)
    const MOVING_AVERAGE_WINDOW = 3;
    // =================================================

    // 1. GET DATA (Assuming 'logs' is injected via Flask previously)
    // If you haven't defined 'logs' yet, uncomment the line below:
    // const logs = {{ logs | tojson }}; 

    // 2. PARSE LOGS INTO A FREQUENCY MAP
    const counts = {};

    logs.forEach(row => {
        // row[1] is the Date String per your screenshot
        const timeString = row[1];
        if (timeString) {
            const dateObj = new Date(timeString);
            if (!isNaN(dateObj)) {
                // Key format: "2026-01-04"
                const dayLabel = dateObj.toISOString().split('T')[0];
                counts[dayLabel] = (counts[dayLabel] || 0) + 1;
            }
        }
    });

    // 3. GENERATE CONTINUOUS TIMELINE (Handle 0s)
    const labels = [];
    const dataPoints = [];
    
    // Use the variable we defined at the top
    const today = new Date();
    
    // Loop backwards from today to 'TOTAL_DAYS_TO_SHOW' days ago
    for (let i = TOTAL_DAYS_TO_SHOW - 1; i >= 0; i--) {
        const d = new Date();
        d.setDate(today.getDate() - i);
        
        // Create key "2026-01-04" to match the map above
        const dateKey = d.toISOString().split('T')[0];
        
        labels.push(dateKey);
        
        // IF log exists, use count. ELSE use 0.
        dataPoints.push(counts[dateKey] || 0);
    }

    // 4. SMOOTHING FUNCTION (Simple Moving Average)
    function calculateMovingAverage(data, windowSize) {
        let result = [];
        for (let i = 0; i < data.length; i++) {
            // Get the slice of data from (i - window) to i
            const start = Math.max(0, i - windowSize + 1);
            const subset = data.slice(start, i + 1);
            
            // Calculate average
            const sum = subset.reduce((a, b) => a + b, 0);
            result.push(sum / subset.length);
        }
        return result;
    }

    // Apply smoothing using the variable defined at the top
    const smoothedData = calculateMovingAverage(dataPoints, MOVING_AVERAGE_WINDOW);

    // 5. PLOT CHART
    const ctx = document.getElementById('trafficChart').getContext('2d');
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    // Update label dynamically to show the window size
                    label: `Trend (${MOVING_AVERAGE_WINDOW}-Day Avg)`, 
                    data: smoothedData, 
                    fill: true,
                    tension: 0.4, // Visual curve
                    borderColor: '#3b82f6', // Blue
                    backgroundColor: 'rgba(59, 130, 246, 0.2)',
                    borderWidth: 2,
                    pointRadius: 0, // Hide dots for cleaner look
                    pointHoverRadius: 6
                },
                {
                    label: 'Raw Daily Count', 
                    data: dataPoints,
                    borderColor: 'rgba(200, 200, 200, 0.5)', // Light Grey
                    borderWidth: 1,
                    fill: false,
                    pointRadius: 0,
                    tension: 0.1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: { legend: { display: true } }, 
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: '#f1f5f9', drawBorder: false },
                    ticks: { display: false }
                },
                x: {
                    grid: { display: false },
                    ticks: { 
                        color: '#94a3b8', 
                        font: { size: 10 },
                        maxRotation: 45,
                        minRotation: 45
                    }
                }
            }
        }
    });
});