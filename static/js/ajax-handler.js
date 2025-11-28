document.addEventListener('DOMContentLoaded', function() {
    // Tìm TẤT CẢ các form có class 'ajax-form'
    const ajaxForms = document.querySelectorAll('.ajax-form');

    ajaxForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault(); // Chặn reload trang

            const actionUrl = this.action;
            const method = this.method;
            const formData = new FormData(this);
            const submitBtn = this.querySelector('button[type="submit"]');

            if (submitBtn) {
                submitBtn.classList.add('loading'); // Thêm class để xoay
                submitBtn.disabled = true; // Khóa nút lại
            }

            fetch(actionUrl, {
                method: method,
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest', // Báo cho Django biết đây là AJAX
                }
            })
            .then(response => response.json()) // Giả sử server luôn trả về JSON
            .then(data => {
                // 1. Khôi phục nút bấm
                if (submitBtn) {
                    submitBtn.classList.remove('loading'); // Bỏ class xoay
                    submitBtn.disabled = false; // Mở khóa nút
                }

                // 2. Xử lý logic dựa trên phản hồi từ server
                if (data.status === 'success') {
                    // Hiện Popup thành công
                    if (typeof showToast === 'function') {
                        showToast(data.message || 'Thao tác thành công!', 'success');
                    }

                    // Nếu server yêu cầu chuyển trang (ví dụ: thanh toán xong -> trang cảm ơn)
                    if (data.redirect_url) {
                        setTimeout(() => {
                            window.location.href = data.redirect_url;
                        }, 1000); // Đợi 1s cho người dùng đọc thông báo rồi chuyển
                    }
                    
                    // Nếu cần cập nhật một phần giao diện (VD: Số lượng giỏ hàng trên header)
                    if (data.cart_count !== undefined) {
                         const cartCountEl = document.querySelector('.cart-count-badge'); // Class hiển thị số trên header
                         if (cartCountEl) cartCountEl.innerText = data.cart_count;
                    }

                } else {
                    // Hiện Popup lỗi
                    if (typeof showToast === 'function') {
                        showToast(data.message || 'Có lỗi xảy ra.', 'error');
                    }
                }
            })
            .catch(error => {
                console.error('Error:', error);
                if (submitBtn) {
                    submitBtn.classList.remove('loading');
                    submitBtn.disabled = false;
                }
                if (typeof showToast === 'function') {
                    showToast('Lỗi kết nối server.', 'error');
                }
            });
        });
    });
});