from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
import re
from collections import Counter

try:
    import spacy
    from spacy.lang.en.stop_words import STOP_WORDS as SPACY_STOPWORDS
    _NLP = None
    _SPACY_AVAILABLE = True
except Exception:
    _SPACY_AVAILABLE = False
    _NLP = None


app = FastAPI(title="ResearchWrapped API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


OPENALEX_BASE = "https://api.openalex.org"


def get_nlp():
    global _NLP
    if _NLP is None and _SPACY_AVAILABLE:
        try:
            _NLP = spacy.load("en_core_web_sm")
        except Exception:
            # spaCy installed but model missing; fall back to blank English pipeline (no POS, no NPs)
            _NLP = spacy.blank("en")
    return _NLP


def reconstruct_openalex_abstract(inv_idx: Dict[str, List[int]]) -> str:
    # OpenAlex stores abstracts as {token: [positions...]}. Reconstruct to positional list.
    if not inv_idx:
        return ""
    max_pos = 0
    for positions in inv_idx.values():
        if positions:
            max_pos = max(max_pos, max(positions))
    tokens = [None] * (max_pos + 1)
    for token, positions in inv_idx.items():
        for pos in positions:
            if 0 <= pos < len(tokens):
                tokens[pos] = token
    joined = " ".join(t for t in tokens if t)
    # Clean OpenAlex artifacts (like '\n')
    return re.sub(r"\s+", " ", joined).strip()


def simple_tokenize(text: str) -> List[str]:
    # Basic, robust tokenizer if spaCy POS isn't available
    return re.findall(r"[A-Za-z][A-Za-z\-']+", text.lower())


def extract_stats(abstracts: List[str]) -> Dict[str, Any]:
    corpus = "\n".join(abstracts)
    nlp = get_nlp()

    if _SPACY_AVAILABLE and nlp and nlp.pipe_names:
        # Full pipeline or partial pipeline
        doc = nlp(corpus)
        stopwords = SPACY_STOPWORDS if "spacy.lang.en" else set()

        # Most used words (lemmas, excluding stopwords and punctuation)
        word_lemmas: List[str] = []
        for token in doc:
            if token.is_alpha and not token.is_stop and len(token.lemma_) > 1:
                # Use lowercase lemma
                word_lemmas.append(token.lemma_.lower())
        top_words = Counter(word_lemmas).most_common(15)

        # Most used conjugations (verbs) aggregated by lemma
        verb_lemmas: List[str] = []
        if doc.has_annotation("POS"):
            for token in doc:
                if token.pos_ == "VERB" and token.lemma_.isalpha():
                    verb_lemmas.append(token.lemma_.lower())
        top_verbs = Counter(verb_lemmas).most_common(10)

        # Topics as frequent noun chunks (normalized)
        topic_chunks: List[str] = []
        if doc.has_annotation("SENT_START") and hasattr(doc, "noun_chunks"):
            for chunk in doc.noun_chunks:
                text = chunk.text.strip().lower()
                # filter very short chunks and stopword-only chunks
                if len(text) > 3 and not all(w in stopwords for w in text.split()):
                    topic_chunks.append(text)
        top_topics = Counter(topic_chunks).most_common(10)
    else:
        # Fallback without spaCy model: basic word counts, heuristic verbs/topics empty
        tokens = simple_tokenize(corpus)
        # Minimal stopword list
        basic_stop = {
            'the','a','an','and','or','but','if','then','else','for','to','of','in','on','with','as','by','is','are','was','were','be','been','it','its','that','this','these','those','from','at','we','our','you','your','they','their','i','me','my','he','she','his','her','them','there','here','over','under','than','such','can','may','might','should','would','could','not','no','yes','do','does','did','have','has','had'
        }
        words = [t for t in tokens if t not in basic_stop and len(t) > 2]
        top_words = Counter(words).most_common(15)
        top_verbs = []
        top_topics = []

    return {
        "top_words": [{"term": w, "count": c} for w, c in top_words],
        "top_verbs": [{"term": w, "count": c} for w, c in top_verbs],
        "topics": [{"term": w, "count": c} for w, c in top_topics],
    }


def fetch_author_by_orcid(orcid: str) -> Dict[str, Any]:
    url = f"{OPENALEX_BASE}/authors"
    params = {"filter": f"orcid:{orcid}", "per_page": 1}
    resp = requests.get(url, params=params, timeout=20)
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to query OpenAlex authors")
    data = resp.json()
    results = data.get("results", [])
    if not results:
        raise HTTPException(status_code=404, detail="Author not found for given ORCID")
    return results[0]


def fetch_recent_works(author_openalex_id: str, max_items: int = 10) -> List[Dict[str, Any]]:
    # author_openalex_id should be like "https://openalex.org/Axxxx"
    works_url = f"{OPENALEX_BASE}/works"
    filter_str = f"authorships.author.id:{author_openalex_id},has_abstract:true"
    resp = requests.get(
        works_url,
        params={
            "filter": filter_str,
            "sort": "publication_year:desc",
            "per_page": 25,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to query OpenAlex works")
    results = resp.json().get("results", [])
    # Keep only works with abstract and a year
    filtered: List[Dict[str, Any]] = []
    for w in results:
        if w.get("abstract_inverted_index"):
            filtered.append(w)
        if len(filtered) >= max_items:
            break
    return filtered


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/analyze")
def analyze(
    orcid: Optional[str] = Query(None, description="ORCID iD, e.g., 0000-0002-1825-0097"),
    author: Optional[str] = Query(None, description="OpenAlex author ID or URL, e.g., A1969205032 or https://openalex.org/A1969205032"),
) -> Dict[str, Any]:
    if not orcid and not author:
        raise HTTPException(status_code=400, detail="Provide either 'orcid' or 'author' parameter")
    if orcid:
        author_obj = fetch_author_by_orcid(orcid)
    else:
        author_norm = author.strip()
        if author_norm.startswith("http"):
            if "/A" in author_norm:
                author_id_url = author_norm
            else:
                raise HTTPException(status_code=400, detail="Unsupported author URL format")
        elif author_norm.startswith("A"):
            author_id_url = f"https://openalex.org/{author_norm}"
        else:
            raise HTTPException(status_code=400, detail="Author must be an OpenAlex author ID (e.g., Axxxx) or URL")

        resp = requests.get(f"{OPENALEX_BASE}/authors/{author_id_url.split('/')[-1]}", timeout=20)
        if resp.status_code != 200:
            raise HTTPException(status_code=404, detail="Author not found for given ID")
        author_obj = resp.json()

    author_id = author_obj.get("id")
    display_name = author_obj.get("display_name")
    works = fetch_recent_works(author_id, max_items=10)

    abstracts: List[str] = []
    titles: List[str] = []
    years: List[int] = []
    for w in works:
        inv = w.get("abstract_inverted_index")
        abstract_text = reconstruct_openalex_abstract(inv)
        if abstract_text:
            abstracts.append(abstract_text)
            titles.append(w.get("title", ""))
            years.append(w.get("publication_year"))

    if not abstracts:
        raise HTTPException(status_code=404, detail="No abstracts found for the last works")

    stats = extract_stats(abstracts)

    return {
        "author_name": display_name,
        "orcid": orcid,
        "works_used": len(abstracts),
        "titles": titles,
        "years": years,
        **stats,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


