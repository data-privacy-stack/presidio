"""Tests adapted from the spacy_stanza repo"""

import warnings

from spacy.lang.en import EnglishDefaults


import pytest

from presidio_analyzer.nlp_engine.stanza_nlp_engine import (
    MultiWordTokenSurface,
    StanzaTokenizer,
    load_pipeline,
)


def tags_equal(act, exp):
    """Check if each actual tag in act is equal to one or more expected tags in exp."""
    return all(a == e if isinstance(e, str) else a in e for a, e in zip(act, exp))


@pytest.fixture(scope="module")
def stanza_pipeline(nlp_engines):
    pytest.importorskip("stanza")
    stanza_en = nlp_engines.get("stanza_en", None)
    if stanza_en:
        stanza_en.load()
        return stanza_en.nlp["en"]

    import stanza

    lang = "en"
    stanza.download(lang)
    nlp = load_pipeline(lang)
    return nlp


@pytest.fixture(scope="module")
def stanza_pipeline_de(nlp_engines):
    """Load a German Stanza pipeline, with the processors StanzaNlpEngine uses."""
    pytest.importorskip("stanza")
    stanza_de = nlp_engines.get("stanza_de", None)
    if stanza_de:
        stanza_de.load()
        return stanza_de.nlp["de"]

    import stanza

    lang = "de"
    stanza.download(lang)
    # Same processors as StanzaNlpEngine.load uses, so that the mwt
    # processor is part of the pipeline (Stanza adds it for German)
    nlp = load_pipeline(lang, processors="tokenize,pos,lemma,ner")
    return nlp


@pytest.mark.skip_engine("stanza_en")
def test_spacy_stanza_english(stanza_pipeline):
    nlp = stanza_pipeline
    assert nlp.Defaults == EnglishDefaults
    lang = "en"
    doc = nlp("Hello world! This is a test.")

    # Expected POS tags. Note: Different versions of stanza result in different
    # POS tags.
    # fmt: off
    pos_exp = ["INTJ", "NOUN", "PUNCT", ("DET", "PRON"), ("VERB", "AUX"), "DET", "NOUN", "PUNCT"]

    assert [t.text for t in doc] == ["Hello", "world", "!", "This", "is", "a", "test", "."]
    assert [t.lemma_ for t in doc] == ["hello", "world", "!", "this", "be", "a", "test", "."]
    assert tags_equal([t.pos_ for t in doc], pos_exp)

    assert [t.is_sent_start for t in doc] == [True, False, False, True, False, False, False, False]
    assert any([t.is_stop for t in doc])
    # fmt: on
    assert len(list(doc.sents)) == 2
    assert doc.has_annotation("TAG")
    assert doc.has_annotation("SENT_START")

    docs = list(nlp.pipe(["Hello world", "This is a test"]))
    assert docs[0].text == "Hello world"
    assert docs[1].text == "This is a test"
    assert tags_equal([t.pos_ for t in docs[1]], pos_exp[3:-1])
    assert doc.ents == tuple()

    # Test NER
    doc = nlp("Barack Obama was born in Hawaii.")
    assert len(doc.ents) == 2
    assert doc.ents[0].text == "Barack Obama"
    assert doc.ents[0].label_ == "PERSON"
    assert doc.ents[1].text == "Hawaii"
    assert doc.ents[1].label_ == "GPE"

    # Test whitespace alignment
    doc = nlp(" Barack  Obama  was  born\n\nin Hawaii.\n")
    assert [t.pos_ for t in doc] == [
        "SPACE",
        "PROPN",
        "SPACE",
        "PROPN",
        "SPACE",
        "AUX",
        "SPACE",
        "VERB",
        "SPACE",
        "ADP",
        "PROPN",
        "PUNCT",
        "SPACE",
    ]
    assert [t.dep_ for t in doc] == [
        "",
        "nsubj:pass",
        "",
        "flat",
        "",
        "aux:pass",
        "",
        "root",
        "",
        "case",
        "root",
        "punct",
        "",
    ]
    assert [t.head.i for t in doc] == [0, 7, 2, 1, 4, 7, 6, 7, 8, 10, 10, 10, 12]
    assert len(doc.ents) == 2
    assert doc.ents[0].text == "Barack  Obama"
    assert doc.ents[0].label_ == "PERSON"
    assert doc.ents[1].text == "Hawaii"
    assert doc.ents[1].label_ == "GPE"

    # Test serialization
    reloaded_nlp = load_pipeline(lang).from_bytes(nlp.to_bytes())
    assert reloaded_nlp.config.to_str() == nlp.config.to_str()


class _FakeStanzaWord:
    def __init__(self, text, head, upos="X", deprel="dep"):
        self.text = text
        self.head = head
        self.upos = upos
        self.deprel = deprel


class _FakeStanzaToken:
    def __init__(self, words, text=None):
        self.words = words
        # A Stanza multi-word token's text is the surface form,
        # not the concatenation of the words it was expanded into
        self.text = text if text is not None else words[0].text


class _FakeStanzaSentence:
    def __init__(self, tokens):
        self.tokens = tokens


class _FakeStanzaDoc:
    def __init__(self, sentences):
        self.sentences = sentences


def test_get_tokens_with_heads_collapses_mwt_and_remaps_heads():
    """Test that mwt tokens are collapsed and dependency heads remapped.

    Covers languages whose Stanza pipeline has both the mwt and the parse
    processors (e.g. Spanish, French): heads of words around a collapsed
    multi-word token must point at the token that covers their governor.
    """
    sentence = _FakeStanzaSentence(
        [
            _FakeStanzaToken([_FakeStanzaWord("Ich", head=2)]),
            _FakeStanzaToken([_FakeStanzaWord("gehe", head=0)]),
            # "im" is expanded by the mwt processor into "in" + "dem"
            _FakeStanzaToken(
                [_FakeStanzaWord("in", head=5), _FakeStanzaWord("dem", head=3)],
                text="im",
            ),
            _FakeStanzaToken([_FakeStanzaWord("Schule", head=2)]),
        ]
    )
    second_sentence = _FakeStanzaSentence(
        [
            _FakeStanzaToken([_FakeStanzaWord("Sie", head=2)]),
            _FakeStanzaToken([_FakeStanzaWord("lacht", head=0)]),
        ]
    )
    snlp_doc = _FakeStanzaDoc([sentence, second_sentence])

    tokens, heads = StanzaTokenizer._StanzaTokenizer__get_tokens_with_heads(snlp_doc)

    # The multi-word token is collapsed into its surface form,
    # other tokens are flattened words as before
    assert [token.text for token in tokens] == [
        "Ich",
        "gehe",
        "im",
        "Schule",
        "Sie",
        "lacht",
    ]
    assert isinstance(tokens[2], MultiWordTokenSurface)
    # text and lemma are the surface form, other annotations come
    # from the first expanded word
    assert tokens[2].lemma == "im"
    assert tokens[2].upos == "X"

    # Relative heads: "Ich" -> "gehe", "gehe" is root, "im" -> "Schule",
    # "Schule" -> "gehe", and the second sentence's words are unaffected
    # by the words collapsed in the first one
    assert heads == [1, 0, 1, -2, 1, 0]


@pytest.mark.skip_engine("stanza_de")
def test_spacy_stanza_german_multiword_tokens(stanza_pipeline_de):
    """Test that German multi-word tokens keep text, tokens and entities intact.

    Regression test for issue #2249: German preposition-article
    contractions are multi-word tokens (mwt) which Stanza's mwt processor
    expands ("im" -> "in" + "dem"). Flattening the expanded words into the
    token list used to break alignment with the original text, so the doc
    text was replaced by space-separated expanded tokens and all entities
    were dropped.
    """
    text = "Wir treffen uns im B\u00fcro mit Thomas Bergmann."
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        doc = stanza_pipeline_de(text)

    # The original text is preserved, not replaced by expanded tokens,
    # and no alignment / multiword warnings are emitted
    assert doc.text == text
    assert not [
        warning for warning in caught if "multiword token" in str(warning.message)
    ]

    # The contraction is kept as a single token in its surface form
    assert [t.text for t in doc] == [
        "Wir",
        "treffen",
        "uns",
        "im",
        "B\u00fcro",
        "mit",
        "Thomas",
        "Bergmann",
        ".",
    ]
    # ... with the surface form as its lemma ...
    assert doc[3].lemma_ == "im"
    # ... and annotations borrowed from the first expanded word
    assert doc[3].pos_ in ("ADP", "APPR")

    # NER entities keep the character offsets of the original text
    expected_start = text.index("Thomas Bergmann")
    assert len(doc.ents) == 1
    assert doc.ents[0].text == "Thomas Bergmann"
    assert doc.ents[0].start_char == expected_start
    assert doc.ents[0].end_char == expected_start + len("Thomas Bergmann")


@pytest.mark.skip_engine("stanza_de")
@pytest.mark.parametrize(
    "contraction",
    ["im", "am", "zum", "zur", "beim", "vom", "ins", "ans"],
)
def test_spacy_stanza_german_contractions_keep_text_and_offsets(
    stanza_pipeline_de, contraction
):
    """Test that every German contraction preserves the text and token offsets."""
    # Every German contraction is expanded by the mwt processor,
    # the doc text and token offsets must survive all of them
    text = f"Wir gehen {contraction} Termin mit Thomas Bergmann."
    doc = stanza_pipeline_de(text)

    assert doc.text == text
    assert contraction in [t.text for t in doc]
    # every token's character span maps back onto itself in the original text
    for token in doc:
        assert doc.text[token.idx : token.idx + len(token.text)] == token.text


@pytest.mark.skip_engine("stanza_de")
def test_spacy_stanza_german_mwt_token_indices_cover_trailing_matches(
    stanza_pipeline_de,
):
    """Test that tokens cover matches at the end of indented German text."""
    # Regression test for the analyzer HTTP 500 on indented text:
    # with a multi-word token and enough whitespace, the replaced
    # (shorter) doc text used to end before a pattern match at the end
    # of the original text, so LemmaContextAwareEnhancer raised
    # "Did not find word ... in the list of tokens".
    text = "Wir treffen uns im B\u00fcro.\n" + " " * 40 + "\nServer 192.168.10.20"
    doc = stanza_pipeline_de(text)

    assert doc.text == text
    for token in doc:
        assert doc.text[token.idx : token.idx + len(token.text)] == token.text

    # a match on the trailing IP address is covered by a token, so that
    # LemmaContextAwareEnhancer._find_index_of_match_token finds it
    ip_start = text.index("192.168.10.20")
    assert any(token.idx <= ip_start < token.idx + len(token.text) for token in doc)
