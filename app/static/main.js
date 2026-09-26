import './main.css';
import './motion.js';
// frontend/js/app.js
import htmx from 'htmx.org';
import Alpine from 'alpinejs';
import Sortable from 'sortablejs';

window.htmx = htmx;
window.Alpine = Alpine;
window.Sortable = Sortable;

/* ── Phone field: country code (+XX) + national number → hidden E.164 input ──
   The backend keeps a single `phone` field; this component stores the full
   international number (`+<dial><national>`) in a hidden input on submit.
   Sorted by name, Iran is intentionally excluded. */
const PHONE_COUNTRIES = [
    { name: 'Afghanistan', dial: '93', flag: '🇦🇫' },
    { name: 'Algeria', dial: '213', flag: '🇩🇿' },
    { name: 'Argentina', dial: '54', flag: '🇦🇷' },
    { name: 'Armenia', dial: '374', flag: '🇦🇲' },
    { name: 'Australia', dial: '61', flag: '🇦🇺' },
    { name: 'Austria', dial: '43', flag: '🇦🇹' },
    { name: 'Azerbaijan', dial: '994', flag: '🇦🇿' },
    { name: 'Bahrain', dial: '973', flag: '🇧🇭' },
    { name: 'Bangladesh', dial: '880', flag: '🇧🇩' },
    { name: 'Belgium', dial: '32', flag: '🇧🇪' },
    { name: 'Brazil', dial: '55', flag: '🇧🇷' },
    { name: 'Bulgaria', dial: '359', flag: '🇧🇬' },
    { name: 'Canada', dial: '1', flag: '🇨🇦' },
    { name: 'Chile', dial: '56', flag: '🇨🇱' },
    { name: 'China', dial: '86', flag: '🇨🇳' },
    { name: 'Colombia', dial: '57', flag: '🇨🇴' },
    { name: 'Croatia', dial: '385', flag: '🇭🇷' },
    { name: 'Czechia', dial: '420', flag: '🇨🇿' },
    { name: 'Denmark', dial: '45', flag: '🇩🇰' },
    { name: 'Egypt', dial: '20', flag: '🇪🇬' },
    { name: 'Finland', dial: '358', flag: '🇫🇮' },
    { name: 'France', dial: '33', flag: '🇫🇷' },
    { name: 'Georgia', dial: '995', flag: '🇬🇪' },
    { name: 'Germany', dial: '49', flag: '🇩🇪' },
    { name: 'Greece', dial: '30', flag: '🇬🇷' },
    { name: 'Hong Kong', dial: '852', flag: '🇭🇰' },
    { name: 'Hungary', dial: '36', flag: '🇭🇺' },
    { name: 'India', dial: '91', flag: '🇮🇳' },
    { name: 'Indonesia', dial: '62', flag: '🇮🇩' },
    { name: 'Ireland', dial: '353', flag: '🇮🇪' },
    { name: 'Israel', dial: '972', flag: '🇮🇱' },
    { name: 'Italy', dial: '39', flag: '🇮🇹' },
    { name: 'Japan', dial: '81', flag: '🇯🇵' },
    { name: 'Jordan', dial: '962', flag: '🇯🇴' },
    { name: 'Kazakhstan', dial: '7', flag: '🇰🇿' },
    { name: 'Kenya', dial: '254', flag: '🇰🇪' },
    { name: 'Kuwait', dial: '965', flag: '🇰🇼' },
    { name: 'Lebanon', dial: '961', flag: '🇱🇧' },
    { name: 'Malaysia', dial: '60', flag: '🇲🇾' },
    { name: 'Mexico', dial: '52', flag: '🇲🇽' },
    { name: 'Morocco', dial: '212', flag: '🇲🇦' },
    { name: 'Netherlands', dial: '31', flag: '🇳🇱' },
    { name: 'New Zealand', dial: '64', flag: '🇳🇿' },
    { name: 'Nigeria', dial: '234', flag: '🇳🇬' },
    { name: 'Norway', dial: '47', flag: '🇳🇴' },
    { name: 'Oman', dial: '968', flag: '🇴🇲' },
    { name: 'Pakistan', dial: '92', flag: '🇵🇰' },
    { name: 'Peru', dial: '51', flag: '🇵🇪' },
    { name: 'Philippines', dial: '63', flag: '🇵🇭' },
    { name: 'Poland', dial: '48', flag: '🇵🇱' },
    { name: 'Portugal', dial: '351', flag: '🇵🇹' },
    { name: 'Qatar', dial: '974', flag: '🇶🇦' },
    { name: 'Romania', dial: '40', flag: '🇷🇴' },
    { name: 'Russia', dial: '7', flag: '🇷🇺' },
    { name: 'Saudi Arabia', dial: '966', flag: '🇸🇦' },
    { name: 'Serbia', dial: '381', flag: '🇷🇸' },
    { name: 'Singapore', dial: '65', flag: '🇸🇬' },
    { name: 'Slovakia', dial: '421', flag: '🇸🇰' },
    { name: 'South Africa', dial: '27', flag: '🇿🇦' },
    { name: 'South Korea', dial: '82', flag: '🇰🇷' },
    { name: 'Spain', dial: '34', flag: '🇪🇸' },
    { name: 'Sri Lanka', dial: '94', flag: '🇱🇰' },
    { name: 'Sweden', dial: '46', flag: '🇸🇪' },
    { name: 'Switzerland', dial: '41', flag: '🇨🇭' },
    { name: 'Taiwan', dial: '886', flag: '🇹🇼' },
    { name: 'Thailand', dial: '66', flag: '🇹🇭' },
    { name: 'Tunisia', dial: '216', flag: '🇹🇳' },
    { name: 'Turkey', dial: '90', flag: '🇹🇷' },
    { name: 'Ukraine', dial: '380', flag: '🇺🇦' },
    { name: 'United Arab Emirates', dial: '971', flag: '🇦🇪' },
    { name: 'United Kingdom', dial: '44', flag: '🇬🇧' },
    { name: 'United States', dial: '1', flag: '🇺🇸' },
    { name: 'Vietnam', dial: '84', flag: '🇻🇳' },
].sort((a, b) => a.name.localeCompare(b.name));

Alpine.data('phoneField', (initialValue) => ({
    countries: PHONE_COUNTRIES,
    dialCode: '+1',
    nationalNumber: '',
    phone: '',

    init() {
        const value = String(initialValue || '').trim();
        if (value.startsWith('+')) {
            const digits = value.slice(1).replace(/\D/g, '');
            let best = this.countries[0];
            for (const c of this.countries) {
                if (digits.startsWith(c.dial) && c.dial.length > best.dial.length) {
                    best = c;
                }
            }
            this.dialCode = '+' + best.dial;
            this.nationalNumber = digits.slice(best.dial.length);
        }
        this.sync();
    },

    onNationalInput(event) {
        if (event.target instanceof HTMLInputElement) {
            event.target.value = event.target.value.replace(/\D/g, '');
            this.nationalNumber = event.target.value;
        }
        this.sync();
    },

    sync() {
        this.phone = this.dialCode + this.nationalNumber;
    },
}));

Alpine.start();

document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, HTMX version:', htmx.version);
    console.log('DOM loaded, Alpine version:', Alpine.version);
    console.log('DOM loaded, Sortable version:', Sortable.version);
});