# Event-Log Augmentation under User-Defined Process Constraints

This repository is the implementation of the paper *Event-Log Augmentation under User-Defined Process Constraints*. Currently under review.

It generates synthetic event logs that satisfy declarative constraints while preserving statistical properties of a reference log. Constraints are encoded as automata and combined with transition-system–based generation; multiple scenarios (e.g. constrained vs. baseline) are supported. 

Scenario A -> SC-kFSA
Scenario B -> SC-∞FSA
Scenario C -> S-kFSA
Scenario D -> S-∞FSA

## Setup

```bash
pip install -r requirements.txt   #
```

Place event logs under `data/` folder, after creating it

## Main pieces

| Path | Role |
|------|------|
| `ConstraintBasedEventLogGenerator/EventLogGenerator.py` | Core generator |
| `ConstraintBasedEventLogGenerator/run_framework.py` | Legacy multi-scenario runner |
| `pipeline.py` | Train/test mining, scenarios A/B/C/D, metrics |
| `constraints/` | Declare constraints as NFAs, filtering, mining helpers |

It is also possible to run everything and setting the hyperparameters in run_pipeline.sh

Built with [pm4py](https://pm4py.fit.fraunhofer.de/) and [automata-lib](https://github.com/caleb531/automata) for NFA operations.

For additional informations refer to the author of the paper.
