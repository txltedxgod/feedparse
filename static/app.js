const $ = id => document.getElementById(id);
let activeFeedId = null;
let activeFilter = 'all';

function stripHtml(html) {
    const doc = new DOMParser().parseFromString(String(html || ''), 'text/html');
    return (doc.body && doc.body.textContent) || '';
}

function safeHref(url) {
    try {
        const parsed = new URL(url, window.location.origin);
        return (parsed.protocol === 'http:' || parsed.protocol === 'https:') ? parsed.href : '#';
    } catch {
        return '#';
    }
}

async function api(url, opts = {}) {
    const res = await fetch(url, {
        headers: {'Content-Type': 'application/json'},
        ...opts
    });
    if (!res.ok) throw new Error(res.statusText);
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

        const label = document.createElement('span');
        label.textContent = f.title || f.url;

        const btn = document.createElement('button');
        btn.className = 'remove';
        btn.innerHTML = '&times;';
        btn.onclick = (e) => {
            e.stopPropagation();
            removeFeed(f.id);
        };

        div.appendChild(label);
        div.appendChild(btn);
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
        const cleanSummary = stripHtml(a.summary).substring(0, 200);

        const h3 = document.createElement('h3');
        if (a.is_starred) {
            const star = document.createElement('span');
            star.className = 'star';
            star.textContent = '★';
            h3.appendChild(star);
            h3.appendChild(document.createTextNode(' '));
        }
        h3.appendChild(document.createTextNode(a.title || 'Untitled'));

        const meta = document.createElement('div');
        meta.className = 'meta';
        meta.textContent = `${a.author || 'unknown'} · ${date}`;

        const preview = document.createElement('div');
        preview.className = 'preview';
        preview.textContent = cleanSummary;

        div.appendChild(h3);
        div.appendChild(meta);
        div.appendChild(preview);
        div.onclick = () => openArticle(a);
        list.appendChild(div);
    });
}

function openArticle(a) {
    const reader = $('reader');
    reader.classList.remove('hidden');

    $('openLink').href = safeHref(a.url);
    $('starBtn').textContent = a.is_starred ? 'unstar' : 'star';
    $('starBtn').onclick = async () => {
        await api(`/api/articles/${a.id}?is_starred=${!a.is_starred}`, {method: 'PATCH'});
        a.is_starred = !a.is_starred;
        $('starBtn').textContent = a.is_starred ? 'unstar' : 'star';
        loadArticles();
    };

    const date = a.published ? new Date(a.published).toLocaleString() : '';
    const container = $('readerContent');
    container.innerHTML = '';

    const h2 = document.createElement('h2');
    h2.textContent = a.title || 'Untitled';
    const meta = document.createElement('div');
    meta.className = 'article-meta';
    meta.textContent = `${a.author || ''} · ${date}`;
    const body = document.createElement('div');
    body.className = 'article-body';
    body.textContent = stripHtml(a.summary);

    container.appendChild(h2);
    container.appendChild(meta);
    container.appendChild(body);

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
