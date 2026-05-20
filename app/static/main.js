import './main.css';
// frontend/js/app.js
import htmx from 'htmx.org';

window.htmx = htmx;

document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, HTMX version:', htmx.version);
});

document.body.addEventListener('htmx:afterRequest', function (evt) {
    console.log('HTMX Request finished:', evt.detail);
});

document.body.addEventListener('htmx:sendError', function (evt) {
    console.error('HTMX failed to send:', evt);
});
