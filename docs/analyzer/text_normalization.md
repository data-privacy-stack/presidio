# Full-width and invisible characters

Entities written with full-width characters (`１２３`, `ＡＢＣ`), which many Chinese and Japanese input methods produce, or with zero-width spaces inserted between their characters, are not matched by patterns and models that expect ASCII.
To detect them, give the `AnalyzerEngine` a text normalizer:

```python
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.text_normalizers import FullWidthAndInvisibleCharsNormalizer

analyzer = AnalyzerEngine(text_normalizer=FullWidthAndInvisibleCharsNormalizer())
results = analyzer.analyze(text="My email is ｊｏｈｎ＠ｅｘａｍｐｌｅ．ｃｏｍ", language="en")
print(results)
```

The text is not normalized unless a text normalizer is given.

## What the default normalizer changes

`FullWidthAndInvisibleCharsNormalizer`:

- Folds full-width letters and digits to ASCII, and full-width symbols too when they sit between letters or digits, as in an email address or an ID number. Full-width punctuation in running text, such as `，` after a Han character, is kept as written.
- Removes zero-width spaces and a few other invisible characters (soft hyphen, word joiner, invisible math operators, byte order mark). Zero-width joiners and non-joiners are kept, since they are part of ordinary spelling in some scripts.

Nothing else changes. In particular there is no Unicode compatibility (NFKC) normalization, which would rewrite characters such as `①`, `²` or half-width katakana.

## How the analyzer uses it

With a text normalizer, the analyzer:

- Runs the NLP engine, all recognizers and context enhancement on the normalized text. When the normalization changed the text, pattern recognizers also run on the original text, so patterns written for it keep matching.
- Compares the allow-list with the normalized text. In `exact` mode each entry is normalized the same way first, so an entry can be written in either form. In `regex` mode the patterns run against the normalized text.
- Returns results with offsets in the original text, so anonymization replaces the original characters, including invisible characters inside a match. The analysis explanation notes when a match was found on normalized text that differs from the original.

Validation, such as a checksum, runs on the normalized value, so entities that were missed before can now be returned.
If you pass precomputed `nlp_artifacts` to `analyze`, compute them on the normalized text.

## Configuration file

In the [analyzer configuration file](analyzer_engine_provider.md), add a `text_normalizer` section next to `context_aware_enhancer`:

```yaml
text_normalizer:
  type: full_width_and_invisible_chars
```

`type` defaults to `full_width_and_invisible_chars`, so an empty `text_normalizer:` section turns on the same normalizer.

## Writing your own normalizer

Subclass `TextNormalizer` and return a `NormalizedText`: the normalized text, and for each of its characters the range of original characters it comes from (`starts` and `ends`).
Both lists have the length of the normalized text, neither decreases, and each range is non-empty and within the original text.
A removed character appears in no range, characters produced from one original character share its range, and a character produced from several original characters gets a range that covers all of them.
The analyzer maps spans between the two texts, so a normalizer only builds the text and the two lists. The same text and language must always give the same result.

```python
from presidio_analyzer.text_normalizers import NormalizedText, TextNormalizer


class DropHashNormalizer(TextNormalizer):
    """Remove '#' characters, as in IDs written as 1234#5678."""

    def normalize(self, text: str, language: str) -> NormalizedText:
        kept = [i for i, char in enumerate(text) if char != "#"]
        return NormalizedText(
            original_text=text,
            text="".join(text[i] for i in kept),
            starts=kept,
            ends=[i + 1 for i in kept],
        )
```

The `language` argument lets a normalizer behave differently per language.
