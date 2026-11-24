# DeepER

1. Represent each populated text attribute with a multilingual LaBSE vector.
   When an attribute contains aliases, mean-pool their normalized vectors to
   form its distributed representation.
2. Build an attribute-wise similarity vector for each query/candidate pair.
3. Train a supervised binary classifier from labeled matches and non-matches.

LaBSE replaces the paper's monolingual GloVe lookup so names and descriptions
from different languages can be compared in a shared embedding space. The
toponym-specific pair vector also contains minimum coordinate distance,
temporal-range overlap/gap, and IPA similarity. Missing values are imputed by
the classifier pipeline and represented with missingness indicators.

## Train

The fastest end-to-end option is the runner below. It trains from `train.tsv`,
selects the match threshold using maximum F5 on `validation.tsv` (beta=5,
therefore emphasizing recall), then evaluates
once on the held-out `test.tsv`. It prints precision, recall, F1, accuracy, and
confusion counts for the test split:

```powershell
python -m Methods.deepER.run_deeper
```

By default this runs MEHDIE Kima → Yaqut and tunes the threshold on validation.
Pass `--threshold` only to override validation-based threshold selection. Choose
another dataset direction or save model/prediction files with:

```powershell
python -m Methods.deepER.run_deeper `
  --test-set WIKIDATA_ZH_RU `
  --source-dataset WIKIDATA_ZH `
  --target-dataset WIKIDATA_RU `
  --save-model Methods/deepER/models/wikidata_zh_ru.joblib `
  --predictions-out Methods/deepER/results/wikidata_zh_ru.tsv
```

To supply a fixed threshold instead, add `--threshold 0.6`; the runner still
reports validation metrics at that threshold and uses it unchanged for test.
Test output reports F5 and F1, with F5 used for threshold selection.

Run `python -m Methods.deepER.run_deeper --help` to see all options.

The runner reads the project's train, validation, and test candidate splits
and expects the multilingual LaBSE model to be available (downloaded by
Sentence Transformers on first use if needed). The loader reads `HF_TOKEN`
from the process environment or the repository-root `.env` and passes it to
Hugging Face when loading LaBSE. Both `HF_TOKEN=value` and `HF_TOKEN: value`
entries are supported. Unique attribute texts are encoded in batches with
progress bars; classifier fitting also reports tree-building progress.

## Train only

Run from the repository root. The command reads only the selected test set's
`train.tsv` with all available record attributes; do not train on validation or
test candidates. At inference, load the same attribute categories (or omit
`attribute_categories` to keep all fields) so the training and test feature
availability is consistent.

```powershell
python -m Methods.deepER.train_deeper `
  --test-set WIKIDATA_ZH_RU `
  --source-dataset WIKIDATA_ZH `
  --target-dataset WIKIDATA_RU `
  --out Methods/deepER/models/wikidata_zh_ru.joblib
```

Train a separate model for each dataset pair and direction. The multilingual
LaBSE checkpoint is downloaded by Sentence Transformers on first use if it is
not already cached.

## Use in the shared experiment interface

```python
from Methods.deepER.deeper import load_classifier
from experiments import load_pairs
from experiments.matching import call_matching_methods
from data_loader import DatasetName, TestSetName

pairs = load_pairs(
    TestSetName.WIKIDATA_ZH_RU,
    DatasetName.WIKIDATA_ZH,
    DatasetName.WIKIDATA_RU,
    dataset_type="test",
)
classifier = load_classifier("Methods/deepER/models/wikidata_zh_ru.joblib")
results = call_matching_methods(
    pairs,
    methods=("deeper",),
    deeper_classifier=classifier,
    deeper_threshold=0.5,
)
```

The result is grouped by query and matches the other pair classifiers:
`{"candidate": id, "match": bool, "probability": float}`. Use
`experiments.metrics.candidate_predictions` and `calculate_metrics` to evaluate
it against the same candidate set and ground truth as the other methods.
