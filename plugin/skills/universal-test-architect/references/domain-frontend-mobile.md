# Web Front Ends and Mobile Apps

Contents: failure topology, state and network, rendering, forms and input, accessibility, performance, mobile specifics, automation hygiene, example invariants.

## Failure topology

Client state desynchronizes from the server; slow or lost networks expose races; rendering differs by device, browser, locale and assistive technology. Failures are often silent (lost drafts, stale views, duplicated submissions). Put most tests at the lowest layer that can see the bug: component and logic tests for state and rendering, a thin set of end-to-end tests for critical journeys.

## State, network and concurrency

- **Optimistic updates:** server rejects a mutation after the UI already showed success: the UI rolls back cleanly, keeps the user's draft, and explains the error.
- **Stale and out-of-order responses:** a slower earlier request must not overwrite a newer one (search-as-you-type, pagination, tab switching); cancellation works.
- **Double submit and retry:** double-click, back-button, refresh mid-submit; submission uses an idempotency key or disabled state; no duplicate orders.
- **Offline and flaky network:** online to offline mid-request, offline to online with queued actions, slow 3G, request timeout, server 5xx and 429; meaningful error and retry, no infinite spinner.
- **Multi-tab and multi-device:** same session in two tabs, logout in one tab, concurrent edits and conflict resolution (last-write-wins vs merge vs prompt).
- **Session and auth:** token expiry during a long form, refresh races, privilege change, deep link after login.
- **Caching:** stale data after mutation, service worker updates, CDN cache of personalized pages.

## Rendering and framework behavior

- Server-side rendering hydration mismatches, loading, empty, error and partial-data states for every data view.
- Long lists (virtualization), very long strings, missing images, slow assets, layout shift while content loads.
- Memory leaks in long-lived single-page apps (listeners, timers, subscriptions not cleaned up): soak test with repeated navigation.
- Browser and device matrix chosen from real traffic; feature detection, not user-agent sniffing.

## Forms and input

Validation messages per field and on server rejection, paste of long or formatted text, autofill, IME composition, emoji and right-to-left text, very long inputs, leading and trailing whitespace, numeric inputs with locale separators, date pickers across time zones and DST, file uploads (size, type, empty, duplicate, cancelled, interrupted).

## Accessibility (WCAG 2.2; test with keyboard and a screen reader, not only automated scanners)

Automated tools catch only a portion of issues; include manual keyboard and screen-reader checks for critical flows.
- **Keyboard:** every function operable by keyboard; no keyboard trap (the older success criterion 2.1.2); logical focus order; focus returns to the trigger when a modal closes; visible focus indicator.
- **New in WCAG 2.2:** focus not obscured by sticky headers, banners or chat widgets (2.4.11, AA); dragging has a single-pointer alternative (2.5.7, AA); minimum target size of 24 by 24 CSS pixels (2.5.8, AA); accessible authentication with no cognitive-function test such as recalling a password without allowing paste or a manager (3.3.8, AA); consistent help placement (3.2.6, A); no redundant re-entry of information already provided (3.3.7, A). The old 4.1.1 Parsing criterion was removed.
- Names, roles and states exposed to assistive technology; live regions for async updates and errors; error association with fields; color contrast; zoom and reflow to 400%; reduced motion; captions and text alternatives.

## Performance

Core Web Vitals on mid-range mobile over throttled networks (loading, interaction latency, layout stability), bundle size budgets, long tasks blocking input, image and font loading, regression budgets in CI.

## Mobile specifics

- **Lifecycle:** backgrounding, foregrounding, process death and restore with state intact, rotation, split screen, low memory, interruptions (calls, notifications), permissions denied, revoked mid-flow, or granted once.
- **Offline-first and sync:** queue persistence across hard app restarts, sync ordering, conflict resolution (same record edited on two devices, edit vs delete), idempotent replays, sync of large backlogs, storage full. Data-integrity failures such as dropped queued actions, out-of-order syncs or duplicate writes are release blockers. The common failure is silent data loss or a stale view, not a crash.
- **Network transitions:** Wi-Fi to cellular mid-upload, airplane mode toggles, captive portals, throttled links (use link conditioners or proxies to drop specific requests).
- **Background limits:** OS and manufacturer battery restrictions delay push and background tasks; test on real devices, since emulators are too idealized.
- **Versions in the wild:** old app versions keep calling new servers for months (see compatibility reference); forced-upgrade path works.
- **Device matrix:** OS versions, screen sizes, notches, dark mode, font scaling, low-end hardware.
- **Platform rules:** deep links and universal links, push payload handling, in-app purchase and receipt validation edge cases, privacy prompts.

## Automation hygiene (front-end flakiness is mostly preventable)

Wait on observable conditions, never fixed sleeps; stable test-id selectors rather than layout-dependent XPath; isolated test data per test (no shared accounts); stub third-party services and control the clock; run critical-path tests against real browsers or devices and the rest at component level. Expect UI end-to-end tools to be among the flakiest layers, so keep that layer small.

## Example invariants to adapt

- I: A user's unsent input is never lost on error, navigation within the app, or reconnect.
- I: The UI never displays data older than the latest acknowledged write for that user's own actions.
- I: Every interactive control is reachable and operable by keyboard alone and exposes a name and role.
- I: Offline-queued actions are applied exactly once, in order, after reconnect.
