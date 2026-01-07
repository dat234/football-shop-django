document.addEventListener('DOMContentLoaded', function() {
    const paymentRadios = document.querySelectorAll('input[name="payment_method"]');
    const submitBtn = document.querySelector('.place-order-btn');

    function updateButtonText() {
        const selected = document.querySelector('input[name="payment_method"]:checked');
        if (selected && selected.value === 'qr') {
            submitBtn.textContent = 'Tiếp tục thanh toán';
        } else {
            submitBtn.textContent = 'Xác nhận Đặt hàng';
        }
    }

    paymentRadios.forEach(radio => {
        radio.addEventListener('change', updateButtonText);
    });

    // Cập nhật khi trang vừa tải
    updateButtonText();
});