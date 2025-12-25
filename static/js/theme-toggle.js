// Theme Toggle Functionality
(function() {
    'use strict';

    const themeToggle = document.getElementById('theme-toggle');
    const root = document.documentElement;
    const body = document.body;

    // Resolve initial theme: saved -> system -> light
    const saved = localStorage.getItem('theme');
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    const initialTheme = saved || (prefersDark ? 'dark' : 'light');

    applyTheme(initialTheme);

    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            const current = root.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
            const next = current === 'dark' ? 'light' : 'dark';

            applyTheme(next);
            localStorage.setItem('theme', next);

            // Button spin animation
            themeToggle.style.transform = 'rotate(360deg)';
            setTimeout(() => {
                themeToggle.style.transform = '';
            }, 300);
        });
    }

    function applyTheme(theme) {
        root.setAttribute('data-theme', theme);
        body.setAttribute('data-theme', theme); // helps if CSS targets body
    }
})();
