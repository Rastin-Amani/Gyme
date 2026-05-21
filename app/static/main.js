import './main.css';
// frontend/js/app.js
import htmx from 'htmx.org';
import Alpine from 'alpinejs';

window.htmx = htmx;

document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, HTMX version:', htmx.version);
    console.log('DOM loaded, Alpine version:', Alpine.version);
});
