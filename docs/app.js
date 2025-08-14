const identifierInput = document.getElementById('identifier');
const backendInput = document.getElementById('backend');
const goButton = document.getElementById('go');
const resultSection = document.getElementById('result');
const authorEl = document.getElementById('author');
const worksEl = document.getElementById('works');
const wordsEl = document.getElementById('top_words');
const verbsEl = document.getElementById('top_verbs');
const topicsEl = document.getElementById('topics');
const canvas = document.getElementById('shareCanvas');
const downloadBtn = document.getElementById('download');
const tweetLink = document.getElementById('tweet');

function deriveParamsFromIdentifier(raw) {
  const str = (raw || '').trim();
  if (!str) return {};
  // ORCID like 0000-0002-1825-0097
  if (/\b\d{4}-\d{4}-\d{4}-\d{3}[\dX]\b/.test(str)) {
    return { orcid: str };
  }
  // OpenAlex author URL or ID Axxxx
  if (/openalex\.org\/.+/.test(str)) {
    return { author: str };
  }
  if (/^A\d+$/i.test(str)) {
    return { author: str };
  }
  // Fallback: treat as orcid
  return { orcid: str };
}

async function fetchAnalysis(baseUrl, params) {
  const usp = new URLSearchParams(params);
  const url = `${baseUrl.replace(/\/$/, '')}/analyze?${usp.toString()}`;
  const res = await fetch(url, { headers: { 'Accept': 'application/json' } });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json();
}

function renderList(el, items) {
  el.innerHTML = '';
  for (const { term, count } of items) {
    const li = document.createElement('li');
    li.textContent = `${term} (${count})`;
    el.appendChild(li);
  }
}

function drawShareCard(data) {
  const ctx = canvas.getContext('2d');
  const W = canvas.width;
  const H = canvas.height;

  // background
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, W, H);
  ctx.strokeStyle = '#111111';
  ctx.lineWidth = 8;
  ctx.strokeRect(8, 8, W - 16, H - 16);

  // Title
  ctx.fillStyle = '#111111';
  ctx.font = 'bold 54px Georgia, serif';
  ctx.fillText('Research Wrapped', 60, 100);

  // Author
  ctx.font = '32px Georgia, serif';
  ctx.fillText(data.author_name || 'Unknown Author', 60, 160);
  ctx.font = '20px Georgia, serif';
  ctx.fillText(`Based on ${data.works_used} recent abstracts`, 60, 190);

  // Columns
  const colX = [60, 440, 820];
  const colTitles = ['Top words', 'Top verbs', 'Topics'];
  const lists = [data.top_words, data.top_verbs, data.topics];

  ctx.font = 'bold 24px Georgia, serif';
  for (let i = 0; i < 3; i++) {
    ctx.fillText(colTitles[i], colX[i], 240);
  }

  ctx.font = '20px Georgia, serif';
  const maxItems = 7;
  for (let i = 0; i < 3; i++) {
    const list = lists[i] || [];
    for (let j = 0; j < Math.min(maxItems, list.length); j++) {
      const { term, count } = list[j];
      const y = 280 + j * 28;
      ctx.fillText(`${term} (${count})`, colX[i], y);
    }
  }

  // Footer
  ctx.font = '18px Georgia, serif';
  ctx.fillText('Made with OpenAlex • researchwrapped', 60, H - 40);
}

function updateTweetLink(data) {
  const text = `My Research Wrapped — ${data.author_name} — Top words: ${
    (data.top_words || []).slice(0, 3).map(x => x.term).join(', ')
  }`;
  const url = 'https://researchwrapped';
  const shareUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`;
  tweetLink.href = shareUrl;
}

goButton.addEventListener('click', async () => {
  const identifier = identifierInput.value.trim();
  const backend = backendInput.value.trim();
  if (!identifier || !backend) {
    alert('Please enter both your ORCID/Author ID and the API URL.');
    return;
  }

  goButton.disabled = true;
  goButton.textContent = 'Working…';
  try {
    const params = deriveParamsFromIdentifier(identifier);
    const data = await fetchAnalysis(backend, params);

    authorEl.textContent = data.author_name || 'Author';
    worksEl.textContent = `Based on ${data.works_used} recent abstracts`;
    renderList(wordsEl, data.top_words || []);
    renderList(verbsEl, data.top_verbs || []);
    renderList(topicsEl, data.topics || []);
    resultSection.classList.remove('hidden');

    drawShareCard(data);
    updateTweetLink(data);
  } catch (err) {
    alert(err.message || String(err));
  } finally {
    goButton.disabled = false;
    goButton.textContent = "Let's go";
  }
});

downloadBtn.addEventListener('click', () => {
  const link = document.createElement('a');
  link.download = 'research-wrapped.png';
  link.href = canvas.toDataURL('image/png');
  link.click();
});

