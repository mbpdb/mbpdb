# Known Issues — failing tests

Snapshot: 2026-08-19, branch `main` @ `6f1b606d`.

```
21 failed, 295 passed, 2 subtests passed
```

Run with:

```bash
cd include/peptide
../../.venv/bin/python -m pytest tests/ -q
```

Note the interpreter: the repo venv is at `/home/kuhfeldrf/mbpdb/.venv`. System
`python3` has no pytest, and there is no bare `python` on PATH.

**None of these are caused by application-logic bugs.** Fifteen are a test-harness
gap and six are tests that were never updated when the code under them changed
deliberately. Everything below is safe to ignore when judging whether a new
change broke something — but check this list first, because a clean tree is
*not* green.

---

## 1. Django app registry never initialised — 15 tests

**Failure:** `django.core.exceptions.AppRegistryNotReady: Apps aren't loaded yet.`

**Affected:**

| File | Class | Count |
|---|---|---|
| `include/peptide/tests/test_data_transformation.py:1625` | `TestDecisionsToUi` | 8 |
| `include/peptide/tests/test_data_transformation.py:1674` | `TestApplyCustomNames` | 5 |
| `include/peptide/tests/test_heatmap_differential.py:445` | `TestTransferFromDtFasta` | 2 |

**Root cause:** `include/peptide/tests/conftest.py` calls
`settings.configure(...)` with `INSTALLED_APPS=[]` (line 43) and then never
calls `django.setup()`. `django` is imported at line 30 but only for that.

That is fine for the service-layer tests, which import plain modules. These 15
tests differ: each one reaches into a Django *view* module —
`peptide.data_transformation.views` and the heatmap equivalent — and that import
chain ends at `peptide/models.py:7`, where `class ProteinInfo(models.Model)`
asks the app registry which app contains it. With no app registry populated,
the metaclass raises.

Import chain, for reference:

```
tests/... setUp()
  -> peptide.data_transformation.views                     (views.py:17)
    -> .services.blast_search                              (blast_search.py:17)
      -> peptide.models                                    (models.py:7)
        -> django ModelBase.__new__ -> apps.check_apps_ready()  -> boom
```

**Likely fix:** add the `peptide` app to `INSTALLED_APPS`, give `DATABASES` a
real (sqlite `:memory:`) default rather than `{}`, and call `django.setup()`
after `settings.configure(...)`. The models only need to be *importable* here,
not queried, so an in-memory DB with no migrations run should be enough. Worth
confirming that pulling in the full app doesn't drag Celery/Redis back in — the
conftest already stubs `peptide.celery` for exactly that reason, so the stub
must stay installed before the app is loaded.

---

## 2. Legend-position tests assert a superseded layout — 6 tests

All in `include/peptide/tests/test_heatmap_legend_position.py`. These broke in
commit `b71d455d` ("Make the below-axis legend width-aware and add a stacked
variant"), which changed both the packing rule and the function signature
without updating the tests. **The current behaviour is the intended one; the
tests are stale.**

### 2a. `_below_legend_geometry()` gained a fifth return value — 4 tests

**Failure:** `ValueError: too many values to unpack (expected 4)`

- `test_stacked_never_crowds_however_narrow_the_figure` (line 185)
- `test_rows_stack_downwards_below_the_axis` (line 195)
- `test_each_row_is_centred_on_the_figure` (line 205)
- `test_units_never_overlap_at_the_width_they_were_packed_for` (line 217)

The function now returns `(positions, height_px, bottom_margin_px, n_rows, bbox)`
— see `heatmap_viz/services/heatmap_renderer.py:219`. `bbox` is the
`(x0, x1, y0, y1)` of the single outline drawn around the whole legend strip,
which replaced the old per-unit borders. The tests still unpack four values.

**Fix:** mechanical — unpack five, ignore `bbox` (or better, assert on it, since
nothing covers the strip outline today).

### 2b. "below" is now stacked-only — 2 tests

- `test_landscape_two_units_side_by_side` (line 108) —
  `AssertionError: -0.259... != -0.374...`, asserting both legends share a `y`.
- `test_stacked_is_taller_than_side_by_side` (line 279) —
  `AssertionError: 597.0 not greater than 597.0`.

Side-by-side packing was tried and deliberately dropped ("looked crowded once
wrapped" — the docstring at `heatmap_renderer.py:235` records this). Units are
now always one per row, centred, for *both* the `below` and `below-stacked`
positions. So two units no longer share a `y`, and the two positions produce
identical figure heights.

**Fix:** these two tests are asserting a design that no longer exists. Either
delete them, or rewrite them around the current contract: `below` and
`below-stacked` should each put one unit per row, centred, and the second test
needs a new distinguishing property (or should go, if the two positions really
are equivalent now — which is itself worth deciding, since keeping two UI
options that render identically is its own problem).

---

## 3. Not covered anywhere

Flagging while it's in view, not a failure:

- **The JS legend re-pack mirror.** `_below_legend_geometry()` is documented as
  the single source of truth for the strip arithmetic, but the browser reaches
  it through a hand-written JS copy in `templates/peptide/heatmap.html`
  (`repackBelowLegends`). Nothing tests that the copy still agrees with the
  Python. It is the piece most likely to drift silently.
- **The heatmap zoom lock** added in `6f1b606d` (y-axis `fixedrange`, `matches`
  linking within a band, pruned modebar buttons). No test asserts that a band's
  rows stay range-linked or that the y-axes stay locked.
