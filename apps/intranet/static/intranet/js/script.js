(function () {
    const navbar = document.getElementById('navbar');
    if (!navbar) {
        return;
    }

    let previousScroll = window.pageYOffset || document.documentElement.scrollTop;

    window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset || document.documentElement.scrollTop;

        if (currentScroll <= 0) {
            navbar.style.top = '0';
        } else if (currentScroll < previousScroll) {
            navbar.style.top = '0';
        } else {
            navbar.style.top = '-85px';
        }

        previousScroll = currentScroll;
    });
})();
