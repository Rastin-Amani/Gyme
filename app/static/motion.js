/* ────────────────────────────────────────────────────────────────────────────
   GYME — Motion pass
   "Ink settling on paper": crisp, fast, tactile. Numbers are the hero.

   Hierarchy (per project policy): CSS → Alpine state → HTMX lifecycle →
   native rAF → motion/mini. `motion/mini` is used only where it materially
   improves expressiveness (HTMX swap continuity, completion pop). Count-up
   numerals use a tiny native rAF tween (WAAPI-mini cannot tween text values).

   All initializers are idempotent and re-run after HTMX swaps / OOB swaps;
   the module executes once (bundled singleton), so no duplicate listeners.
   ---------------------------------------------------------------------------- */
import { animate } from 'motion/mini';

const reduceMotion =
    typeof window !== 'undefined' &&
    window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/* ── Count-up numerals (font-display signature) ────────────────────────────── */
function runCountUp(el) {
    const raw = (el.dataset.countUp || el.textContent || '0').replace(/[,\s]/g, '');
    const target = parseFloat(raw);
    if (!Number.isFinite(target)) return;

    const end = Math.round(target);
    if (reduceMotion || end <= 0 || end > 100000) {
        el.textContent = String(end);
        return;
    }

    const duration = Math.min(700, 300 + end * 3);
    const start = performance.now();
    const easeOut = (t) => 1 - Math.pow(1 - t, 3);

    const frame = (now) => {
        const p = Math.min(1, (now - start) / duration);
        el.textContent = String(Math.round(end * easeOut(p)));
        if (p < 1) {
            requestAnimationFrame(frame);
        } else {
            el.textContent = String(end);
        }
    };
    requestAnimationFrame(frame);
}

function initCountUps(scope = document) {
    scope
        .querySelectorAll('[data-count-up]:not([data-counted])')
        .forEach((el) => {
            el.dataset.counted = '1';
            if (typeof IntersectionObserver === 'undefined') {
                runCountUp(el);
                return;
            }
            const io = new IntersectionObserver(
                (entries, observer) => {
                    entries.forEach((entry) => {
                        if (entry.isIntersecting) {
                            observer.unobserve(entry.target);
                            runCountUp(entry.target);
                        }
                    });
                },
                { threshold: 0.3 }
            );
            io.observe(el);
        });
}

/* ── HTMX swap continuity ────────────────────────────────────────────────────
   When a server-driven region settles, let the fresh content ease in instead
   of appearing as a hard cut. Cooldown guards against unrelated OOB swaps
   (e.g. toasts) re-triggering on an already-visible region.                */
function runSettle(el) {
    if (reduceMotion) return;
    const now = performance.now();
    if (now - (parseFloat(el.dataset.settledAt) || 0) < 600) return;
    el.dataset.settledAt = String(now);
    animate(
        el,
        { opacity: [0, 1], transform: ['translateY(6px)', 'translateY(0px)'] },
        { duration: 0.22, easing: 'ease-out' }
    );
}

function initSettles(scope = document) {
    scope.querySelectorAll('[data-settle]').forEach(runSettle);
}

/* ── New-row stagger (small groups only; keeps layout calm) ────────────────── */
function runEnter(container) {
    if (reduceMotion) return;
    const children = Array.from(container.children);
    if (!children.length) return;
    if (children.length > 14 && !container.dataset.forceStagger) return;
    animate(
        children,
        { opacity: [0, 1], transform: ['translateY(10px)', 'translateY(0px)'] },
        {
            duration: 0.28,
            delay: (i) => Math.min(i * 0.045, 0.3),
            easing: 'ease-out',
        }
    );
}

function initEnters(scope = document) {
    scope
        .querySelectorAll('[data-enter]:not([data-entered])')
        .forEach((container) => {
            container.dataset.entered = '1';
            runEnter(container);
        });
}

/* ── Completion acknowledgment (workout day done) ────────────────────────────
   Brief, honest: the request is real (HX-Refresh reloads the fresh state),
   so this only acknowledges the press before the server truth arrives.    */
function wireDoneButtons() {
    document.addEventListener('click', (event) => {
        const btn = event.target.closest('.js-done-btn');
        if (!btn || btn.dataset.doneFired) return;
        btn.dataset.doneFired = '1';
        const label = btn.querySelector('.js-done-label');
        if (label) label.textContent = '✓';
        btn.classList.add('pulse-ember');
        if (!reduceMotion) {
            animate(
                btn,
                { scale: [1, 1.05, 1] },
                { duration: 0.4, easing: 'ease-out' }
            );
        }
    });
}

/* ── Idempotent bootstrap ──────────────────────────────────────────────────── */
function init(fromSwap) {
    initCountUps();
    if (fromSwap) {
        initSettles();
        initEnters();
    }
}

document.addEventListener('DOMContentLoaded', () => init(false));
document.addEventListener('htmx:afterSettle', () => init(true));
document.addEventListener('htmx:afterSwap', () => init(true));
wireDoneButtons();