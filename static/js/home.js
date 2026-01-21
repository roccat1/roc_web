document.addEventListener('DOMContentLoaded', function() {

    // ================= CONFIGURATION =================
    const SMOOTHING_WINDOWS = {
        last30: 3,    
        last365: 7,   
        monthly: 1,   
        yearly: 1     
    };
    // =================================================

    // --- 1. PREP DATA ---
    function parseAsDatabaseTime(dateString) {
        if (!dateString) return null;
        
        // The input is now "2026-01-21T21:52:00"
        // When we do new Date("..."), the browser treats this ISO format (without Z) 
        // as "Local Browser Time". 
        // So 21:52 becomes 21:52 on the user's clock. Perfect.
        const d = new Date(dateString);
        
        // We still need to create a UTC object for the chart logic to work 
        // consistently across the rest of your script
        return new Date(Date.UTC(
            d.getFullYear(),
            d.getMonth(),
            d.getDate(),
            d.getHours(),
            d.getMinutes(),
            d.getSeconds()
        ));
    }

    // Apply the helper
    const allDates = logs.map(row => parseAsDatabaseTime(row[2])).filter(d => d);
    const timestamps = allDates.map(d => d.getTime());

    // ... rest of the code ...
    
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

    function updateDashboardStats() {
        const now = new Date();
        const oneDayMs = 1000 * 60 * 60 * 24;

        // 1. Total Logs
        const totalCount = allDates.length;
        document.getElementById('statTotal').textContent = totalCount.toLocaleString();

        // Helper: Count logs within the last X days
        function getCountInWindow(days) {
            const cutoff = new Date(now.getTime() - (days * oneDayMs));
            return allDates.filter(d => d >= cutoff).length;
        }

        // 2. Avg / Day (Last 30 Days)
        const count30 = getCountInWindow(30);
        document.getElementById('statAvg30').textContent = (count30 / 30).toFixed(2);

        // 3. Avg / Day (Last 365 Days)
        const count365 = getCountInWindow(365);
        document.getElementById('statAvg365').textContent = (count365 / 365).toFixed(2);

        // 4. Avg / Day (Ever)
        if (timestamps.length > 0) {
            const firstDate = new Date(Math.min(...timestamps));
            const daysDiff = (now - firstDate) / oneDayMs;
            const daysActive = Math.max(1, Math.floor(daysDiff)); 
            document.getElementById('statAvgEver').textContent = (totalCount / daysActive).toFixed(2);
        } else {
            document.getElementById('statAvgEver').textContent = "0.00";
        }

        // 5. Peak Hour (Last 30 Days Only)
        const cutoff30 = new Date(now.getTime() - (30 * oneDayMs));
        const logsLast30 = allDates.filter(d => d >= cutoff30);

        if (logsLast30.length > 0) {
            const hourCounts = {};
            logsLast30.forEach(d => {
                const hour = d.getUTCHours(); // UPDATED: Use UTC Hours
                hourCounts[hour] = (hourCounts[hour] || 0) + 1;
            });

            let maxHour = 0;
            let maxCount = 0;
            for (const [hour, count] of Object.entries(hourCounts)) {
                if (count > maxCount) {
                    maxCount = count;
                    maxHour = hour;
                }
            }
            const hourStr = maxHour.toString().padStart(2, '0');
            document.getElementById('statPeakHour').textContent = `${hourStr}:00`;
        } else {
            document.getElementById('statPeakHour').textContent = "-";
        }
    }

    updateDashboardStats();

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
        // VIEW: LAST 30 DAYS 
        // =========================================================
        if (viewType === 'last30') {
            isNavigable = true;
            let startDate, endDate;

            if (offset === 0) {
                endDate = new Date(); 
                startDate = new Date();
                startDate.setDate(endDate.getDate() - 29); 
                
                const startStr = startDate.toLocaleDateString('ca-ES', { timeZone: 'UTC', day:'numeric', month:'short'});
                const endStr = endDate.toLocaleDateString('ca-ES', { timeZone: 'UTC', day:'numeric', month:'short'});
                labelText = `${startStr} - ${endStr}`;
            } else {
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
        // VIEW: LAST YEAR 
        // =========================================================
        else if (viewType === 'last365') {
            isNavigable = true;
            let startDate, endDate;

            if (offset === 0) {
                endDate = new Date();
                startDate = new Date();
                startDate.setDate(endDate.getDate() - 364);
                labelText = "Últims 365 dies";
            } else {
                const targetYear = new Date().getFullYear() - offset;
                startDate = new Date(Date.UTC(targetYear, 0, 1));
                endDate = new Date(Date.UTC(targetYear, 11, 31));
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
        // VIEW: MONTHLY
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
            rawData = []; 
        } 
        
        // =========================================================
        // VIEW: YEARLY
        // =========================================================
        else if (viewType === 'yearly') {
            isNavigable = false;
            labelText = "Històric (Mitjana vs Total)";

            allDates.forEach(d => {
                const key = d.getUTCFullYear().toString(); // UPDATED: UTC
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

        // =========================================================
        // VIEW: HOURLY (15-minute intervals)
        // =========================================================
        else if (viewType === 'hours') {
            isNavigable = false;
            labelText = "Per hora (15 min)";

            // 1. Generate all 96 intervals (00:00 to 23:45)
            for (let i = 0; i < 96; i++) {
                const hours = Math.floor(i / 4);
                const mins = (i % 4) * 15;
                const label = `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}`;
                labels.push(label);
                counts[label] = 0;
            }

            // 2. Fill with Real Data
            allDates.forEach(d => {
                const hours = d.getUTCHours();     
                const mins = d.getUTCMinutes();    
                // Calculate which 15-min slot this falls into
                const slot = hours * 4 + Math.floor(mins / 15);
                
                // Reconstruct label to match the generated keys
                const slotHours = Math.floor(slot / 4);
                const slotMins = (slot % 4) * 15;
                const label = `${String(slotHours).padStart(2, '0')}:${String(slotMins).padStart(2, '0')}`;
                
                if (counts.hasOwnProperty(label)) counts[label]++;
            });

            rawData = labels.map(k => counts[k]);
            
            // 3. APPLY SMOOTHING OF 2 (As requested)
            smoothData = calculateMovingAverage(rawData, 2);
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
        
        // CONFIGURATION PER VIEW
        const isYearly = (viewType === 'yearly');
        
        // CHANGE: We treat 'hours' as a LINE chart now, so we can see both Real Data and Tendency
        // If you strictly want bars for hours, we would need a mixed-chart config.
        // Keeping it false ensures consistent look with "Last 30 Days".
        const isBarChart = false; 

        const lineTension = isYearly ? 0 : 0.4;
        const dotRadius = isYearly ? 4 : 0; // Small dots for yearly, no dots for others to look cleaner

        if (!myChart) {
            myChart = new Chart(ctx, {
                type: 'line', // Always line to support dual datasets
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
                            tension: 0, // Real data is always jagged
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
                                maxRotation: 45, 
                                minRotation: 45, 
                                autoSkip: true, 
                                maxTicksLimit: (viewType === 'hours') ? 24 : 10 
                            } 
                        }
                    }
                }
            });
        } else {
            // Update Data
            myChart.data.labels = labels;
            myChart.data.datasets[0].data = smoothData; // Tendency
            myChart.data.datasets[1].data = rawData;    // Real Data
            
            // Update Visual Styles based on view
            myChart.data.datasets[0].tension = lineTension;
            myChart.data.datasets[0].pointRadius = dotRadius;
            
            // Update X-Axis tick limit specific for hourly view
            myChart.options.scales.x.ticks.maxTicksLimit = (viewType === 'hours') ? 24 : 10;
            
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