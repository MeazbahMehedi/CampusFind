// Run before the page paints to keep the saved theme consistent.
(() => {
    let theme = 'light';
    try {
        theme = localStorage.getItem('campusfind-theme') || 'light';
    } catch (_) {
        /* Storage can be disabled. */ }
    document.documentElement.dataset.theme = theme === 'dark' ? 'dark' : 'light';
})();
