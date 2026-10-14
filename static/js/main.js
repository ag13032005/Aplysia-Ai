// Add loading animation
document.addEventListener('DOMContentLoaded', function() {
    // Add smooth scrolling to all links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // Add tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[title]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    const fetchButton = document.getElementById('fetchThingSpeak');
    const status = document.getElementById('thingSpeakStatus');
    if (fetchButton && status) {
        fetchButton.addEventListener('click', async function() {
            fetchButton.disabled = true;
            status.textContent = 'Fetching latest reading...';

            try {
                const response = await fetch('/api/thingspeak/latest');
                const data = await response.json();
                if (!response.ok) throw new Error(data.error || 'Fetch failed.');

                Object.entries(data).forEach(([field, value]) => {
                    const input = document.getElementById(field);
                    if (input) input.value = value;
                    input?.dispatchEvent(new Event('input', { bubbles: true }));
                });
                status.textContent = 'Latest sensor data loaded.';
                status.className = 'small text-success';
            } catch (error) {
                status.textContent = error.message;
                status.className = 'small text-danger';
            } finally {
                fetchButton.disabled = false;
            }
        });
    }
});

// Form validation
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return true;
    
    const inputs = form.querySelectorAll('input[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            input.classList.add('is-invalid');
            isValid = false;
        } else {
            input.classList.remove('is-invalid');
        }
    });
    
    return isValid;
}