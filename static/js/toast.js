// Hàm tạo toast html và thêm vào giao diện
function showToast(message, type = 'success') {
    let container = document.getElementById('toast-container');
    
    // Nếu chưa có container thì tạo mới (đề phòng trường hợp file html thiếu)
    if (!container) {
        container = document.createElement('ul');
        container.id = 'toast-container';
        container.className = 'messages-container';
        document.body.appendChild(container);
    }

    // Tạo thẻ li
    const li = document.createElement('li');
    li.className = type; 
    li.innerHTML = `
        <span>${message}</span>
        <button class="close-toast" onclick="closeToast(this)">&times;</button>
    `;

    container.appendChild(li);
    autoClose(li);
}

// Hàm tắt toast
function closeToast(btn) {
    const li = btn.closest('li'); // Tìm thẻ li cha
    if (li) {
        li.classList.add('fade-out');
        setTimeout(() => li.remove(), 500);
    }
}

// Hàm tự động tắt sau 3s
function autoClose(element) {
    setTimeout(() => {
        if (element) {
            element.classList.add('fade-out');
            setTimeout(() => element.remove(), 500);
        }
    }, 5000);
}

// Tự động kích hoạt hiệu ứng tắt cho các message có sẵn từ Django (khi load trang)
document.addEventListener('DOMContentLoaded', () => {
    const serverMessages = document.querySelectorAll('.messages-container li');
    serverMessages.forEach(li => autoClose(li));
});