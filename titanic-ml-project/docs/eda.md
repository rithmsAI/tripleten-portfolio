# Titanic exploratory data analysis

This report describes the **891 labeled passengers** in `training/data/train.csv`.
It documents the data exploration requested in the Sprint 11 review. There are
**342 survivors (38.38%)** and **549 non-survivors
(61.62%)**. The data has **0 exact duplicate rows** and
**0 repeated PassengerId values**.

This is a retrospective description of the supplied labeled dataset, generated
after the existing model was trained and reviewed. It does not retrain the model,
change its features or imputation settings, or provide a new validation result.
`test.csv` has no survival labels; `gender_submission.csv` is an example submission,
not observed outcomes. Neither file is used in these calculations.

## Findings

- Cabin is missing for 687 passengers (77.10%);
  Age is missing for 177 (19.87%);
  Embarked is missing for 2 (0.22%).
  Cabin is not a feature in the current model. Age and Embarked use replacements
  learned from the training split, rather than statistics from this whole-dataset report.
- Fare is right-skewed: the mean is 32.20, the median is
  14.45, and the largest observed fare is 512.3292.
  There are 15 zero fares. Zero is an observed
  value in this report, not automatically treated as missing.
- Observed survival is 74.20% for female passengers and
  18.89% for male passengers. By passenger class, the observed rates
  are 62.96% in first class, 47.28% in second class and
  24.24% in third class. Group counts and joint rates below make the
  denominators visible.

## Missing values

An empty CSV field is counted as missing. Percentages use all 891 passengers.

| Column | Missing records | Missing percent |
| --- | --- | --- |
| PassengerId | 0 | 0.00% |
| Survived | 0 | 0.00% |
| Pclass | 0 | 0.00% |
| Name | 0 | 0.00% |
| Sex | 0 | 0.00% |
| Age | 177 | 19.87% |
| SibSp | 0 | 0.00% |
| Parch | 0 | 0.00% |
| Ticket | 0 | 0.00% |
| Fare | 0 | 0.00% |
| Cabin | 687 | 77.10% |
| Embarked | 2 | 0.22% |

## Numerical feature distributions

Statistics exclude missing values in each column. Quartiles use linear
interpolation over sorted observed values. They describe this dataset and are
not replacement values or cutoffs fitted for serving.

| Feature | Observed | Missing | Min | 25th percentile | Median | Mean | 75th percentile | Max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Age | 714 | 177 | 0.42 | 20.12 | 28.00 | 29.70 | 38.00 | 80.00 |
| Fare | 891 | 0 | 0.00 | 7.91 | 14.45 | 32.20 | 31.00 | 512.33 |
| SibSp | 891 | 0 | 0.00 | 0.00 | 0.00 | 0.52 | 1.00 | 8.00 |
| Parch | 891 | 0 | 0.00 | 0.00 | 0.00 | 0.38 | 0.00 | 6.00 |

### Age and fare frequency bins

Each bin includes its lower bound and excludes its upper bound. The final bin
has no upper limit. Percentages use the observed count for that feature; missing
Age values are reported above and are not silently assigned to a bin. These are
fixed descriptive bins, separate from the model's learned fare cutoffs.

| Feature | Bin | Records | Observed denominator | Percent of observed |
| --- | --- | --- | --- | --- |
| Age | 0 to <18 | 113 | 714 | 15.83% |
| Age | 18 to <35 | 366 | 714 | 51.26% |
| Age | 35 to <60 | 209 | 714 | 29.27% |
| Age | 60+ | 26 | 714 | 3.64% |
| Fare | 0 to <10 | 336 | 891 | 37.71% |
| Fare | 10 to <25 | 221 | 891 | 24.80% |
| Fare | 25 to <50 | 173 | 891 | 19.42% |
| Fare | 50 to <100 | 108 | 891 | 12.12% |
| Fare | 100 to <200 | 33 | 891 | 3.70% |
| Fare | 200+ | 20 | 891 | 2.24% |

## Categorical and family-count distributions

Percentages use all 891 passengers, including the explicit Missing category.
SibSp counts siblings/spouses aboard; Parch counts parents/children aboard.
PassengerId, Name and Ticket identify records or groups rather than serving as
continuous measurements, so they are not included in the numerical summaries.

| Feature | Category or count | Passengers | Percent |
| --- | --- | --- | --- |
| Pclass | 1 | 216 | 24.24% |
| Pclass | 2 | 184 | 20.65% |
| Pclass | 3 | 491 | 55.11% |
| Sex | female | 314 | 35.24% |
| Sex | male | 577 | 64.76% |
| Embarked | C | 168 | 18.86% |
| Embarked | Missing | 2 | 0.22% |
| Embarked | Q | 77 | 8.64% |
| Embarked | S | 644 | 72.28% |
| SibSp | 0 | 608 | 68.24% |
| SibSp | 1 | 209 | 23.46% |
| SibSp | 2 | 28 | 3.14% |
| SibSp | 3 | 16 | 1.80% |
| SibSp | 4 | 18 | 2.02% |
| SibSp | 5 | 5 | 0.56% |
| SibSp | 8 | 7 | 0.79% |
| Parch | 0 | 678 | 76.09% |
| Parch | 1 | 118 | 13.24% |
| Parch | 2 | 80 | 8.98% |
| Parch | 3 | 5 | 0.56% |
| Parch | 4 | 4 | 0.45% |
| Parch | 5 | 5 | 0.56% |
| Parch | 6 | 1 | 0.11% |

## Survival by sex and passenger class

Survival rate is survivors divided by passengers **within each row's group**.
The first two grouping blocks are marginal summaries; the last is the joint
sex/class cross-tabulation. They describe the same passengers, so their blocks
must not be added together as independent samples.

| Grouping | Group | Passengers | Survivors | Non-survivors | Survival rate |
| --- | --- | --- | --- | --- | --- |
| Sex | female | 314 | 233 | 81 | 74.20% |
| Sex | male | 577 | 109 | 468 | 18.89% |
| Pclass | 1 | 216 | 136 | 80 | 62.96% |
| Pclass | 2 | 184 | 87 | 97 | 47.28% |
| Pclass | 3 | 491 | 119 | 372 | 24.24% |
| Sex and Pclass | female / 1 | 94 | 91 | 3 | 96.81% |
| Sex and Pclass | female / 2 | 76 | 70 | 6 | 92.11% |
| Sex and Pclass | female / 3 | 144 | 72 | 72 | 50.00% |
| Sex and Pclass | male / 1 | 122 | 45 | 77 | 36.89% |
| Sex and Pclass | male / 2 | 108 | 17 | 91 | 15.74% |
| Sex and Pclass | male / 3 | 347 | 47 | 300 | 13.54% |

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

Source: `training/data/train.csv` (891 records, 12 columns).
SHA-256 after UTF-8 decoding and LF newline normalization:
`4a437fde05fe5264e1701a7387ac6fb75393772ba38bb2c9c566405af5af4bd7`.
