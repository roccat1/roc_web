document.addEventListener('DOMContentLoaded', function() {

    // ================= CONFIGURATION =================
    // Define the moving average window size (in days/units) for each view.
    const SMOOTHING_WINDOWS = {
        last30: 3,    
        last365: 7,   
        monthly: 1,   
        yearly: 1     
    };
    // =================================================

    // --- 1. PREP DATA ---
    const allDates = logs.map(row => row[1] ? new Date(row[1]) : null).filter(d => d && !isNaN(d));
    const timestamps = allDates.map(d => d.getTime());

    // Update "Last Update" Text
    const dateElement = document.querySelector('.date');
    if (dateElement && timestamps.length > 0) {
        const newestDate = new Date(Math.max(...timestamps));
        const now = new Date();
        const minutesAgo = (now - newestDate) / (1000 * 60);
        
        let timeStr = minutesAgo < 60 
            ? `${Math.round(minutesAgo)} min` 
            : `${(minutesAgo / 60).toFixed(1)} h`;
        
        if (minutesAgo > 1440) timeStr = `${Math.round(minutesAgo/1440)} dies`;

        const dateString = newestDate.toLocaleString('ca-ES', { 
            timeZone: 'UTC', 
            hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' 
        });
        dateElement.textContent = `Última: fa ${timeStr} (${dateString})`;
    }

    // --- 2. MATH HELPERS (STRICT UTC) ---

    function getDayOfYearUTC(date) {
        const start = new Date(Date.UTC(date.getUTCFullYear(), 0, 0));
        const diff = date - start;
        const oneDay = 1000 * 60 * 60 * 24;
        return Math.floor(diff / oneDay);
    }

    function getDaysActive(dateObj, type) {
        const now = new Date();
        const isCurrentYear = dateObj.getUTCFullYear() === now.getUTCFullYear();
        const isCurrentMonth = isCurrentYear && dateObj.getUTCMonth() === now.getUTCMonth();

        if (type === 'year') {
            if (isCurrentYear) return getDayOfYearUTC(now);
            const year = dateObj.getUTCFullYear();
            return ((year % 4 === 0 && year % 100 > 0) || year % 400 === 0) ? 366 : 365;
        }

        if (type === 'month') {
            if (isCurrentMonth) return now.getUTCDate();
            return new Date(Date.UTC(dateObj.getUTCFullYear(), dateObj.getUTCMonth() + 1, 0)).getUTCDate();
        }
        return 1;
    }

    function calculateMovingAverage(data, windowSize) {
        if (windowSize <= 1) return data; 
        
        let result = [];
        for (let i = 0; i < data.length; i++) {
            const start = Math.max(0, i - windowSize + 1);
            const subset = data.slice(start, i + 1);
            const sum = subset.reduce((a, b) => a + b, 0);
            result.push(sum / subset.length);
        }
        return result;
    }

    // --- 3. DATA LOGIC ENGINE ---
    let myChart = null; 
    let currentOffset = 0; 

    function getDataForView(viewType, offset) {
        const counts = {}; 
        let labels = [];
        let rawData = [];
        let smoothData = [];
        let labelText = "";
        let isNavigable = false;

        // =========================================================
        // VIEW: LAST 30 DAYS (Hybrid: Rolling -> Full Months)
        // =========================================================
        if (viewType === 'last30') {
            isNavigable = true;
            let startDate, endDate;

            if (offset === 0) {
                // Offset 0: Show Last 30 Days (Rolling)
                endDate = new Date(); 
                startDate = new Date();
                startDate.setDate(endDate.getDate() - 29); 
                
                const startStr = startDate.toLocaleDateString('ca-ES', { timeZone: 'UTC', day:'numeric', month:'short'});
                const endStr = endDate.toLocaleDateString('ca-ES', { timeZone: 'UTC', day:'numeric', month:'short'});
                labelText = `${startStr} - ${endStr}`;
            } else {
                // Offset > 0: Show Full Calendar Months
                const now = new Date();
                const targetDate = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() - offset, 1));
                
                startDate = new Date(Date.UTC(targetDate.getUTCFullYear(), targetDate.getUTCMonth(), 1));
                endDate = new Date(Date.UTC(targetDate.getUTCFullYear(), targetDate.getUTCMonth() + 1, 0)); 
                
                labelText = startDate.toLocaleDateString('ca-ES', { timeZone: 'UTC', month: 'long', year: 'numeric' });
                labelText = labelText.charAt(0).toUpperCase() + labelText.slice(1);
            }

            const curr = new Date(startDate);
            while (curr <= endDate) {
                const key = curr.toISOString().split('T')[0];
                labels.push(key);
                counts[key] = 0;
                curr.setDate(curr.getDate() + 1);
            }

            allDates.forEach(d => {
                const key = d.toISOString().split('T')[0];
                if (counts.hasOwnProperty(key)) counts[key]++;
            });

            rawData = labels.map(k => counts[k]);
            smoothData = calculateMovingAverage(rawData, SMOOTHING_WINDOWS.last30);
        } 
        
        // =========================================================
        // VIEW: LAST YEAR (Reverted to Hybrid: Rolling -> Full Years)
        // =========================================================
        else if (viewType === 'last365') {
            isNavigable = true;
            let startDate, endDate;

            if (offset === 0) {
                // Offset 0: Rolling last 365 days
                endDate = new Date();
                startDate = new Date();
                startDate.setDate(endDate.getDate() - 364);
                labelText = "Últims 365 dies";
            } else {
                // Offset > 0: Full Calendar Years
                const targetYear = new Date().getFullYear() - offset;
                startDate = new Date(Date.UTC(targetYear, 0, 1)); // Jan 1
                endDate = new Date(Date.UTC(targetYear, 11, 31)); // Dec 31
                labelText = `Any ${targetYear}`;
            }

            const curr = new Date(startDate);
            while (curr <= endDate) {
                const key = curr.toISOString().split('T')[0];
                labels.push(key);
                counts[key] = 0;
                curr.setDate(curr.getDate() + 1);
            }

            allDates.forEach(d => {
                const key = d.toISOString().split('T')[0];
                if (counts.hasOwnProperty(key)) counts[key]++;
            });

            rawData = labels.map(k => counts[k]);
            smoothData = calculateMovingAverage(rawData, SMOOTHING_WINDOWS.last365); 
        } 
        
        // =========================================================
        // VIEW: MONTHLY AGGREGATE
        // =========================================================
        else if (viewType === 'monthly') {
            isNavigable = false; 
            labelText = "Històric (Mitjana vs Total)";
            
            allDates.forEach(d => {
                const key = d.toISOString().slice(0, 7); 
                counts[key] = (counts[key] || 0) + 1;
            });

            labels = Object.keys(counts).sort();
            
            const calculatedValues = labels.map(k => {
                const [y, m] = k.split('-');
                const dateObj = new Date(Date.UTC(parseInt(y), parseInt(m)-1, 1));
                const total = counts[k];
                const daysActive = getDaysActive(dateObj, 'month');
                return parseFloat((total / daysActive).toFixed(2));
            });

            smoothData = calculateMovingAverage(calculatedValues, SMOOTHING_WINDOWS.monthly);
            rawData = []; // Hide raw data
        } 
        
        // =========================================================
        // VIEW: YEARLY AGGREGATE
        // =========================================================
        else if (viewType === 'yearly') {
            isNavigable = false;
            labelText = "Històric (Mitjana vs Total)";

            allDates.forEach(d => {
                const key = d.getUTCFullYear().toString();
                counts[key] = (counts[key] || 0) + 1;
            });

            labels = Object.keys(counts).sort();

            rawData = labels.map(k => {
                const year = parseInt(k);
                const dateObj = new Date(Date.UTC(year, 0, 1));
                const total = counts[k];
                const daysActive = getDaysActive(dateObj, 'year');
                return parseFloat((total / daysActive).toFixed(2));
            });

            smoothData = calculateMovingAverage(rawData, SMOOTHING_WINDOWS.yearly); 
        }

        return { labels, rawData, smoothData, labelText, isNavigable };
    }

    // --- 4. RENDER / UPDATE CHART ---
    function updateChart() {
        const viewSelector = document.getElementById('chartView');
        const viewType = viewSelector.value;
        
        const { labels, rawData, smoothData, labelText, isNavigable } = getDataForView(viewType, currentOffset);

        document.getElementById('chartDateLabel').textContent = labelText;
        const navDiv = document.getElementById('chartNav');
        
        if(isNavigable) {
            navDiv.style.opacity = '1';
            navDiv.style.pointerEvents = 'auto';
            document.getElementById('nextPeriod').disabled = (currentOffset === 0);
        } else {
            navDiv.style.opacity = '0.3';
            navDiv.style.pointerEvents = 'none';
        }

        const ctx = document.getElementById('trafficChart').getContext('2d');

        // VISUAL CONFIG
        const lineTension = (viewType === 'yearly') ? 0 : 0.4;
        const dotRadius = (viewType === 'yearly') ? 4 : 0;

        if (!myChart) {
            // === INIT ===
            myChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Tendència', 
                            data: smoothData, 
                            fill: true,
                            tension: lineTension, 
                            borderColor: '#3b82f6', 
                            backgroundColor: 'rgba(59, 130, 246, 0.2)',
                            borderWidth: 2,
                            pointRadius: dotRadius,
                            pointHoverRadius: 6,
                            order: 1 
                        },
                        {
                            label: 'Dades Reals', 
                            data: rawData,
                            borderColor: 'rgba(200, 200, 200, 0.6)', 
                            borderWidth: 1.5,
                            fill: false,
                            pointRadius: 0, 
                            pointHoverRadius: 4,
                            tension: 0, 
                            order: 2 
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: { duration: 500 },
                    interaction: { mode: 'index', intersect: false },
                    plugins: { legend: { display: false } }, 
                    scales: {
                        y: { beginAtZero: true, grid: { color: '#f1f5f9', drawBorder: false } },
                        x: { 
                            grid: { display: false }, 
                            ticks: { 
                                maxRotation: 45, minRotation: 45, autoSkip: true, maxTicksLimit: 10,
                                callback: function(value, index, values) {
                                    const label = this.getLabelForValue(value);
                                    if(label.length > 4) {
                                        const d = new Date(label);
                                        return d.toLocaleDateString('ca-ES', { timeZone: 'UTC', day: '2-digit', month: '2-digit' });
                                    }
                                    return label;
                                }
                            } 
                        }
                    }
                }
            });
        } else {
            // === UPDATE ===
            myChart.data.labels = labels;
            myChart.data.datasets[0].data = smoothData;
            myChart.data.datasets[1].data = rawData;
            
            myChart.data.datasets[0].tension = lineTension;
            myChart.data.datasets[0].pointRadius = dotRadius;
            
            myChart.update();
        }
    }

    document.getElementById('chartView').addEventListener('change', () => {
        currentOffset = 0; 
        updateChart();
    });

    document.getElementById('prevPeriod').addEventListener('click', () => {
        currentOffset++;
        updateChart();
    });

    document.getElementById('nextPeriod').addEventListener('click', () => {
        if (currentOffset > 0) {
            currentOffset--;
            updateChart();
        }
    });

    updateChart();
});