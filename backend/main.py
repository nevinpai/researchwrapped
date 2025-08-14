from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import re
import nltk
import os
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from collections import Counter

# Set the NLTK data path
nltk_data_dir = os.path.join(os.path.dirname(__file__), 'nltk_data')
if os.path.exists(nltk_data_dir):
    nltk.data.path.append(nltk_data_dir)

app = Flask(__name__)
CORS(app, origins=["https://nevinpai.github.io", "http://127.0.0.1:5500", "null"])

def get_researcher_info(orcid_id):
    """
    Fetches the last 10 works of a researcher and their display name.
    """
    # Handle both full URL and just the ID
    orcid_id_only = orcid_id.split('/')[-1]
    
    url = f"https://api.openalex.org/works?filter=author.orcid:https://orcid.org/{orcid_id_only}&per-page=10"
    try:
        response = requests.get(url)
        response.raise_for_status()
        results = response.json().get('results', [])
        if not results:
            return None, None
        
        author_name = "Unknown Author"
        # Find the author in the first paper's authorships that matches the ORCID
        for authorship in results[0].get('authorships', []):
            author_info = authorship.get('author', {})
            if author_info.get('orcid') and author_info['orcid'].endswith(orcid_id_only):
                author_name = author_info.get('display_name', author_name)
                break  # Found the correct author

        return results, author_name
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from OpenAlex: {e}")
        return None, None

def get_abstract(work):
    """
    Extracts the abstract from a work object by fetching the full work details.
    """
    if not work or 'id' not in work:
        return None

    work_id = work['id'].split('/')[-1]
    url = f"https://api.openalex.org/works/{work_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        work_details = response.json()
        return work_details.get('abstract_inverted_index', {})
    except requests.exceptions.RequestException as e:
        print(f"Error fetching work details from OpenAlex: {e}")
        return None

def deinvert_abstract(inverted_index):
    """
    Deinverts the abstract from the inverted index format.
    """
    if not inverted_index:
        return ""
    
    terms = []
    for term, indices in inverted_index.items():
        for index in indices:
            while len(terms) <= index:
                terms.append("")
            terms[index] = term
    return " ".join(terms)

def analyze_abstracts(abstracts):
    """
    Analyzes abstracts for word counts, common verbs, and common nouns.
    """
    stop_words = set(stopwords.words('english'))
    
    text = " ".join(abstracts)
    words = word_tokenize(text.lower())
    
    # Filter for alphabetic words and remove stopwords
    filtered_words = [word for word in words if word.isalpha() and word not in stop_words]
    
    # Overall word frequency
    word_counts = Counter(filtered_words)
    
    # Part-of-speech tagging
    tagged_words = nltk.pos_tag(filtered_words)
    
    # Most common verbs (VB, VBD, VBG, VBN, VBP, VBZ)
    verbs = [word for word, tag in tagged_words if tag.startswith('VB')]
    verb_counts = Counter(verbs)
    
    # Most common nouns (NN, NNS, NNP, NNPS)
    nouns = [word for word, tag in tagged_words if tag.startswith('NN')]
    noun_counts = Counter(nouns)
    
    # Vocabulary Diversity (Lexical Density)
    diversity_score = (len(word_counts) / len(filtered_words)) * 100 if filtered_words else 0
    
    return {
        "total_words": len(filtered_words),
        "unique_words": len(word_counts),
        "diversity_score": round(diversity_score, 2),
        "most_common_words": word_counts.most_common(5),
        "most_common_verbs": verb_counts.most_common(5),
        "most_common_nouns": noun_counts.most_common(5),
    }

@app.route('/api/process', methods=['POST'])
def process_researcher():
    data = request.get_json()
    researcher_id = data.get('researcher_id')

    if not researcher_id:
        return jsonify({'error': 'Researcher ID is required'}), 400

    # Validate ORCID format (e.g., 0000-0001-2345-6789)
    orcid_pattern = re.compile(r'^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$')
    if not orcid_pattern.match(researcher_id.split('/')[-1]):
        return jsonify({'error': 'Invalid ORCID format'}), 400

    works, author_name = get_researcher_info(researcher_id)

    if works is None:
        return jsonify({'error': 'Could not fetch data from OpenAlex'}), 500

    abstracts = []
    for work in works:
        inverted_abstract = get_abstract(work)
        if inverted_abstract:
            abstracts.append(deinvert_abstract(inverted_abstract))

    if not abstracts:
        return jsonify({'error': 'No abstracts found for this researcher'}), 404

    analysis_results = analyze_abstracts(abstracts)
    analysis_results['author_name'] = author_name

    return jsonify(analysis_results)

if __name__ == '__main__':
    app.run(debug=False)
