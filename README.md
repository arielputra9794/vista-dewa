# VISTA — IDX:DEWA

Ariel Arviano Putra | Student ID 29125401 | Digital Business Valuation Midterm

Submission revision: 25 October 2026. Market reference: 19 October 2026; financial position: 30 September 2026.

## Access and setup

Public app: https://vista-ariel-dewa.streamlit.app/

For complete instructions, read VISTA_User_Guide.pdf (4 pages). The public site requires internet. Local use requires Python 3.12 and the packages in requirements.txt. No API key, subscription or AI service is needed to calculate results.

From the extracted project folder:

```sh
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Alternatively run `python launch.py` or the Mac Launch_VISTA.command shortcut. The launcher creates a virtual environment and installs dependencies when necessary. Keep the terminal open. Local URLs only work on the machine running VISTA. The optional legacy web_app.py interface uses the same engine but does not provide structured imports.

## Files and model structure

- app.py: primary Streamlit interface; engine.py: valuation calculations; model_io.py: structured-import validation.
- data/model_inputs.json: historical data, market inputs, assumptions, sources and scenarios. data/source_inputs.csv: 187 source-page inputs. sources/: four supplied financial reports.
- VISTA_Pitch.pptx: submission report, cover + 15 content slides + references + 3 appendices (20 slides total). VISTA_Pitch.pdf: fixed-layout reading copy.
- VISTA_User_Guide.pdf: setup, inputs, updates, calculations, outputs and limitations.
- VISTA_Methodology.pdf: original six-page report plus two-page revision addendum.
- VISTA_Valuation.xlsx: supporting formula-based workbook (not VBA). Select the scenario in Controls D4; use Automatic calculation. The application is the primary functional deliverable.
- test_engine.py, test_import.py, test_streamlit.py and VALIDATION.md: repeatable checks and scope of validation.

## Inputs, updates and outputs

Use sidebar controls and the operating/peer editors for active-case changes. For historical updates, expand Update financial and market data, download the JSON template, edit values and sources, upload and select Validate and apply import. Invalid data leave the current model intact. Save active model inputs to retain changes. Restore submitted data returns to the saved dataset.

Model values are IDR billion; share counts are millions. JSON ratios use decimals. latest_period selects the historical snapshot; latest_period_months is 3, 6, 9 or 12. Update financial_date and opening_cash consistently. Preserve prior periods and acquisition evidence. Imports are session-only; publishing a new default requires updating data/model_inputs.json in the repository. Static Excel/PDF/PPTX and the source CSV do not automatically update. Review the fixed 2026 quarterly narrative after any period rollover.

FCFF DCF discounts five years and a reinvestment-funded terminal value. Relative valuation applies selected-peer median EV/EBITDA to normalized annualized EBITDA. Both reconcile operating EV to equity. Suitability scores set blending weights. Named scenarios and sensitivity grids use their documented assumptions; the active dashboard uses current overrides. Export active forecast CSV, result JSON and model-input JSON in Scenarios & sensitivity.

## Results and limitations

Submitted Base: blended Rp152.3/share; DCF Rp79.8; relative Rp209.1; market reference Rp242; gap -37.1%; confidence 34/100. Bear/Base/Bull blends: Rp97.9 / Rp152.3 / Rp247.1. Recommendation: PROVISIONAL AVOID / REDUCE. These are assumption-dependent academic results.

One-off acquisition gains are excluded from recurring EBIT. Restatement/reclassification treatments are documented. Exploration recovery is not a mine NAV. Share-count verification, harmonized peer earnings, capital commitments, seasonality and terminal-value dependence remain limitations. Imports check arithmetic and structure, not the truth of external sources. AI disclosure and student responsibility appear in the deck and report.

## Reproduce checks

```sh
python -m unittest -v test_engine test_import
python test_streamlit.py
```

24 engine/import tests passed. Additional Streamlit and browser checks are documented in VALIDATION.md. Internal consistency does not certify an investment recommendation.
