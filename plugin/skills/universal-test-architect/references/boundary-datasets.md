# Boundary and Hostile Value Datasets

Starter sets of values that frequently expose bugs. Select by the input's type; do not dump everything. Contents: numbers, money, strings and Unicode, time, collections and structures, identifiers, files and payloads, networks and protocols, concurrency timing, environment.

External corpora worth pointing users to: the Big List of Naughty Strings (strings likely to break user-input handling), internationalized name test data, and the "falsehoods programmers believe" articles for time, names, addresses, emails and phone numbers (they read like suites of edge-case tests from real-world usage). The value lists below come from general engineering practice, not from a specific study.

## Numbers

- Zero, negative zero, one, minus one; smallest positive and negative increments.
- Integer limits: int8/16/32/64 min and max, and each plus or minus one; unsigned wraparound; `2^53` and `2^53 + 1` (float integers lose exactness); parsing of numbers larger than the type.
- Floats: NaN (and NaN != NaN), positive and negative infinity, subnormals, machine epsilon, `0.1 + 0.2`, very large and very small exponents, catastrophic cancellation, sum order effects.
- Percentages and ratios: 0, 100, over 100, negative; division by zero; rounding at .5 (banker's vs half-up).
- Counts and sizes: 0, 1, max page size, max page size plus one, limit of one, offset beyond the end.
- Numeric strings: leading zeros, plus signs, thousands and decimal separators by locale, scientific notation, hex, whitespace, full-width digits.

## Money

Store and compute in integer minor units or decimals. Test: zero amount, one minor unit, maximum amount, negative (refund), currencies with zero or three decimal places, rounding on split and tax (sum of rounded parts vs rounded sum), currency mismatch, exchange-rate staleness, repeated partial refunds that sum past the original.

## Strings and Unicode

- Empty, one character, whitespace only, leading and trailing whitespace, very long (limit, limit plus one, megabytes), embedded newline, tab, carriage return, null byte.
- Unicode: combining marks and normalization forms (precomposed vs decomposed should compare equal or be handled deliberately), emoji and zero-width joiner sequences, surrogate pairs, right-to-left text and bidi control characters, homoglyphs and look-alike characters, case folding (Turkish dotless i, German sharp s), invalid UTF-8 byte sequences, byte-length vs character-length vs grapheme-length.
- Injection-style strings: quotes and backslashes, SQL fragments, shell metacharacters, template delimiters, HTML and script tags, path traversal sequences, CRLF in headers, format strings, very long or nested regex-hostile sequences.
- Names and addresses: single name, very long names, apostrophes and hyphens, no family name, non-Latin scripts, titles and suffixes; addresses without postal codes or with unusual formats.
- Email and URL forms: plus addressing, unusual but valid local parts, internationalized domains, very long, trailing dots, userinfo in URLs, non-HTTP schemes, private and loopback addresses for SSRF tests.

## Time

- Edges: Unix epoch, negative timestamps, year 2038 and beyond for 32-bit, year 9999, year 0 and 1, far past and far future.
- Calendar: Feb 28, 29 and March 1 in leap and non-leap years, century leap rules, month ends (30 vs 31), week-year vs calendar-year boundaries, first and last week of the year, ISO week 53.
- Time zones: UTC offsets with half-hour and 45-minute zones, DST start (missing hour) and end (repeated hour), events scheduled in a skipped hour, zone rule changes from updated tz database, user zone differs from server zone, date-only vs datetime semantics.
- Clocks: leap seconds, clock going backwards, skew between nodes, monotonic vs wall clock, timeouts measured with the wrong clock.
- Durations and windows: zero duration, exactly at the window edge, one tick either side, very long durations, overflow in millisecond arithmetic, rolling vs calendar windows.
- Parsing and formatting: ISO 8601 vs RFC 3339 differences, missing zone, two-digit years, `YYYY` vs `yyyy` format mistakes, locale date order (day-month vs month-day).

## Collections and structures

Empty, single element, two elements, duplicates, all identical, already sorted, reverse sorted, nulls inside, maximum size, very deep nesting, cyclic references, unordered input where order is assumed, mutation during iteration, iterator exhausted, maps with missing or extra keys, duplicate keys in JSON, key ordering differences.

## Identifiers

UUID variants and case, empty string, very long, non-existent, deleted, belonging to another tenant or user, sequential and guessable values, collisions after truncation, IDs with special characters, integer overflow of auto-increment, numeric ID given as a string.

## Files and payloads

Zero bytes, one byte, exactly at the size limit and one over, truncated, wrong extension vs real type, magic-number mismatch, corrupt header, zip with path traversal entries, decompression bomb, deeply nested archive, CSV with embedded quotes and newlines, BOM present, different line endings, very wide rows, duplicate headers, mixed encodings, extremely large JSON numbers, images with huge dimensions, password-protected or encrypted files.

## Networks and protocols

Connection refused, reset mid-response, half-open, slow loris (bytes trickle), partial body, duplicate and out-of-order packets, DNS failure or changing answers, TLS expired or mismatched certificate, redirect loops, 3xx, 429 with and without `Retry-After`, 503, chunked encoding edge cases, huge headers, HTTP method and content-type mismatches, clock skew in signed requests.

## Concurrency timing

Two actors at the same instant, N actors on one key, interleavings at every step of a multi-step operation (use controlled schedules or seeded simulation), cancel racing complete, retry racing original, delayed duplicate arriving after later state, lock expiry during work, thread-pool exhaustion.

## Environment

Disk full, read-only file system, low memory, file-descriptor exhaustion, slow disk, missing or unreadable config, missing environment variable, wrong locale, wrong time zone, no network, proxy required, container restart at arbitrary times, different CPU architecture.
