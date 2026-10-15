# HIPE-2022 datasets

Multilingual historical documents (mainly newspapers, 1780s–2010s) with named entities annotated and linked to Wikidata. Used here as a high-context set: every toponym appears inside running text, and its Wikidata QID is the ground truth.

> Ehrmann, M., Romanello, M., Najem-Meyer, S., Doucet, A. & Clematide, S. (2022). *Overview of HIPE-2022: Named Entity Recognition and Linking in Multilingual Historical Documents.* CLEF 2022.

- Repository: https://github.com/hipe-eval/HIPE-2022-data
- Zenodo: https://zenodo.org/record/6579950
- Release: **v2.1**, tag `v2.1-test-all-unmasked` (latest). v1.0 and v2.0 are older versions of the same data and are not included.

## Folder layout

```
HIPE-2022/<dataset>/<lang>/HIPE-2022-v2.1-<dataset>-<split>-<lang>.tsv
```

Only the fully annotated train, dev and test files are kept. These were deliberately left out:

- `test-allmasked`: the test set with all annotations removed.
- `test-ELmasked`: the test set without entity links.
- `ajmc-entity-ocr-correction-*`: OCR correction mappings.

## Datasets

| Dataset | Languages | Splits | Document type | Period | Linked to Wikidata | License |
|---|---|---|---|---|---|---|
| `hipe2020` | de, en, fr | train, dev, test (en: dev, test only) | Swiss, Luxembourgish and American newspapers | 1790–2018 | Yes | CC BY-NC-SA 4.0 |
| `newseye` | de, fi, fr, sv | train, dev, dev2, test | Newspapers | 1848–1946 | Yes | CC BY 4.0 |
| `topres19th` | en | train, dev, test | British regional newspapers | 1780–1869 | Yes (toponyms only) | CC BY-NC-SA 4.0 |
| `sonar` | de | dev, test | German newspapers | 1868–1937 | Yes | CC BY 4.0 |
| `ajmc` | de, en, fr | train, dev, test | Classical commentaries (Sophocles) | 1853–1896 | Yes | CC BY |
| `letemps` | fr | train, dev, test | Swiss newspapers | 1804–1981 | **No** | CC BY-NC-SA 4.0 |

## Location mentions and ground truth

Counted over all splits. A mention is one entity span (`B-` tag plus its `I-` tags).

| Dataset | Lang | Location mentions | With QID | `NIL` | Unique QIDs |
|---|---|---|---|---|---|
| hipe2020 | de | 2,923 | 2,803 | 120 | 871 |
| hipe2020 | en | 565 | 487 | 78 | 245 |
| hipe2020 | fr | 4,717 | 4,486 | 231 | 1,254 |
| newseye | de | 7,115 | 4,300 | 2,815 | 1,099 |
| newseye | fi | 1,422 | 1,229 | 193 | 440 |
| newseye | fr | 6,097 | 4,612 | 1,485 | 1,426 |
| newseye | sv | 1,586 | 1,356 | 230 | 491 |
| topres19th | en | 3,726 | 3,527 | 199 | 994 |
| sonar | de | 477 | 448 | 29 | 207 |
| ajmc | de | 43 | 43 | 0 | 27 |
| ajmc | en | 45 | 41 | 0 | 29 |
| ajmc | fr | 24 | 23 | 1 | 19 |
| letemps | fr | 6,367 | 0 | – | – |
| **Total** | | **35,107** | **23,355** | **5,381** | **5,378** |

In topres19th, 186 `BUILDING` and 68 `STREET` mentions also carry a QID. These are not included in the table. In ajmc English, 4 location mentions have neither a QID nor `NIL`.

## File format

Tab-separated, UTF-8, one token per line. The first line is the column header. Documents start with `#` metadata lines, and an empty line separates documents.

| Column | Content |
|---|---|
| `TOKEN` | The token as it appears in the (often OCR'd) text |
| `NE-COARSE-LIT` | Coarse entity type, literal sense, IOB format (`B-loc`, `I-loc`, `O`) |
| `NE-COARSE-METO` | Coarse type, metonymic sense (e.g. a city name used for its government) |
| `NE-FINE-LIT` | Fine-grained type, literal sense (e.g. `B-loc.adm.town`) |
| `NE-FINE-METO` | Fine-grained type, metonymic sense |
| `NE-FINE-COMP` | Entity component (e.g. title, function) |
| `NE-NESTED` | Nested entity type (e.g. the place inside an organisation name) |
| `NEL-LIT` | **Ground truth:** Wikidata QID of the literal entity, `NIL` if no Wikidata entry exists, `_` outside entities |
| `NEL-METO` | Wikidata QID for the metonymic sense |
| `MISC` | Token flags: `NoSpaceAfter`, `EndOfLine`, `EndOfSentence`, `Partial-x:y`, OCR edit distance `LED…` (ajmc) |

Not every dataset fills every column. The metadata line `# hipe2022:applicable_columns` lists the ones in use; the rest contain `_`.

| Dataset | Applicable columns |
|---|---|
| hipe2020 de/fr | all ten |
| hipe2020 en | `TOKEN`, `NE-COARSE-LIT`, `NE-COARSE-METO`, `NEL-LIT`, `MISC` |
| newseye, ajmc | `TOKEN`, `NE-COARSE-LIT`, `NE-FINE-LIT`, `NE-NESTED`, `NEL-LIT`, `MISC` |
| sonar, topres19th | `TOKEN`, `NE-COARSE-LIT`, `NEL-LIT`, `MISC` |
| letemps | `TOKEN`, `NE-COARSE-LIT`, `NE-FINE-LIT`, `NE-NESTED`, `MISC` (no `NEL-LIT`) |

### Entity type labels

The labels differ in case and inventory between datasets. Normalise them before combining.

| Dataset | Coarse types |
|---|---|
| hipe2020 | `loc`, `pers`, `org`, `prod`, `time` |
| letemps | `loc`, `pers`, `org` |
| ajmc | `loc`, `pers`, `work`, `scope`, `object`, `date` |
| newseye | `LOC`, `PER`, `ORG`, `HumanProd` |
| sonar | `LOC`, `PER`, `ORG` |
| topres19th | `LOC`, `BUILDING`, `STREET` |

hipe2020 and letemps also have fine-grained location types in `NE-FINE-LIT`, e.g. `loc.adm.town`, `loc.adm.nat`, `loc.adm.reg`, `loc.phys.hydro`, `loc.oro`, `loc.fac`.

### Document metadata

Each document starts with lines such as:

```
# hipe2022:document_id = EXP-1888-08-03-a-i0030
# hipe2022:date = 1888-08-03
# hipe2022:language = fr
# hipe2022:document_type = newspaper
# hipe2022:dataset = hipe2020
# hipe2022:applicable_columns = TOKEN NE-COARSE-LIT ...
```

There are also dataset-specific lines, e.g. `# <dataset>:publication_title`, `version`, `doi` and `original_license`. Some datasets add more:

- topres19th: `place_publication` and OCR quality scores;
- ajmc: `author`, `title` and `page`.

## Reading the data

```python
def read_hipe(path):
    """Yield (doc_meta, tokens) per document; tokens are dicts keyed by column name."""
    with open(path, encoding="utf-8") as f:
        cols = f.readline().rstrip("\n").split("\t")
        meta, toks = {}, []
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("# hipe2022:document_id"):
                if toks:
                    yield meta, toks
                meta, toks = {}, []
            if line.startswith("#") and "=" in line:
                k, v = line[1:].split("=", 1)
                meta[k.strip()] = v.strip()
            elif line and not line.startswith("#"):
                toks.append(dict(zip(cols, line.split("\t"))))
        if toks:
            yield meta, toks

def location_mentions(toks):
    """Group IOB tokens into location mentions with their QID (ground truth)."""
    mentions, cur = [], None
    for i, t in enumerate(toks):
        tag = t["NE-COARSE-LIT"]
        if tag.startswith("B-") and tag[2:].lower() == "loc":
            cur = {"start": i, "tokens": [t["TOKEN"]], "qid": t["NEL-LIT"]}
            mentions.append(cur)
        elif tag.startswith("I-") and cur is not None and tag[2:].lower() == "loc":
            cur["tokens"].append(t["TOKEN"])
        else:
            cur = None
    return mentions
```

## Coverage by data category

| Category | Available | Notes |
|---|---|---|
| Name | Yes | The mention as written, often with historical spelling and OCR errors |
| Geography | Via Wikidata | Coordinates, type and admin unit can be fetched from the QID. These come from the same entity that defines the ground truth, so they reveal the answer |
| Time and source | Yes | Document date, publication title and language per document |
| Text context | Yes, rich | The full surrounding document |

## Known issues

- **letemps has no entity links.** Without `NEL-LIT` there are no QIDs, so it has no ground truth for matching. Use it for recognition only, or leave it out.
- **hipe2020 English has no train split.**
- **newseye has many `NIL` links**, about 40 % in German. These locations have no Wikidata entry. Keep them as "no match" cases rather than dropping them.
- **OCR noise.** Tokens are OCR output, e.g. `dc` for `de` and `ſ` for `s`. Multi-token mentions can also be split by OCR errors (`Ame - rikan`).
- **ajmc has very few locations** (112 mentions in total); its entities are mostly people and works.
- **Non-commercial licences.** hipe2020, letemps and topres19th are CC BY-NC-SA 4.0.
- **Not Hebrew or Arabic.** The languages are de, en, fr, fi and sv, so this set tests how context helps linking, not cross-script matching.
