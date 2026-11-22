# Using Ditto with Our Data

This guide describes how to train Ditto and run matching when our data is
ready. Ditto does not split raw records, serialize project tables, or create
labels automatically. Prepare the files below yourself or with a project data
preparation step, then point Ditto at them.

## 1. Prepare the labeled data

Create separate training, validation, and test files. Each line in each file
must contain a labeled record pair in Ditto's tab-separated format:

```text
<serialized left record><TAB><serialized right record><TAB><label>
```

`<TAB>` means a literal tab character. Labels are `1` for a match and `0` for
a non-match. Serialize each record as attributes in `COL name VAL value`
form, for example:

```text
COL title VAL Alexandria COL country VAL Egypt<TAB>COL name VAL Alexandria COL region VAL Egypt<TAB>1
```

Keep actual fields free of tab and newline characters, since tabs delimit the
pair and label. Use the same attribute names consistently where possible.
Do not include record IDs in the serialized text; Ditto matches record content.

Choose the split assignments before training. Avoid placing the same entity
records in multiple splits, and include both matches and non-matches in the
validation set so threshold selection is meaningful. Ditto uses validation F1
to select the best checkpoint and reports test F1.

For example, the files could be placed at:

```text
datasets/your_dataset/train.txt
datasets/your_dataset/valid.txt
datasets/your_dataset/test.txt
```

## 2. Install dependencies

For an AMD GPU, first follow
[AMD's PyTorch installation guide](https://rocm.docs.amd.com/projects/ai-ecosystem/en/latest/frameworks/pytorch/install.html)
to install a PyTorch build that matches the supported ROCm, operating system,
Python version, and GPU. Then install the repository requirements from the
repository root, keeping the ROCm-enabled PyTorch build in the environment:

```powershell
python -m pip install -r requirements.txt
```

Verify that PyTorch detects the GPU:

```powershell
python -c "import torch; print(torch.cuda.is_available()); print(torch.version.hip)"
```

ROCm-enabled PyTorch exposes AMD devices through PyTorch's `torch.cuda` API.
This project currently relies on that API for accelerator detection. If
`torch.cuda.is_available()` is false, Ditto will use the CPU; `--fp16` will
require a supported, detected GPU. Check AMD's current support information
before choosing a platform; the Windows HIP SDK does not currently list
PyTorch among its supported AI frameworks.

## 3. Train a model

From `Methods\ditto`, pass the three files explicitly. The task name is
used to name the checkpoint and does not need to be added to `configs.json`
when all dataset paths are provided:

```powershell
Set-Location Methods\ditto
python train_ditto.py --task pleiades_trismegistos `
  --trainset ..\..\datasets\your_dataset\train.txt `
  --validset ..\..\datasets\your_dataset\valid.txt `
  --testset ..\..\datasets\your_dataset\test.txt `
  --lm distilbert --max_len 128 --batch_size 16 --n_epochs 5 `
  --class_weighted --save_model
```

Adjust the paths, model, maximum sequence length, batch size, and epoch count
for the dataset and available hardware. Use `--class_weighted` when matches
are much rarer than non-matches. It can be omitted for more balanced data.
`--save_model` stores the best validation checkpoint at
`checkpoints/pleiades_trismegistos/model.pt` by default.

Training automatically uses a GPU detected by PyTorch and otherwise runs on
the CPU. `--fp16` enables PyTorch's native mixed-precision training on a
supported GPU; Apex is not needed. Start without `--fp16` if you are unsure
whether the selected backend supports it.

## 4. Prepare candidate pairs for matching

Matching input is a JSON Lines file: one JSON value per line, where each value
is a two-element list containing the left and right record objects. Each record
object should contain its attributes; an optional `id` is preserved in output
but not included in the text sent to the model.

```json
[{"id":"p1","title":"Alexandria","country":"Egypt"},{"id":"t9","name":"Alexandria","region":"Egypt"}]
```

Create one such line for each candidate pair and save it as, for example,
`datasets/your_dataset/candidates.jsonl`. The matching tool scores only the
pairs supplied; candidate generation remains a separate step.

## 5. Run matching

Run the matcher from `Methods\ditto` using the same task name and validation
file as training:

```powershell
python matcher.py --task pleiades_trismegistos `
  --validset ..\..\datasets\your_dataset\valid.txt `
  --checkpoint_path checkpoints\ `
  --input_path ..\..\datasets\your_dataset\candidates.jsonl `
  --output_path ..\..\datasets\your_dataset\predictions.jsonl `
  --lm distilbert --max_len 128
```

The validation set is used to tune the match threshold. The predictions file
contains the input records, a `match` value (`0` or `1`), and a
`match_confidence` score. Add `--use_gpu` to run matching on a supported
PyTorch GPU. Add `--fp16` only when that GPU backend supports PyTorch AMP.

If training used `--summarize`, also pass the same `--trainset` and `--testset`
paths to `matcher.py`. Custom task names do not provide the task-specific
configuration needed for `--dk` domain-knowledge injection.
