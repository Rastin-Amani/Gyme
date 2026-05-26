import './main.css';
// frontend/js/app.js
import htmx from 'htmx.org';
import Alpine from 'alpinejs';
import Sortable from 'sortablejs';

window.htmx = htmx;
window.Alpine = Alpine;
window.Sortable = Sortable;

Alpine.start();

document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, HTMX version:', htmx.version);
    console.log('DOM loaded, Alpine version:', Alpine.version);
    console.log('DOM loaded, Sortable version:', Sortable.version);
});
