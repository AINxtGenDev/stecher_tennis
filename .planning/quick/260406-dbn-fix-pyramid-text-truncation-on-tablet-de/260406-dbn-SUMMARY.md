# Quick Task 260406-dbn: Fix pyramid text truncation on tablet devices

**Date:** 2026-04-06
**Status:** Complete

## Changes

### templates/index.html

**Root cause:** The base `.player-info` style had `overflow: hidden; text-overflow: ellipsis` which truncated long player names (e.g. "Kronberger", "Strauberger") regardless of font size.

**Fix:** Added `overflow: visible`, `text-overflow: unset`, `white-space: normal`, and `word-break: break-word` overrides in both tablet breakpoints:

- **@media (max-width: 1200px)**: width 75px, font-size 0.35rem + overflow overrides
- **@media (max-width: 768px)**: width 55px, font-size 0.28rem + overflow overrides

Names now wrap to a second line instead of being truncated with ellipsis.

## Verification

Tested in browser dev tools at:
- 1024x768 (tablet landscape) — names fully visible ✓
- 768x1024 (tablet portrait) — names fully visible ✓
- 390x844 (phone) — unchanged, working ✓
- 1920x1080 (desktop) — unchanged, working ✓
