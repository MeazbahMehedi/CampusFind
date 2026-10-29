(() => {
    const root = document.documentElement;
    const themeButton = document.querySelector('.theme-toggle');

    function describeTheme() {
        if (themeButton) themeButton.setAttribute('aria-label', `Switch to ${root.dataset.theme === 'dark' ? 'light' : 'dark'} theme`);
    }
    describeTheme();
    themeButton?.addEventListener('click', () => {
        const theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
        root.dataset.theme = theme;
        try {
            localStorage.setItem('campusfind-theme', theme);
        } catch (_) {
            /* Optional persistence. */ }
        describeTheme();
    });

    const menuButton = document.querySelector('.menu-toggle');
    const sidebar = document.querySelector('.sidebar');
    const scrim = document.querySelector('.sidebar-scrim');
    const media = window.matchMedia('(max-width:760px)');

    function menu(open) {
        sidebar?.classList.toggle('open', open);
        scrim?.classList.toggle('visible', open);
        menuButton?.setAttribute('aria-expanded', String(open));
        if (media.matches && sidebar) sidebar.inert = !open;
        if (open) sidebar?.querySelector('a')?.focus();
        else if (media.matches) menuButton?.focus();
    }
    if (media.matches && sidebar) sidebar.inert = true;
    menuButton?.addEventListener('click', () => menu(!sidebar.classList.contains('open')));
    scrim?.addEventListener('click', () => menu(false));
    media.addEventListener('change', () => {
        if (sidebar) sidebar.inert = media.matches && !sidebar.classList.contains('open');
    });
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && sidebar?.classList.contains('open')) menu(false);
        if (event.key === 'Tab' && media.matches && sidebar?.classList.contains('open')) {
            const links = [...sidebar.querySelectorAll('a,button')];
            const first = links[0],
                last = links[links.length - 1];
            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
        }
    });
    document.querySelectorAll('.dismiss-flash').forEach(button => button.addEventListener('click', () => button.closest('.flash').remove()));

    const dialog = document.querySelector('#confirm-dialog');
    let pendingForm;
    document.querySelectorAll('form[data-confirm]').forEach(form => {
        form.addEventListener('submit', event => {
            if (form.dataset.confirmed === 'true') return;
            event.preventDefault();
            pendingForm = form;
            document.querySelector('#confirm-message').textContent = form.dataset.confirm;
            dialog.showModal();
        });
    });
    dialog?.addEventListener('close', () => {
        if (dialog.returnValue === 'confirm' && pendingForm) {
            pendingForm.dataset.confirmed = 'true';
            pendingForm.requestSubmit();
        }
        pendingForm = null;
    });
    document.querySelectorAll('form[method="post"]').forEach(form => {
        form.addEventListener('submit', event => {
            if (event.defaultPrevented) return;
            const button = event.submitter;
            if (button) {
                button.disabled = true;
                button.setAttribute('aria-busy', 'true');
            }
        });
    });
    const imageInput = document.querySelector('[data-image-input]');
    let previewURL;
    imageInput?.addEventListener('change', () => {
        const preview = document.querySelector('#upload-preview');
        if (previewURL) URL.revokeObjectURL(previewURL);
        const file = imageInput.files[0];
        preview.hidden = true;
        imageInput.setCustomValidity('');
        if (!file) return;
        if (file.size > 5 * 1024 * 1024) {
            imageInput.setCustomValidity('Choose an image smaller than 5 MB.');
            imageInput.reportValidity();
            return;
        }
        previewURL = URL.createObjectURL(file);
        preview.src = previewURL;
        preview.hidden = false;
    });
})();
