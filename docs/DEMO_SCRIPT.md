# ReVolt – 3-Minute Demo Script

**Before you start (do this 10 minutes early)**
- Backend running (`python backend/app.py`), frontend open at http://localhost:5173, badge says **Live API**.
- Have a backup: set `VITE_USE_MOCK=true` in `.env` if the backend or Wi-Fi fails. The demo works the same.
- Browser zoom ~110%, notifications off, start on Page 1.
- Rehearse with two inputs and note what the real model returns: the default (cycle 120) and a heavily used battery (try cycle 400-600). Use whichever number gives a clear **red** result, and write it here: ____

---

## 0:00 – 0:30 · The problem (slide or speaking, no screen)

> "Millions of EVs will retire their batteries in the next decade. A battery that is no longer good enough for a car, say at 70–80% health, still holds a lot of energy. Most of these batteries are recycled early, or thrown away, because there's no cheap way to check which ones can be reused.
> At the same time, homes with solar panels waste energy at midday and buy expensive grid power in the evening.
> **ReVolt connects the two: reuse retired EV batteries as home solar storage.**"

## 0:30 – 1:30 · Page 1: Battery Assessment (show screen)

*Action: point to the form.*
> "A retired battery comes to us with five measurements: cycle count, voltage, current, temperature and discharge time. I can type them here, or upload a CSV from a test rig."

*Action: click **Assess battery**.*
> "Our ML model estimates the battery's State of Health. Here it's **about 78%**, shown on this gauge. The remaining capacity is 1.57 Ah out of a rated 2 Ah. And it gets a **colour-coded category**: amber, 'needs further assessment'."

*Action: change cycle number to your rehearsed high value (e.g. 500) → Assess again.*
> "If I try a heavily used battery, SOH drops, and the badge turns **red: recycle recommended**. Above 80% it turns green: a candidate for second-life testing."

*Action: point at the disclaimer.*
> "Important: this is a **screening indicator, not a safety certification**. We say that clearly in the product. It tells you which batteries are worth testing properly."

## 1:30 – 2:30 · Page 2: Solar Simulation

*Action: click **Solar Simulation** tab.*
> "Now, what would this battery do in a home? The SOH from the last step is carried over automatically. Here is a typical day: solar in yellow peaks at noon, household load in purple peaks in the evening."

*Action: keep capacity 10 kWh → **Run simulation**.*
> "The usable capacity is battery size times health: about 7.8 kWh. Look at the state-of-charge chart: the battery **charges from midday solar and discharges in the evening**, staying between the 10% and 90% safety limits."

*Action: scroll to grid import chart and summary cards.*
> "Red bars show what we still buy from the grid, yellow shows wasted solar. We get **solar utilisation of X%** and **grid import of Y kWh** for the day."

*Action: change capacity to 5 → Run again.*
> "With a smaller battery, grid import goes up. The tool gives recommendations on sizing."

*(Replace X and Y with the real numbers from your run during rehearsal.)*

## 2:30 – 3:00 · Close

> "ReVolt is a prototype with three parts: ML that screens batteries, a simulation that shows value, and a dashboard anyone can use. Built with React, Flask and scikit-learn.
> Next steps: train on real battery datasets, add tariff-based savings, and scale to many batteries as a **virtual power plant**.
> Thank you. We're happy to take questions."

---

## Likely judge questions (short answers)

| Question | Answer |
|----------|--------|
| How accurate is the model? | It's a prototype trained on a public battery dataset. It's a screening tool, not a certification. We'd validate on real data before any real use. |
| Is it safe to reuse batteries? | Not on this tool's word alone. We state clearly that it's preliminary; physical testing by professionals is required. |
| Why 80% / 60% thresholds? | They're adjustable assumptions based on common industry rules of thumb. |
| How does this link to VPP/DER (Theme 6)? | Many second-life batteries in homes can be coordinated as one virtual power plant. This prototype shows the single-home building block. |
| Real hardware? | No. This is a software prototype and simulation. |

## If something goes wrong

- **Red error box on screen:** "That's our backend being offline, so I'll switch to the built-in demo data." Set `VITE_USE_MOCK=true`, restart `npm run dev`.
- **Page blank:** refresh the browser (Ctrl+R).
- Keep a **screen recording** of a successful run as the last-resort backup.
