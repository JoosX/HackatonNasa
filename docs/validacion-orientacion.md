**English** | [Español](validacion-orientacion.es.md)

# Guidance: scope and pending validation

Version 2026-11-14. Educational adaptation by team ApeLogic, for adults. **No clinical approval and no NASA certification.** No integration test was run on David's laptop for this improvement.

## What changed

The emergency walkthrough runs with JavaScript included in the page, without waiting for the API, records, Ollama or the internet once loaded. It asks about responsiveness and breathing, accounts for uncertainty and prioritizes help when there are symptoms, even if the panel is green. Users can go back, restart and close without saving answers. It does not teach the specific CPR techniques used in microgravity.

The eight guides include preparation, equipment, steps, common mistakes and what to do without the equipment. The five instrument-based measurements have specific measurement references, separate from the NASA context sources. Sleep is a team diary; mood and stress are the team's own unvalidated scales.

The rules keep their demonstration colors for compatibility. Each one declares that clinical approval is false, who is responsible, its limitations and its software validity period; the guide lets users check the exact cutoffs. Unfounded 15/30-minute waits were removed from the actions, as were the night-count cutoffs from the sleep advice. This is a documentation audit of the prototype, **not a validation of the cutoffs**. For real use, flight medicine must approve or replace each rule, device, context and procedure.

ORI routes explicit urgent expressions to a fixed response before searching or generating with AI. This conservative detection may be triggered by examples and negations, does not recognize every way of describing a symptom and must not be used to rule out urgency. The guidance button is always available. If the embeddings index does not match the current guides, ORI uses the updated text with keyword search; David can regenerate the index with his usual process.

## Sources and purpose

| Source | Used for | Does not prove |
|---|---|---|
| [RCUK BLS 2025](https://www.resus.org.uk/professional-library/2025-resuscitation-guidelines/adult-basic-life-support-guidelines) | Recognizing unresponsiveness, abnormal breathing, calling for help, CPR and AED | Approval of the spaceflight walkthrough |
| [DGLRM / ESAM-SMG 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7607644/) | The need for microgravity-specific techniques and restraint | That the user can perform them or that the app validates them |
| [MedlinePlus Pulse](https://medlineplus.gov/ency/article/003399.htm) | Rest and manual counting at the wrist | Traffic-light cutoffs for astronauts |
| [CDC Blood Pressure](https://www.cdc.gov/high-blood-pressure/measure/index.html) | Preparation and on-Earth blood pressure technique | An approved position for a microgravity mission |
| [FDA Pulse Oximeter](https://www.fda.gov/consumers/consumer-updates/pulse-oximeter-basics) | Reading and limitations of the pulse oximeter | CO₂, ship air or a diagnosis from a percentage |
| [FDA Glucose Devices](https://www.fda.gov/medical-devices/in-vitro-diagnostics/blood-glucose-monitoring-devices) | Use, hygiene and limitations of the glucose meter | Equivalence between capillary alarms and the OSD-575 laboratory |
| [MedlinePlus Temperature](https://medlineplus.gov/ency/article/003400.htm) | Preparation and thermometer method | A single diagnostic cutoff for every method |
| [NASA HRP](https://www.nasa.gov/hrp/risks/) / [OSD-575](https://osdr.nasa.gov/bio/repo/data/studies/OSD-575) | Spaceflight risks and historical samples | Clinical validation of the team's rules |

## Short test with people outside the team (pending)

Technical check carried out in a local browser: the collapse path with gasping, the conscious path with symptoms, access from the log to the blood pressure guide, the limits table, ORI routing and reopening with reset answers. Activation with Enter, closing with Escape and focus on the new question were checked. At 390 × 844, the decision buttons are 52 px tall and the dialog has no horizontal overflow; the notice was shortened so the first three answers are visible. The browser's original size was restored. These checks are not a full accessibility audit or a user test.

Do not present a technical check as a user test. Ask three people without medical training to complete these scenarios with demo data, without telling them where to click. Do not simulate maneuvers on people.

1. "Your crewmate collapses and is only gasping. Where do you look for help and what would you do first?" They should open the guidance, reach the resuscitation path and prioritize help without waiting for measurements or the chat.
2. "You have chest pain, but your pulse shows green." They should ask for help; green should not reassure them.
3. "You want to log blood pressure. You don't know what to prepare." They should find the equipment, preparation, steps, unit and both values.
4. "You don't have a pulse oximeter." They should report symptoms and leave the value missing; never make up a percentage.
5. "Did NASA approve these colors?" They should find the explanation and answer no.

Record for each person: scenario, time to first action, task completed without help, error observed and verbatim comment. Internal usability goal (not clinical): find help within 10 seconds and zero interpretations of "green = emergency ruled out". If someone makes a mistake, adjust and repeat with another person. Do not claim the goal was met until there are results.

| Anonymous person | Scenario | Seconds | Without help | Error / comment |
|---|---|---|---|---|
| Pending | — | — | — | Not carried out yet |

## Professional review (pending)

Flight medicine / emergency medicine reviewer to be assigned. Request a review of the full text, the uncertainty paths, CPR/AED according to environment and equipment, alert criteria, plausibility ranges, data age and every color cutoff. Record name, credentials, date, version, comments and explicit approval before changing the status to approved. Do not replace this review with bibliographic sources or team approval.

## Integration into the DavidMAC version (2026-11-15)

Parts of the `romario/orientacion-fundamentada` branch integrated on top of the version with the onboard database and ORI protocols:

- **Emergency walkthrough** (decision tree: responding? / breathing?): "Urgent guidance" button in the top bar and "Open step-by-step walkthrough" button in every ORI emergency answer. Works without the server, the AI or the Earth link.
- **"Measure, understand and act" guide** for each indicator (`data/medicion_guiada.json`, `/api/orientacion`), opened from "How do I take this measurement?" in the log.
- **Measurement context** (at rest, exercise, fasting, after eating): stored in the database; glucose measured outside fasting is not classified.
- **Data quality** (current, suspicious, outdated, context pending) computed by the rules engine.
- **Declared validation** in `data/reglas.json` and removal of unfounded 15/30-minute waits, also in ORI's protocols.
- **Robustness**: if the AI index does not match the current guides, the current guides are used; the chat uses the database state, not the one sent by the browser.

`mediciones.py` and `evolucion.py` were not integrated: they duplicate this version's log (`db.py`) and rules engine (`motor.py`). Pending difference in approach: ORI answers emergencies with a step-by-step protocol in the chat (empathetic, with whom to call), in addition to routing to the walkthrough. Flight medicine must review it like everything else.
