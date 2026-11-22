import torch
import torch.nn as nn
import os
import numpy as np
import random
import json
import jsonlines
import csv
import re
import time
import argparse
import sys
import sklearn
import traceback
import tempfile

from torch.utils import data
from tqdm import tqdm
from scipy.special import softmax

from ditto_light.ditto import evaluate, DittoModel
from ditto_light.exceptions import ModelNotFoundError
from ditto_light.dataset import DittoDataset
from ditto_light.config import resolve_task_config


def set_seed(seed: int):
    """
    Helper function for reproducible behavior to set the seed in ``random``, ``numpy``, ``torch``
    """
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def to_str(ent1, ent2, summarizer=None, max_len=256, dk_injector=None):
    """Serialize a pair of data entries

    Args:
        ent1 (Dictionary): the 1st data entry
        ent2 (Dictionary): the 2nd data entry
        summarizer (Summarizer, optional): the summarization module
        max_len (int, optional): the max sequence length
        dk_injector (DKInjector, optional): the domain-knowledge injector

    Returns:
        string: the serialized version
    """
    content = ''
    for ent in [ent1, ent2]:
        if isinstance(ent, str):
            content += ent
        else:
            for attr in ent.keys():
                if attr != 'id':
                    content += 'COL %s VAL %s ' % (attr, ent[attr])
        content += '\t'

    content += '0'

    if summarizer is not None:
        content = summarizer.transform(content, max_len=max_len)

    new_ent1, new_ent2, _ = content.split('\t')
    if dk_injector is not None:
        new_ent1 = dk_injector.transform(new_ent1)
        new_ent2 = dk_injector.transform(new_ent2)

    return new_ent1 + '\t' + new_ent2 + '\t0'


def classify(sentence_pairs, model,
             lm='distilbert',
             max_len=256,
             threshold=None,
             fp16=False):
    """Apply the MRPC model.

    Args:
        sentence_pairs (list of str): the sequence pairs
        model (MultiTaskNet): the model in pytorch
        max_len (int, optional): the max sequence length
        threshold (float, optional): the threshold of the 0's class

    Returns:
        list of float: the scores of the pairs
    """
    inputs = sentence_pairs
    # print('max_len =', max_len)
    dataset = DittoDataset(inputs,
                           max_len=max_len,
                           lm=lm)
    # print(dataset[0])
    iterator = data.DataLoader(dataset=dataset,
                               batch_size=len(dataset),
                               shuffle=False,
                               num_workers=0,
                               collate_fn=DittoDataset.pad)

    # prediction
    all_probs = []
    all_logits = []
    with torch.no_grad():
        # print('Classification')
        for i, batch in enumerate(iterator):
            x, _ = batch
            with torch.autocast(
                device_type=model.device,
                dtype=torch.float16,
                enabled=fp16,
            ):
                logits = model(x)
            probs = logits.softmax(dim=1)[:, 1]
            all_probs += probs.cpu().numpy().tolist()
            all_logits += logits.cpu().numpy().tolist()

    if threshold is None:
        threshold = 0.5

    pred = [1 if p > threshold else 0 for p in all_probs]
    return pred, all_logits

def predict(input_path, output_path, config,
            model,
            batch_size=1024,
            summarizer=None,
            lm='distilbert',
            max_len=256,
            dk_injector=None,
            threshold=None,
            fp16=False):
    """Run the model over the input file containing the candidate entry pairs

    Args:
        input_path (str): the input file path
        output_path (str): the output file path
        config (Dictionary): task configuration
        model (DittoModel): the model for prediction
        batch_size (int): the batch size
        summarizer (Summarizer, optional): the summarization module
        max_len (int, optional): the max sequence length
        dk_injector (DKInjector, optional): the domain-knowledge injector
        threshold (float, optional): the threshold of the 0's class

    Returns:
        None
    """
    pairs = []
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    def process_batch(rows, pairs, writer):
        predictions, logits = classify(pairs, model, lm=lm,
                                       max_len=max_len,
                                       threshold=threshold,
                                       fp16=fp16)
        # try:
        #     predictions, logits = classify(pairs, model, lm=lm,
        #                                    max_len=max_len,
        #                                    threshold=threshold)
        # except:
        #     # ignore the whole batch
        #     return
        scores = softmax(logits, axis=1)
        for row, pred, score in zip(rows, predictions, scores):
            output = {'left': row[0], 'right': row[1],
                'match': pred,
                'match_confidence': score[int(pred)]}
            writer.write(output)

    # batch processing
    start_time = time.time()
    is_text_input = input_path.endswith('.txt')
    input_reader = (
        open(input_path, encoding='utf-8')
        if is_text_input
        else jsonlines.open(input_path)
    )
    with input_reader as reader,\
         jsonlines.open(output_path, mode='w') as writer:
        pairs = []
        rows = []
        for idx, row in tqdm(enumerate(reader)):
            if is_text_input:
                row = row.rstrip('\r\n').split('\t')[:2]
            pairs.append(to_str(row[0], row[1], summarizer, max_len, dk_injector))
            rows.append(row)
            if len(pairs) == batch_size:
                process_batch(rows, pairs, writer)
                pairs.clear()
                rows.clear()

        if len(pairs) > 0:
            process_batch(rows, pairs, writer)

    run_time = time.time() - start_time
    run_tag = '%s_lm=%s_dk=%s_su=%s' % (config['name'], lm, str(dk_injector != None), str(summarizer != None))
    os.system('echo %s %f >> log.txt' % (run_tag, run_time))


def tune_threshold(config, model, hp):
    """Tune the prediction threshold for a given model on a validation set"""
    validset = config['validset']
    task = hp.task

    # summarize the sequences up to the max sequence length
    set_seed(123)
    summarizer = injector = None
    if hp.summarize:
        from ditto_light.summarize import Summarizer

        summarizer = Summarizer(config, lm=hp.lm)
        validset = summarizer.transform_file(validset, max_len=hp.max_len, overwrite=True)

    if hp.dk is not None:
        from ditto_light.knowledge import GeneralDKInjector, ProductDKInjector

        if hp.dk == 'product':
            injector = ProductDKInjector(config, hp.dk)
        else:
            injector = GeneralDKInjector(config, hp.dk)

        validset = injector.transform_file(validset)

    # load dev sets
    valid_dataset = DittoDataset(validset,
                                 max_len=hp.max_len,
                                 lm=hp.lm)

    # print(valid_dataset[0])

    valid_iter = data.DataLoader(dataset=valid_dataset,
                                 batch_size=64,
                                 shuffle=False,
                                 num_workers=0,
                                 collate_fn=DittoDataset.pad)

    # acc, prec, recall, f1, v_loss, th = eval_classifier(model, valid_iter,
    #                                                     get_threshold=True)
    f1, th = evaluate(model, valid_iter, threshold=None)

    # verify F1
    set_seed(123)
    predicts = []
    with tempfile.TemporaryDirectory() as temp_dir:
        prediction_path = os.path.join(temp_dir, "validation.jsonl")
        predict(validset, prediction_path, config, model,
                batch_size=hp.batch_size,
                summarizer=summarizer,
                max_len=hp.max_len,
                lm=hp.lm,
                dk_injector=injector,
                threshold=th,
                fp16=hp.fp16)

        with jsonlines.open(prediction_path, mode="r") as reader:
            for line in reader:
                predicts.append(int(line['match']))

    labels = []
    with open(validset, encoding='utf-8') as fin:
        for line in fin:
            labels.append(int(line.split('\t')[-1]))

    real_f1 = sklearn.metrics.f1_score(labels, predicts)
    print("load_f1 =", f1)
    print("real_f1 =", real_f1)

    return th



def load_model(
    task, path, lm, use_gpu, validset=None, trainset=None, testset=None
):
    """Load a model for a specific task.

    Args:
        task (str): the task name
        path (str): the path of the checkpoint directory
        lm (str): the language model
        use_gpu (boolean): whether to use gpu
    Returns:
        Dictionary: the task config
        MultiTaskNet: the model
    """
    # load models
    checkpoint = os.path.join(path, task, 'model.pt')
    if not os.path.exists(checkpoint):
        raise ModelNotFoundError(checkpoint)

    with open('configs.json', encoding='utf-8') as file:
        configs = {conf['name']: conf for conf in json.load(file)}
    config = resolve_task_config(
        configs,
        task,
        {"trainset": trainset, "validset": validset, "testset": testset},
        required=("validset",),
    )

    if use_gpu:
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
    else:
        device = 'cpu'

    model = DittoModel(device=device, lm=lm)

    saved_state = torch.load(checkpoint, map_location=lambda storage, loc: storage)
    model.load_state_dict(saved_state['model'])
    model = model.to(device)
    model.eval()

    return config, model


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", type=str, default='Structured/Beer')
    parser.add_argument("--trainset", type=str)
    parser.add_argument("--validset", type=str)
    parser.add_argument("--testset", type=str)
    parser.add_argument("--input_path", type=str, default='input/candidates_small.jsonl')
    parser.add_argument("--output_path", type=str, default='output/matched_small.jsonl')
    parser.add_argument("--lm", type=str, default='distilbert')
    parser.add_argument("--use_gpu", dest="use_gpu", action="store_true")
    parser.add_argument("--fp16", dest="fp16", action="store_true")
    parser.add_argument("--checkpoint_path", type=str, default='checkpoints/')
    parser.add_argument("--dk", type=str, default=None)
    parser.add_argument("--summarize", dest="summarize", action="store_true")
    parser.add_argument("--max_len", type=int, default=256)
    parser.add_argument("--batch_size", type=int, default=64)
    hp = parser.parse_args()

    # load the models
    set_seed(123)
    if hp.fp16 and (not hp.use_gpu or not torch.cuda.is_available()):
        parser.error("--fp16 requires --use_gpu and a supported CUDA/ROCm PyTorch GPU")
    config, model = load_model(
        hp.task,
        hp.checkpoint_path,
        hp.lm,
        hp.use_gpu,
        validset=hp.validset,
        trainset=hp.trainset,
        testset=hp.testset,
    )

    summarizer = dk_injector = None
    if hp.summarize:
        from ditto_light.summarize import Summarizer

        summarizer = Summarizer(config, hp.lm)

    if hp.dk is not None:
        from ditto_light.knowledge import GeneralDKInjector, ProductDKInjector

        if 'product' in hp.dk:
            dk_injector = ProductDKInjector(config, hp.dk)
        else:
            dk_injector = GeneralDKInjector(config, hp.dk)

    # tune threshold
    threshold = tune_threshold(config, model, hp)

    # run prediction
    predict(hp.input_path, hp.output_path, config, model,
            batch_size=hp.batch_size,
            summarizer=summarizer,
            max_len=hp.max_len,
            lm=hp.lm,
            dk_injector=dk_injector,
            threshold=threshold,
            fp16=hp.fp16)
