const $ = id => document.getElementById(id);
let activeFeedId = null;
let activeFilter = 'all';

async function api(url, opts = {}) {
    const res = await fetch(url, {
        headers: {'Content-Type': 'application/json'},
        ...opts
    });
    return res.json();
}

async function loadFeeds() {
    const feeds = await api('/api/feeds');
    const list = $('feedList');
    list.innerHTML = '';

    const allItem = document.createElement('div');
    allItem.className = 'feed-item' + (!activeFeedId ? ' active' : '');
    allItem.textContent = 'All feeds';
    allItem.onclick = () => { activeFeedId = null; loadFeeds(); loadArticles(); };
    list.appendChild(allItem);

    feeds.forEach(f => {
        const div = document.createElement('div');
        div.className = 'feed-item' + (activeFeedId === f.id ? ' active' : '');
        div.innerHTML = `
            <span>${f.title || f.url}</span>
            <button class="remove" onclick="event.stopPropagation(); removeFeed(${f.id})">&times;</button>
        `;
        div.onclick = () => { activeFeedId = f.id; loadFeeds(); loadArticles(); };
        list.appendChild(div);
    });
}

async function removeFeed(id) {
    await api(`/api/feeds/${id}`, {method: 'DELETE'});
    if (activeFeedId === id) activeFeedId = null;
    loadFeeds();
    loadArticles();
}

async function loadArticles() {
    let url = '/api/articles?limit=100';
    if (activeFeedId) url += `&feed_id=${activeFeedId}`;
    if (activeFilter === 'unread') url += '&unread=true';
    if (activeFilter === 'starred') url += '&starred=true';

    const articles = await api(url);
    const list = $('articleList');
    list.innerHTML = '';

    if (articles.length === 0) {
        list.innerHTML = '<p style="color:#555;text-align:center;padding:40px">no articles yet</p>';
        return;
    }

    articles.forEach(a => {
        const div = document.createElement('div');
        div.className = 'article-card' + (a.is_read ? ' read' : '');
        const date = a.published ? new Date(a.published).toLocaleDateString() : '';
        const starIcon = a.is_starred ? '<span class="star">★</span> ' : '';
        // strip html tags from summary
        const cleanSummary = a.summary.replace(/<[^>]*>/g, '').substring(0, 200);

        div.innerHTML = `
            <h3>${starIcon}${a.title}</h3>
            <div class="meta">${a.author || 'unknown'} · ${date}</div>
            <div class="preview">${cleanSummary}</div>
        `;
        div.onclick = () => openArticle(a);
        list.appendChild(div);
    });
}

function openArticle(a) {
    const reader = $('reader');
    reader.classList.remove('hidden');

    $('openLink').href = a.url;
    $('starBtn').textContent = a.is_starred ? 'unstar' : 'star';
    $('starBtn').onclick = async () => {
        await api(`/api/articles/${a.id}?is_starred=${!a.is_starred}`, {method: 'PATCH'});
        a.is_starred = !a.is_starred;
        $('starBtn').textContent = a.is_starred ? 'unstar' : 'star';
        loadArticles();
    };

    const date = a.published ? new Date(a.published).toLocaleString() : '';
    $('readerContent').innerHTML = `
        <h2>${a.title}</h2>
        <div class="article-meta">${a.author || ''} · ${date}</div>
        <div class="article-body">${a.summary}</div>
    `;

    // mark as read
    if (!a.is_read) {
        api(`/api/articles/${a.id}?is_read=true`, {method: 'PATCH'});
        a.is_read = true;
    }
}

$('closeReader').onclick = () => {
    $('reader').classList.add('hidden');
    loadArticles();
};

// modal
$('addFeedBtn').onclick = () => $('addModal').classList.remove('hidden');
$('modalCancel').onclick = () => $('addModal').classList.add('hidden');
$('modalAdd').onclick = async () => {
    const url = $('feedUrl').value.trim();
    if (!url) return;
    await api('/api/feeds', {method: 'POST', body: JSON.stringify({url})});
    $('feedUrl').value = '';
    $('addModal').classList.add('hidden');
    loadFeeds();
    loadArticles();
};

// filters
document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.onclick = () => {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        activeFilter = btn.dataset.filter;
        loadArticles();
    };
});

$('refreshBtn').onclick = async () => {
    $('refreshBtn').textContent = 'refreshing...';
    await api('/api/feeds/refresh', {method: 'POST'});
    $('refreshBtn').textContent = 'refresh feeds';
    loadArticles();
};

loadFeeds();
loadArticles();
