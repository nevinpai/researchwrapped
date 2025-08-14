import nltk

def download_nltk_data():
    """
    Downloads the necessary NLTK data.
    """
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords')
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt')
    try:
        nltk.data.find('taggers/averaged_perceptron_tagger')
    except LookupError:
        nltk.download('averaged_perceptron_tagger')

if __name__ == '__main__':
    download_nltk_data()
    print("NLTK data is ready.")
