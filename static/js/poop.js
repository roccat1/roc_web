document.addEventListener('DOMContentLoaded', function() {
    
    // Elements
    const initialState = document.getElementById('initial-state');
    const confirmState = document.getElementById('confirm-state');
    const successState = document.getElementById('success-state');
    const timeDisplay = document.getElementById('current-time-display');
    
    const btnPoopNow = document.getElementById('btn-poop-now');
    const btnCancel = document.getElementById('btn-cancel');
    const btnConfirm = document.getElementById('btn-confirm');
    const manualForm = document.getElementById('manual-form');
    const dateInput = document.getElementById('past-date');

    // 1. "Poop Now" Click Logic
    btnPoopNow.addEventListener('click', function() {
        // Get current time formatted HH:MM
        const now = new Date();
        const timeString = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        timeDisplay.textContent = timeString;
        
        // Switch UI
        initialState.classList.add('hidden');
        confirmState.classList.remove('hidden');
    });

    // 2. Cancel Logic
    btnCancel.addEventListener('click', function() {
        confirmState.classList.add('hidden');
        initialState.classList.remove('hidden');
    });

    // 3. Confirm Logic
    btnConfirm.addEventListener('click', function() {
        confirmState.classList.add('hidden');
        successState.classList.remove('hidden');

        const data = new FormData();

        const now = new Date();
        now.setMinutes(now.getMinutes() - now.getTimezoneOffset()); // Delete timezone offset
        const timeString = now.toISOString().slice(0, 16);

        console.log("Logging time:", timeString);

        data.append('user_time', timeString);

        fetch('/poop', {
            method: 'POST',
            body: data 
            // Note: Do NOT set 'Content-Type'. The browser sets it automatically for FormData.
        })
        .then(response => {
            if (response.ok) {
                console.log("💩 Logged successfully!");
                // Optional: Reload the page to see the new flash message/table entry
                window.location.reload(); 
            } else {
                console.error("Something went wrong.");
            }
        })
        .catch(error => console.error('Error:', error));

        successState.classList.add('hidden');
        initialState.classList.remove('hidden');
    });

    // 4. Manual Form Logic - Set default time
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    dateInput.value = now.toISOString().slice(0, 16);

    manualForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const btn = manualForm.querySelector('.btn-submit');
        const originalText = btn.textContent;

        btn.textContent = "Logged!";
        btn.style.backgroundColor = "var(--success-green)";
        
        const data = new FormData();

        data.append('user_time', dateInput.value);

        fetch('/poop', {
            method: 'POST',
            body: data 
            // Note: Do NOT set 'Content-Type'. The browser sets it automatically for FormData.
        })
        .then(response => {
            if (response.ok) {
                console.log("💩 Logged successfully!");
                // Optional: Reload the page to see the new flash message/table entry
                window.location.reload(); 
            } else {
                console.error("Something went wrong.");
            }
        })
        .catch(error => console.error('Error:', error));
    });
});