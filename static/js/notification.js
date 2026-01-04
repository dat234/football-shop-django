document.addEventListener('DOMContentLoaded', function() {
    const notifBtn = document.querySelector('.notification-btn'); // Class của nút chuông trong header
    const notifDropdown = document.querySelector('.notification-dropdown');
    const modalOverlay = document.getElementById('notif-modal');
    const modalClose = document.querySelector('.modal-close');
    
    // 1. Toggle Dropdown
    if (notifBtn && notifDropdown) {
        notifBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            // Đóng các dropdown khác (ví dụ: User Menu)
            document.querySelectorAll('.dropdown-menu.show').forEach(menu => {
                if (menu !== notifDropdown) menu.classList.remove('show');
            });
            notifDropdown.classList.toggle('show');
        });

        // Đóng khi click ra ngoài
        document.addEventListener('click', function(e) {
            if (!notifDropdown.contains(e.target) && !notifBtn.contains(e.target)) {
                notifDropdown.classList.remove('show');
            }
        });
    }

    // 2. Handle Notification Click (Open Modal)
    const notifItems = document.querySelectorAll('.notification-item');
    notifItems.forEach(item => {
        item.addEventListener('click', function() {
            const apiUrl = this.dataset.url; // Lấy URL chính xác từ data attribute
            
            // Gọi API lấy chi tiết và đánh dấu đã đọc
            fetch(apiUrl)
                .then(response => response.json())
                .then(data => {
                    // Cập nhật nội dung Modal
                    document.getElementById('modal-title').textContent = data.title;
                    document.getElementById('modal-message').textContent = data.message;
                    document.getElementById('modal-time').textContent = data.created_at;
                    
                    // Hiển thị Modal
                    modalOverlay.classList.add('active');
                    
                    // Cập nhật giao diện (bỏ class unread, giảm số lượng badge)
                    if (this.classList.contains('unread')) {
                        this.classList.remove('unread');
                        updateBadgeCount();
                    }
                    
                    // Đóng dropdown
                    notifDropdown.classList.remove('show');
                })
                .catch(err => console.error('Lỗi tải thông báo:', err));
        });
    });

    // 3. Close Modal
    if (modalClose) {
        modalClose.addEventListener('click', () => {
            modalOverlay.classList.remove('active');
        });
    }
    
    if (modalOverlay) {
        modalOverlay.addEventListener('click', (e) => {
            if (e.target === modalOverlay) {
                modalOverlay.classList.remove('active');
            }
        });
    }

    function updateBadgeCount() {
        const badge = document.querySelector('.notif-badge');
        if (badge) {
            let count = parseInt(badge.textContent);
            if (count > 1) {
                badge.textContent = count - 1;
            } else {
                badge.remove(); // Xóa badge nếu về 0
            }
        }
    }
});
