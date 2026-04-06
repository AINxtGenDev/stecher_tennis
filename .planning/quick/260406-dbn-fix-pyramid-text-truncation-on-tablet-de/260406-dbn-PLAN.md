---
phase: quick
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: [templates/index.html]
autonomous: false
requirements: [fix-tablet-truncation]
must_haves:
  truths:
    - "Long German surnames (Kronberger, Strauberger, Bachmayr) display fully on tablet screens (768-1200px)"
    - "Pyramid layout remains visually correct on all screen sizes"
    - "Phone and desktop views are not affected"
  artifacts:
    - path: "templates/index.html"
      provides: "Updated tablet responsive CSS"
  key_links: []
---

<objective>
Fix player name truncation on tablet devices by removing overflow:hidden/text-overflow:ellipsis for tablet breakpoints and allowing text to wrap within the player boxes, combined with appropriate font-size and width adjustments.

Purpose: Player names are cut off on iPad tablets despite two previous font-size reduction attempts. The root cause is `overflow: hidden; text-overflow: ellipsis` on `.player-info` which forces truncation regardless of font size.
Output: Updated CSS in templates/index.html
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@templates/index.html
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix tablet CSS to prevent name truncation</name>
  <files>templates/index.html</files>
  <action>
In templates/index.html, make these CSS changes:

1. In the `@media (max-width: 1200px)` block (line ~86), update to:
```css
.ranking-list .player {
  width: 75px;
  font-size: 0.35rem;
  margin: 2px;
}
.ranking-list .player .player-info {
  overflow: visible;
  text-overflow: unset;
  white-space: normal;
  word-break: break-word;
}
.ranking-list .player .player-name {
  white-space: normal;
  word-break: break-word;
  line-height: 1.15;
}
```

2. In the `@media (max-width: 768px)` block (line ~95), add after the existing `.ranking-list .player` rule:
```css
.ranking-list .player .player-info {
  overflow: visible;
  text-overflow: unset;
  white-space: normal;
  word-break: break-word;
}
.ranking-list .player .player-name {
  white-space: normal;
  word-break: break-word;
  line-height: 1.15;
}
```
Keep the existing player width: 55px and font-size: 0.28rem for 768px breakpoint.

The key insight: the base style on line 27 sets `overflow: hidden; text-overflow: ellipsis` on `.player-info` which CAUSES the truncation. The tablet breakpoints must override this to allow text to wrap within the box. The boxes use `height: auto; aspect-ratio: 1` so they can grow slightly if needed, but with these small font sizes wrapping should fit.

Do NOT change the 480px (phone) breakpoint or the base (desktop) styles.
  </action>
  <verify>
    <automated>python -c "
content = open('templates/index.html').read()
assert 'overflow: visible' in content, 'Missing overflow: visible'
assert content.count('overflow: visible') >= 2, 'Need overflow:visible in both tablet breakpoints'
assert 'word-break: break-word' in content, 'Missing word-break'
print('CSS changes verified')
"</automated>
  </verify>
  <done>Tablet breakpoints override overflow:hidden with overflow:visible and allow word wrapping for player names</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>Updated tablet CSS to prevent name truncation by allowing text wrapping instead of ellipsis truncation</what-built>
  <how-to-verify>
    1. Run `python app.py` to start the dev server
    2. Open the app on your iPad tablet (or use browser dev tools with iPad dimensions ~768x1024 and ~1024x1366)
    3. Check that long names like "Kronberger", "Strauberger", "Bachmayr" display fully without being cut off
    4. Verify the pyramid still looks good overall — boxes may wrap text to 2 lines which is fine
    5. Check desktop view (full width) still works normally
    6. Check phone view (< 480px) still works normally
  </how-to-verify>
  <resume-signal>Type "approved" or describe what still needs fixing</resume-signal>
</task>

</tasks>

<verification>
- Long German surnames fully visible on tablet screen sizes
- No regression on phone or desktop views
- Pyramid layout intact
</verification>

<success_criteria>
All player names display without truncation on tablet devices (768-1200px viewport width).
</success_criteria>

<output>
After completion, create `.planning/quick/260406-dbn-fix-pyramid-text-truncation-on-tablet-de/260406-dbn-SUMMARY.md`
</output>
