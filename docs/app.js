document.getElementById('submit-btn').addEventListener('click', () => {
    const researcherId = document.getElementById('researcher-id').value;
    const container = document.querySelector('.container');
    container.innerHTML = '<p class="loading">Generating your Research Wrapped...</p>';

    fetch('https://researchwrapped.onrender.com/api/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ researcher_id: researcherId })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (data.error) {
            container.innerHTML = `<p class="error">${data.error}</p>`;
            return;
        }
        renderResultsCard(data);
    })
    .catch(error => {
        console.error('Error:', error);
        container.innerHTML = '<p class="error">Something went wrong. Please try again.</p>';
    });
});

function renderResultsCard(data) {
    const container = document.querySelector('.container');
    container.innerHTML = ''; // Clear previous content

    const createList = (items) => {
        const ul = document.createElement('ul');
        items.forEach(item => {
            const li = document.createElement('li');
            li.textContent = `${item[0]} `;
            const span = document.createElement('span');
            span.textContent = `(${item[1]})`;
            li.appendChild(span);
            ul.appendChild(li);
        });
        return ul;
    };

    const card = document.createElement('div');
    card.className = 'results-card';

    card.innerHTML = `
        <div class="screenshot-guide top-left"></div>
        <div class="screenshot-guide top-right"></div>
        <div class="card-header">
            <h2>Your Research, Wrapped</h2>
            <p class="author-name"></p>
        </div>
        <div class="card-body">
            <div class="stat-highlight">
                <div class="stat-value"></div>
                <div class="stat-label">Vocabulary Diversity</div>
            </div>
            <div class="stat-section nouns">
                <h3>Most Used Nouns</h3>
            </div>
            <div class="stat-section verbs">
                <h3>Most Used Verbs</h3>
            </div>
        </div>
        <div class="card-footer">
            <a href="https://nevinpai.github.io/researchwrapped/" target="_blank">nevinpai.github.io/researchwrapped</a>
        </div>
        <div class="screenshot-guide bottom-left"></div>
        <div class="screenshot-guide bottom-right"></div>
    `;

    // Safely set text content
    card.querySelector('.author-name').textContent = data.author_name;
    card.querySelector('.stat-value').textContent = `${data.diversity_score}%`;
    
    // Safely append lists
    card.querySelector('.stat-section.nouns').appendChild(createList(data.most_common_nouns));
    card.querySelector('.stat-section.verbs').appendChild(createList(data.most_common_verbs));

    container.appendChild(card);

    const sharePrompt = document.createElement('p');
    sharePrompt.className = 'share-prompt';
    sharePrompt.textContent = 'Screenshot this card to share!';
    container.appendChild(sharePrompt);
}
