document.addEventListener('DOMContentLoaded', function() {
    const carousel = document.querySelector('.products-carousel');
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    
    if (!carousel || !prevBtn || !nextBtn) return;

    const originalCards = Array.from(carousel.querySelectorAll('.product-card'));
    if (originalCards.length === 0) return;

    // Clone items: [Set 1] [Set 2 (Original)] [Set 3]
    // This allows infinite scrolling in both directions
    originalCards.forEach(card => carousel.appendChild(card.cloneNode(true)));
    originalCards.forEach(card => carousel.appendChild(card.cloneNode(true)));

    const itemsPerSet = originalCards.length;
    let currentIndex = itemsPerSet; // Start at the beginning of Set 2
    let autoPlayInterval;
    let isInteracting = false;

    function scrollToIndex(index, smooth = true) {
        const card = carousel.querySelector('.product-card');
        if(!card) return;
        
        // Tính toán lại gap dựa trên thực tế (do dùng vw)
        const style = window.getComputedStyle(carousel);
        const gap = parseFloat(style.gap) || 0;
        const itemWidth = card.offsetWidth;
        const fullItemWidth = itemWidth + gap;
        const containerWidth = carousel.offsetWidth;
        
        // Position of the start of the target item
        const itemLeft = index * fullItemWidth;
        
        // Center it: Item Left + Half Item - Half Container
        const targetScroll = itemLeft + (itemWidth / 2) - (containerWidth / 2);
        
        carousel.scrollTo({
            left: targetScroll,
            behavior: smooth ? 'smooth' : 'auto'
        });
    }

    function updateActiveCard() {
        const center = carousel.scrollLeft + (carousel.offsetWidth / 2);
        const allCards = carousel.querySelectorAll('.product-card');
        
        allCards.forEach((card) => {
            const cardCenter = card.offsetLeft + (card.offsetWidth / 2);
            const dist = Math.abs(center - cardCenter);
            
            if (dist < 150) {
                card.classList.add('active');
            } else {
                card.classList.remove('active');
            }
        });
    }

    // Infinite Loop Reset Logic
    function checkInfiniteLoop() {
        const N = itemsPerSet;
        // If we are in Set 3 (index >= 2N), jump back to Set 2
        if (currentIndex >= 2 * N) {
            currentIndex = currentIndex - N;
            scrollToIndex(currentIndex, false);
        } 
        // If we are in Set 1 (index < N), jump forward to Set 2
        else if (currentIndex < N) {
            currentIndex = currentIndex + N;
            scrollToIndex(currentIndex, false);
        }
    }

    // Navigation
    function next() {
        currentIndex++;
        scrollToIndex(currentIndex, true);
        resetAutoPlay();
    }

    function prev() {
        currentIndex--;
        scrollToIndex(currentIndex, true);
        resetAutoPlay();
    }

    // Auto Play (5 seconds)
    function startAutoPlay() {
        clearInterval(autoPlayInterval);
        autoPlayInterval = setInterval(() => {
            if (!isInteracting) {
                next();
            }
        }, 5000);
    }

    function resetAutoPlay() {
        clearInterval(autoPlayInterval);
        startAutoPlay();
    }

    // Event Listeners
    nextBtn.addEventListener('click', next);
    prevBtn.addEventListener('click', prev);

    let scrollTimeout;
    carousel.addEventListener('scroll', () => {
        updateActiveCard();
        
        // Detect scroll end to check infinite loop
        clearTimeout(scrollTimeout);
        scrollTimeout = setTimeout(() => {
            checkInfiniteLoop();
        }, 100);
    });

    carousel.addEventListener('mouseenter', () => isInteracting = true);
    carousel.addEventListener('mouseleave', () => isInteracting = false);

    // Initialize
    setTimeout(() => {
        scrollToIndex(currentIndex, false);
        updateActiveCard();
        startAutoPlay();
    }, 100);
    
    // Handle resize
    window.addEventListener('resize', () => scrollToIndex(currentIndex, false));
});