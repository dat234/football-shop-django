document.addEventListener('DOMContentLoaded', function() {
    function setupDropdown(toggleId, menuId) {
        const toggle = document.getElementById(toggleId);
        const menu = document.getElementById(menuId);
        if (!toggle || !menu) return;

        toggle.addEventListener('click', function(event) {
            event.stopPropagation();
            document.querySelectorAll('.dropdown-menu.show').forEach(openMenu => {
                if (openMenu !== menu) openMenu.classList.remove('show');
            });
            menu.classList.toggle('show');
        });
    }

    setupDropdown('user-menu-toggle', 'user-menu');

    window.addEventListener('click', function(event) {
        document.querySelectorAll('.dropdown-menu.show').forEach(openMenu => {
            if (!openMenu.parentElement.contains(event.target)) {
                openMenu.classList.remove('show');
            }
        });
    });
});