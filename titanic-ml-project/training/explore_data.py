"""Describe the supplied labeled Titanic data without changing it or fitting a model.

Run from any directory. Uses only Python's standard library. ``--check`` verifies
that the committed report and CSV summaries match the current input data.
"""

import argparse
import csv
import hashlib
import io
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "training" / "data" / "train.csv"
OUTPUT = ROOT / "docs"
NUMERIC = ("Age", "Fare", "SibSp", "Parch")
CATEGORICAL = ("Pclass", "Sex", "Embarked", "SibSp", "Parch")


def csv_text(header, rows):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return stream.getvalue()


def table(header, rows):
    lines = ["| " + " | ".join(header) + " |",
             "| " + " | ".join("---" for _ in header) + " |"]
    lines.extend("| " + " | ".join(str(value) for value in row) + " |" for row in rows)
    return "\n".join(lines)


def quantile(values, fraction):
    """Linear interpolation between sorted observations, including endpoints."""
    values = sorted(values)
    position = (len(values) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def analyze(path=DATA):
    # A canonical LF digest stays stable across Windows and Linux checkouts.
    source = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    reader = csv.DictReader(io.StringIO(source))
    columns = reader.fieldnames or []
    required = {"PassengerId", "Survived", "Name", "Cabin", *NUMERIC, *CATEGORICAL}
    if required.difference(columns):
        raise ValueError(f"Missing required columns: {sorted(required.difference(columns))}")
    rows = list(reader)
    if not rows:
        raise ValueError("The dataset has no passenger records.")
    if any(row["Survived"] not in {"0", "1"} for row in rows):
        raise ValueError("Survived must contain only the observed labels 0 and 1.")
    count = len(rows)
    survivors = sum(int(row["Survived"]) for row in rows)
    missing = [(column, sum(not row[column].strip() for row in rows)) for column in columns]
    missing_csv = [(column, n, f"{n / count:.6f}") for column, n in missing]
    missing_lookup = dict(missing)

    numeric = []
    numeric_values = {}
    for column in NUMERIC:
        values = [float(row[column]) for row in rows if row[column].strip()]
        if not values:
            raise ValueError(f"No observed numeric values for {column}.")
        numeric_values[column] = values
        numeric.append((column, len(values), count - len(values), min(values),
                        quantile(values, .25), median(values), mean(values),
                        quantile(values, .75), max(values)))

    frequencies = []
    for column in CATEGORICAL:
        for category, n in sorted(Counter(row[column] or "Missing" for row in rows).items()):
            frequencies.append((column, category, n, f"{n / count:.6f}"))

    survival = []
    for grouping, fields in (("Sex", ("Sex",)), ("Pclass", ("Pclass",)),
                             ("Sex and Pclass", ("Sex", "Pclass"))):
        groups = defaultdict(list)
        for row in rows:
            groups[tuple(row[field] for field in fields)].append(int(row["Survived"]))
        for group, labels in sorted(groups.items()):
            n, survived = len(labels), sum(labels)
            survival.append((grouping, " / ".join(group), n, survived, n - survived,
                             f"{survived / n:.6f}"))

    bins = []
    for column, edges in (("Age", (0, 18, 35, 60, float("inf"))),
                          ("Fare", (0, 10, 25, 50, 100, 200, float("inf")))):
        values = numeric_values[column]
        if any(value < 0 for value in values):
            raise ValueError(f"Negative {column} values fall outside the documented histogram bins.")
        for lower, upper in zip(edges, edges[1:]):
            label = f"{lower:g} to <{upper:g}" if upper != float("inf") else f"{lower:g}+"
            n = sum(lower <= value < upper for value in values)
            bins.append((column, label, n, len(values), f"{n / len(values):.6f}"))

    duplicates = count - len({tuple(row[column] for column in columns) for row in rows})
    duplicate_ids = count - len({row["PassengerId"] for row in rows})
    sex_rates = {group: float(rate) for grouping, group, _, _, _, rate in survival if grouping == "Sex"}
    class_rates = {group: float(rate) for grouping, group, _, _, _, rate in survival if grouping == "Pclass"}
    report = f"""# Titanic exploratory data analysis

This report describes the **{count} labeled passengers** in `training/data/train.csv`.
It documents the data exploration requested in the Sprint 11 review. There are
**{survivors} survivors ({survivors / count:.2%})** and **{count - survivors} non-survivors
({(count - survivors) / count:.2%})**. The data has **{duplicates} exact duplicate rows** and
**{duplicate_ids} repeated PassengerId values**.

This is a retrospective description of the supplied labeled dataset, generated
after the existing model was trained and reviewed. It does not retrain the model,
change its features or imputation settings, or provide a new validation result.
`test.csv` has no survival labels; `gender_submission.csv` is an example submission,
not observed outcomes. Neither file is used in these calculations.

## Findings

- Cabin is missing for {missing_lookup['Cabin']} passengers ({missing_lookup['Cabin'] / count:.2%});
  Age is missing for {missing_lookup['Age']} ({missing_lookup['Age'] / count:.2%});
  Embarked is missing for {missing_lookup['Embarked']} ({missing_lookup['Embarked'] / count:.2%}).
  Cabin is not a feature in the current model. Age and Embarked use replacements
  learned from the training split, rather than statistics from this whole-dataset report.
- Fare is right-skewed: the mean is {mean(numeric_values['Fare']):.2f}, the median is
  {median(numeric_values['Fare']):.2f}, and the largest observed fare is {max(numeric_values['Fare']):.4f}.
  There are {sum(value == 0 for value in numeric_values['Fare'])} zero fares. Zero is an observed
  value in this report, not automatically treated as missing.
- Observed survival is {sex_rates['female']:.2%} for female passengers and
  {sex_rates['male']:.2%} for male passengers. By passenger class, the observed rates
  are {class_rates['1']:.2%} in first class, {class_rates['2']:.2%} in second class and
  {class_rates['3']:.2%} in third class. Group counts and joint rates below make the
  denominators visible.

## Missing values

An empty CSV field is counted as missing. Percentages use all {count} passengers.

{table(('Column', 'Missing records', 'Missing percent'), [(column, n, f'{n / count:.2%}') for column, n in missing])}

## Numerical feature distributions

Statistics exclude missing values in each column. Quartiles use linear
interpolation over sorted observed values. They describe this dataset and are
not replacement values or cutoffs fitted for serving.

{table(('Feature', 'Observed', 'Missing', 'Min', '25th percentile', 'Median', 'Mean', '75th percentile', 'Max'), [(column, n, absent, *[f'{value:.2f}' for value in values]) for column, n, absent, *values in numeric])}

### Age and fare frequency bins

Each bin includes its lower bound and excludes its upper bound. The final bin
has no upper limit. Percentages use the observed count for that feature; missing
Age values are reported above and are not silently assigned to a bin. These are
fixed descriptive bins, separate from the model's learned fare cutoffs.

{table(('Feature', 'Bin', 'Records', 'Observed denominator', 'Percent of observed'), [(column, label, n, denominator, f'{float(rate):.2%}') for column, label, n, denominator, rate in bins])}

## Categorical and family-count distributions

Percentages use all {count} passengers, including the explicit Missing category.
SibSp counts siblings/spouses aboard; Parch counts parents/children aboard.
PassengerId, Name and Ticket identify records or groups rather than serving as
continuous measurements, so they are not included in the numerical summaries.

{table(('Feature', 'Category or count', 'Passengers', 'Percent'), [(column, category, n, f'{float(rate):.2%}') for column, category, n, rate in frequencies])}

## Survival by sex and passenger class

Survival rate is survivors divided by passengers **within each row's group**.
The first two grouping blocks are marginal summaries; the last is the joint
sex/class cross-tabulation. They describe the same passengers, so their blocks
must not be added together as independent samples.

{table(('Grouping', 'Group', 'Passengers', 'Survivors', 'Non-survivors', 'Survival rate'), [(grouping, group, n, survived, died, f'{float(rate):.2%}') for grouping, group, n, survived, died, rate in survival])}

## Interpretation and model-evaluation limits

These are observational associations in a historical sample, not causal effects
or guarantees for an individual passenger. Class, sex, age and other conditions
may be related; these tables do not adjust for confounding. Smaller joint groups
have less evidence, and differences in rates are not statistical significance tests.

The existing **82.68% validation accuracy** remains the result from the original
stratified split of **712 training and 179 validation records**. This EDA covers
the whole supplied labeled file, including those validation records. It must not
be used to tune the model and then claim that same split is an untouched estimate.
Future changes informed by these findings need a new evaluation design, such as
cross-validation within training data and an untouched final test set. Training
imputation, encoders and fare boundaries must continue to be learned only from
the training data and reused unchanged for inference.

## Reproduce the report

From the project root, using Python 3.11 or newer:

```powershell
python training/explore_data.py
python training/explore_data.py --check
```

The script uses only the Python standard library and writes `docs/eda.md` plus
the five `docs/eda_*.csv` summaries. `--check` compares the expected outputs to
the committed files without writing. Datasets and saved model artifacts are
never modified.

Source: `training/data/train.csv` ({count} records, {len(columns)} columns).
SHA-256 after UTF-8 decoding and LF newline normalization:
`{hashlib.sha256(source.encode('utf-8')).hexdigest()}`.
"""
    return {
        "eda.md": report,
        "eda_missing_values.csv": csv_text(("column", "missing_count", "missing_fraction"), missing_csv),
        "eda_numeric_summary.csv": csv_text(("feature", "observed", "missing", "min", "q25", "median", "mean", "q75", "max"), [(column, n, absent, *[f"{v:.6f}" for v in values]) for column, n, absent, *values in numeric]),
        "eda_frequencies.csv": csv_text(("feature", "category", "count", "fraction_of_all"), frequencies),
        "eda_bins.csv": csv_text(("feature", "bin", "count", "observed_denominator", "fraction_of_observed"), bins),
        "eda_survival_rates.csv": csv_text(("grouping", "group", "count", "survivors", "non_survivors", "survival_rate"), survival),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify existing reports without writing files.")
    args = parser.parse_args()
    artifacts = analyze()
    if args.check:
        stale = [name for name, content in artifacts.items()
                 if not (OUTPUT / name).is_file()
                 or (OUTPUT / name).read_text(encoding="utf-8") != content]
        if stale:
            parser.exit(1, "EDA outputs missing or out of date: " + ", ".join(stale) + "\n")
        print(f"Verified {len(artifacts)} EDA outputs against {DATA.name}.")
        return
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, content in artifacts.items():
        (OUTPUT / name).write_text(content, encoding="utf-8", newline="\n")
    print(f"Wrote {len(artifacts)} EDA outputs to {OUTPUT}.")


if __name__ == "__main__":
    main()
