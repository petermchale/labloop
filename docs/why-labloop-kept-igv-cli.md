# IGV CLI and igv-reports comparison

**Retain IGV CLI as LabLoop's default.** The igv-reports prototype enabled
rendering without visible windows on a Mac, but showed no speed benefit and
needed more work for persistent use.

These findings come from the chr22 trio fixture on an Apple Silicon Mac,
November 9, 2026. They are not a general benchmark of either project.

| Aspect | IGV CLI / Desktop | igv-reports prototype |
| --- | --- | --- |
| Mac interface | Batch mode displays IGV windows | Headless Chrome hides windows, but may show Dock icons |
| Dependencies | IGV Desktop and Java | igv-reports and Chrome/Chromium |
| Evidence | PNG/SVG snapshots | Interactive HTML reports and PNG captures |
| Timing for 39 candidates | 34 seconds between first and last snapshots; startup and first capture excluded | 203 seconds for one capture pass, plus 57 seconds preparation |
| Reliability observed | Batch completed | Fresh-page captures completed; persistent viewer crashed at candidate 32 |
| Storage | Snapshot files | Duplicated embedded slices made the combined report about 299 MiB |

**Timings are not directly comparable:** IGV used collapsed tracks; the prototype
rendered expanded, taller panels. Development, installation, debugging, and stress
tests are excluded from the figures above.

## Capture validation

With pinned versions (igv-reports 1.17.0, igv.js 3.8.10, Playwright 1.65.0,
Chrome 156.0.8078.80), all 117 captures across 39 candidates passed read/tag and
render-state checks. All 78 repeat/delayed comparisons were pixel-identical;
failed and timed-out loads produced no images.

Readiness checks relied on internal igv.js fields. These results do not guarantee
capture completeness on other datasets or validate crossovers biologically.
The images used original BAM haplotags and did not include a phased VCF track.

## Persistent browser without validation

Reusing one browser and viewer took about **184 seconds for the first 31 captures**,
versus **181 seconds** previously. Report generation took 43 seconds; startup and
page loading took another 5 seconds. The page crashed loading candidate 32, so
there is no full-run timing or established crash cause.

Each embedded session still required decoding its data. Reusing indexed alignment
data across nearby candidates would require a different implementation and a new
measurement.

The experimental code, dependencies, and run artifacts were removed. IGV CLI
setup improvements remain. See [IGV batch scripts](https://igv.org/doc/desktop/UserGuide/tools/batch/)
and [igv-reports](https://github.com/igvteam/igv-reports).
