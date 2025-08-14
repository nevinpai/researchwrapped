# Research, Wrapped

A minimalist summary of your latest research, ready to share. Inspired by Spotify Wrapped, this tool provides a fun, shareable overview of a researcher's recent work based on their ORCID iD.

[**Live Demo**](https://nevinpai.github.io/researchwrapped/)

![Screenshot of Research, Wrapped](https://i.imgur.com/your-screenshot.png) <!-- It's a good idea to add a real screenshot here! -->

## How It Works

1.  **Enter ORCID**: Provide an ORCID iD (or the full URL).
2.  **Fetch Data**: The backend fetches the 10 most recent publication abstracts from the [OpenAlex API](https://docs.openalex.org/).
3.  **Analyze**: It performs a basic NLP analysis to find the most common nouns and verbs and calculates a vocabulary diversity score.
4.  **Display**: The results are rendered as a clean, shareable card.

## Running Locally

### Frontend

No special setup is needed. Simply open `frontend/index.html` in a modern web browser.

### Backend

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Download NLP data:**
    ```bash
    python download_nltk.py
    ```

4.  **Run the Flask server:**
    ```bash
    python main.py
    ```

The server will be running at `http://127.0.0.1:5000`.

## Deployment

The frontend is deployed as a static site on GitHub Pages. The backend is configured for deployment on Render's free tier.

---

Built with Python, Flask, and vanilla JavaScript.
