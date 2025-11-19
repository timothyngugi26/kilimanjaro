document.addEventListener('DOMContentLoaded', function() {
    // Add to cart functionality
    const addToCartButtons = document.querySelectorAll('.add-to-cart');
    const feedbackToast = new bootstrap.Toast(document.getElementById('feedbackToast'));
    
    addToCartButtons.forEach(button => {
        button.addEventListener('click', function() {
            const item = this.dataset.item;
            
            fetch('/add_to_cart', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ item: item })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Show feedback
                    document.getElementById('toastMessage').textContent = `✓ Added ${item}`;
                    feedbackToast.show();
                    
                    // Reload page to update order summary
                    setTimeout(() => {
                        location.reload();
                    }, 1000);
                }
            });
        });
    });
    
    // Remove from cart functionality
    const removeButtons = document.querySelectorAll('.remove-item');
    removeButtons.forEach(button => {
        button.addEventListener('click', function() {
            const item = this.dataset.item;
            
            fetch('/remove_from_cart', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ item: item })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                }
            });
        });
    });
    
    // Delivery option toggle
    const deliveryOptionRadios = document.querySelectorAll('input[name="delivery_option"]');
    const deliveryLocation = document.getElementById('deliveryLocation');
    const pickupTime = document.getElementById('pickupTime');
    
    deliveryOptionRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.value === 'delivery') {
                deliveryLocation.style.display = 'block';
                pickupTime.style.display = 'none';
            } else {
                deliveryLocation.style.display = 'none';
                pickupTime.style.display = 'block';
            }
        });
    });
    
    // Set default pickup time to current time + 1 hour
    const now = new Date();
    now.setHours(now.getHours() + 1);
    const pickupTimeInput = document.getElementById('pickup_time');
    if (pickupTimeInput) {
        pickupTimeInput.value = now.toTimeString().slice(0, 5);
    }
});