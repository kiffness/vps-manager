let currentFilePath = null;
let monacoEditor = null;
const expandedPaths = new Set();
const treeCache = {};

// ── API key ───────────────────────────────────────────────────────────────────

function getApiKey() {
    return localStorage.getItem('vps_api_key') || '';
}

function apiFetch(url, options = {}) {
    return fetch(url, {
        ...options,
        headers: {
            ...options.headers,
            'X-API-Key': getApiKey(),
        },
    });
}

// ── Lock screen ───────────────────────────────────────────────────────────────

function showLockScreen() {
    document.getElementById('lock-screen').style.display = 'flex';
}

function hideLockScreen() {
    document.getElementById('lock-screen').style.display = 'none';
}

document.getElementById('unlock-btn').addEventListener('click', async () => {
    const key = document.getElementById('api-key-input').value.trim();
    if (!key) return;
    const res = await fetch('/api/files/?path=', { headers: { 'X-API-Key': key } });
    if (res.status !== 403) {
        localStorage.setItem('vps_api_key', key);
        document.getElementById('lock-error').style.display = 'none';
        hideLockScreen();
        refreshTree();
    } else {
        document.getElementById('lock-error').style.display = 'block';
    }
});

document.getElementById('api-key-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') document.getElementById('unlock-btn').click();
});

document.getElementById('lock-btn').addEventListener('click', () => {
    localStorage.removeItem('vps_api_key');
    document.getElementById('api-key-input').value = '';
    document.getElementById('lock-error').style.display = 'none';
    showLockScreen();
});

// ── Tabs ──────────────────────────────────────────────────────────────────────

document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const tab = btn.dataset.tab;
        document.querySelectorAll('.tab-section').forEach(s => s.style.display = 'none');
        document.getElementById(`tab-${tab}`).style.display = 'flex';
        if (tab === 'docker') loadDockerDashboard();
        if (tab === 'server') startResourceStream();
        else stopResourceStream();
    });
});

// ── File tree ─────────────────────────────────────────────────────────────────

async function fetchDirectory(path) {
    if (treeCache[path]) return treeCache[path];
    const res = await apiFetch(`/api/files/?path=${encodeURIComponent(path)}`);
    if (!res.ok) return [];
    const entries = await res.json();
    entries.sort((a, b) => {
        if (a.type === b.type) return a.name.localeCompare(b.name);
        return a.type === 'directory' ? -1 : 1;
    });
    treeCache[path] = entries;
    return entries;
}

async function renderTree(containerEl, path, indent) {
    const entries = await fetchDirectory(path);

    for (const entry of entries) {
        const fullPath = path ? `${path}/${entry.name}` : entry.name;

        const item = document.createElement('div');
        item.className = 'tree-item';
        item.style.paddingLeft = `${indent * 12 + 6}px`;
        item.dataset.path = fullPath;

        if (entry.type === 'directory') {
            const isExpanded = expandedPaths.has(fullPath);
            item.innerHTML = `
                <span class="tree-arrow codicon ${isExpanded ? 'codicon-chevron-down' : 'codicon-chevron-right'}"></span>
                <span class="tree-icon ${isExpanded ? 'folder-open' : 'folder'} codicon ${isExpanded ? 'codicon-folder-opened' : 'codicon-folder'}"></span>
                <span class="tree-label">${entry.name}</span>
                <button class="tree-delete-btn" title="Delete">×</button>
            `;

            const childContainer = document.createElement('div');
            childContainer.className = 'tree-children';
            if (!isExpanded) childContainer.style.display = 'none';

            item.addEventListener('click', async (e) => {
                if (e.target.classList.contains('tree-delete-btn')) return;
                if (expandedPaths.has(fullPath)) {
                    expandedPaths.delete(fullPath);
                    item.querySelector('.tree-arrow').className = 'tree-arrow codicon codicon-chevron-right';
                    item.querySelector('.tree-icon').className = 'tree-icon folder codicon codicon-folder';
                    childContainer.style.display = 'none';
                } else {
                    expandedPaths.add(fullPath);
                    item.querySelector('.tree-arrow').className = 'tree-arrow codicon codicon-chevron-down';
                    item.querySelector('.tree-icon').className = 'tree-icon folder-open codicon codicon-folder-opened';
                    childContainer.innerHTML = '';
                    await renderTree(childContainer, fullPath, indent + 1);
                    childContainer.style.display = 'block';
                }
            });

            item.querySelector('.tree-delete-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                deleteEntry(fullPath, entry.name);
            });

            containerEl.appendChild(item);
            containerEl.appendChild(childContainer);

            if (isExpanded) {
                await renderTree(childContainer, fullPath, indent + 1);
            }

        } else {
            const iconClass = getFileIconClass(entry.name);
            item.innerHTML = `
                <span class="tree-arrow"></span>
                <span class="tree-icon ${iconClass.color} codicon ${iconClass.icon}"></span>
                <span class="tree-label">${entry.name}</span>
                <button class="tree-delete-btn" title="Delete">×</button>
            `;

            item.addEventListener('click', (e) => {
                if (e.target.classList.contains('tree-delete-btn')) return;
                document.querySelectorAll('.tree-item.active').forEach(el => el.classList.remove('active'));
                item.classList.add('active');
                loadFile(fullPath);
            });

            item.querySelector('.tree-delete-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                deleteEntry(fullPath, entry.name);
            });

            containerEl.appendChild(item);
        }
    }
}

function getFileIconClass(name) {
    const ext = name.split('.').pop().toLowerCase();
    const map = {
        py:   { icon: 'codicon-file-code',    color: 'file-py' },
        js:   { icon: 'codicon-file-code',    color: 'file-js' },
        ts:   { icon: 'codicon-file-code',    color: 'file-ts' },
        html: { icon: 'codicon-file-code',    color: 'file-html' },
        css:  { icon: 'codicon-file-code',    color: 'file-css' },
        json: { icon: 'codicon-json',         color: 'file-json' },
        md:   { icon: 'codicon-markdown',     color: 'file-md' },
        yml:  { icon: 'codicon-file-code',    color: 'file-yml' },
        yaml: { icon: 'codicon-file-code',    color: 'file-yml' },
        sh:   { icon: 'codicon-terminal',     color: 'file-sh' },
        txt:  { icon: 'codicon-file-text',    color: 'file-default' },
    };
    return map[ext] || { icon: 'codicon-file', color: 'file-default' };
}

async function refreshTree() {
    Object.keys(treeCache).forEach(k => delete treeCache[k]);
    const tree = document.getElementById('file-tree');
    tree.innerHTML = '';
    await renderTree(tree, '', 0);
}

// ── File read / edit ──────────────────────────────────────────────────────────

async function loadFile(path) {
    const res = await apiFetch(`/api/files/content?file=${encodeURIComponent(path)}`);
    if (!res.ok) {
        showStatus(`Failed to load file: ${res.status}`, true);
        return;
    }

    const data = await res.json();
    currentFilePath = path;

    const filename = path.split('/').pop();
    document.getElementById('editor-filename').textContent = filename;

    const iconClass = getFileIconClass(filename);
    const iconEl = document.getElementById('editor-file-icon');
    iconEl.className = `codicon ${iconClass.icon} ${iconClass.color}`;

    document.getElementById('editor-empty').style.display = 'none';
    document.getElementById('editor-container').style.display = 'flex';

    const language = detectLanguage(path);

    if (monacoEditor) {
        monacoEditor.setValue(data.content);
        monaco.editor.setModelLanguage(monacoEditor.getModel(), language);
    } else {
        require.config({ paths: { vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/vs' } });
        require(['vs/editor/editor.main'], function () {
            monacoEditor = monaco.editor.create(document.getElementById('editor'), {
                value: data.content,
                language: language,
                theme: 'vs-dark',
                automaticLayout: true,
                fontSize: 13,
                minimap: { enabled: true },
                scrollBeyondLastLine: false,
            });
        });
    }
}

function detectLanguage(path) {
    const ext = path.split('.').pop().toLowerCase();
    const map = {
        js: 'javascript', ts: 'typescript', py: 'python',
        html: 'html', css: 'css', json: 'json',
        md: 'markdown', sh: 'shell', yml: 'yaml', yaml: 'yaml',
        toml: 'ini', txt: 'plaintext',
    };
    return map[ext] || 'plaintext';
}

// ── Save ──────────────────────────────────────────────────────────────────────

document.getElementById('save-btn').addEventListener('click', async () => {
    if (!monacoEditor || !currentFilePath) return;

    const res = await apiFetch('/api/files/content', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: currentFilePath, content: monacoEditor.getValue() }),
    });

    showStatus(res.ok ? 'Saved.' : `Save failed: ${res.status}`, !res.ok);
});

// ── Close editor ──────────────────────────────────────────────────────────────

document.getElementById('close-btn').addEventListener('click', () => {
    document.getElementById('editor-container').style.display = 'none';
    document.getElementById('editor-empty').style.display = 'flex';
    document.querySelectorAll('.tree-item.active').forEach(el => el.classList.remove('active'));
    currentFilePath = null;
});

// ── Delete ────────────────────────────────────────────────────────────────────

async function deleteEntry(path, name) {
    if (!confirm(`Delete "${name}"?`)) return;

    const res = await apiFetch(`/api/files/?path=${encodeURIComponent(path)}`, {
        method: 'DELETE',
    });

    if (res.ok) {
        if (currentFilePath === path) {
            document.getElementById('editor-container').style.display = 'none';
            document.getElementById('editor-empty').style.display = 'flex';
            currentFilePath = null;
        }
        refreshTree();
    } else {
        showStatus(`Delete failed: ${res.status}`, true);
    }
}

// ── Status message ────────────────────────────────────────────────────────────

function showStatus(msg, isError = false) {
    const el = document.getElementById('status-msg');
    el.textContent = msg;
    el.className = isError ? 'error' : '';
    setTimeout(() => { el.textContent = ''; }, 3000);
}

// ── Docker dashboard ──────────────────────────────────────────────────────────

function loadDockerDashboard() {
    loadContainers();
    loadNetworks();
    loadImages();
}

document.getElementById('refresh-docker-btn').addEventListener('click', loadDockerDashboard);

// Containers

async function loadContainers() {
    const res = await apiFetch('/docker/containers');
    if (!res.ok) return;
    const containers = await res.json();

    const list = document.getElementById('container-list');
    list.innerHTML = '';

    for (const c of containers) {
        const card = document.createElement('div');
        card.className = 'container-card';

        const isRunning = c.status === 'running';
        const badgeClass = isRunning ? 'running' : 'stopped';

        const row = document.createElement('div');
        row.className = 'card-row';
        row.innerHTML = `
            <span class="card-name">${c.name}</span>
            <span class="card-meta">${c.image}</span>
            <span class="status-badge ${badgeClass}">${c.status}</span>
        `;

        const logsPanel = document.createElement('div');
        logsPanel.className = 'logs-panel';

        const logsBtn = makeActionBtn('Logs', 'logs', () => toggleLogs(c.id, logsPanel, logsBtn));

        row.appendChild(makeActionBtn('Start', 'start', () => containerAction(c.id, 'start')));
        row.appendChild(makeActionBtn('Stop', 'stop', () => containerAction(c.id, 'stop')));
        row.appendChild(makeActionBtn('Restart', 'restart', () => containerAction(c.id, 'restart')));
        row.appendChild(logsBtn);

        card.appendChild(row);
        card.appendChild(logsPanel);
        list.appendChild(card);
    }
}

function makeActionBtn(label, cls, onClick) {
    const btn = document.createElement('button');
    btn.className = `action-btn ${cls}`;
    btn.textContent = label;
    btn.addEventListener('click', onClick);
    return btn;
}

async function containerAction(id, action) {
    const res = await apiFetch('/docker/containers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, action }),
    });
    if (res.ok) loadContainers();
}

async function toggleLogs(id, panel, btn) {
    if (panel.style.display === 'block') {
        panel.style.display = 'none';
        btn.textContent = 'Logs';
        return;
    }
    const res = await apiFetch(`/docker/containers/${id}`);
    if (!res.ok) return;
    const data = await res.json();
    panel.textContent = data.logs.join('\n');
    panel.style.display = 'block';
    panel.scrollTop = panel.scrollHeight;
    btn.textContent = 'Hide Logs';
}

// Networks

async function loadNetworks() {
    const res = await apiFetch('/docker/networks');
    if (!res.ok) return;
    const networks = await res.json();

    const list = document.getElementById('network-list');
    list.innerHTML = '';

    for (const n of networks) {
        const card = document.createElement('div');
        card.className = 'network-card card-row';
        card.innerHTML = `
            <span class="card-name">${n.name}</span>
            <span class="card-meta">${n.driver}</span>
            <span class="card-meta">${n.containers.length ? n.containers.join(', ') : 'no containers'}</span>
        `;
        list.appendChild(card);
    }
}

// Images

let allImages = [];
let imageInUse = new Set();
let imageFilter = 'all';

document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        imageFilter = btn.dataset.filter;
        renderImages();
    });
});

document.getElementById('delete-unused-btn').addEventListener('click', async () => {
    const unused = allImages.filter(img => !imageInUse.has(img.id));
    if (!unused.length) return;
    if (!confirm(`Delete ${unused.length} unused image(s)?`)) return;
    for (const img of unused) {
        await apiFetch(`/docker/images/${encodeURIComponent(img.id)}`, { method: 'DELETE' });
    }
    loadImages();
});

async function loadImages() {
    const [imgRes, conRes] = await Promise.all([
        apiFetch('/docker/images'),
        apiFetch('/docker/containers'),
    ]);
    if (!imgRes.ok) return;

    allImages = await imgRes.json();
    const containers = conRes.ok ? await conRes.json() : [];
    imageInUse = new Set(containers.map(c => c.image_id));

    renderImages();
}

function renderImages() {
    const list = document.getElementById('image-list');
    list.innerHTML = '';

    const filtered = allImages.filter(img => {
        if (imageFilter === 'used') return imageInUse.has(img.id);
        if (imageFilter === 'unused') return !imageInUse.has(img.id);
        return true;
    });

    for (const img of filtered) {
        const card = document.createElement('div');
        card.className = 'image-card card-row';
        const tags = img.tags.length ? img.tags.join(', ') : 'untagged';
        const size = (img.size / 1024 / 1024).toFixed(1) + ' MB';
        const used = imageInUse.has(img.id);
        const usedBadge = used
            ? '<span class="status-badge running">in use</span>'
            : '<span class="status-badge stopped">unused</span>';
        card.innerHTML = `
            <span class="card-name">${tags}</span>
            <span class="card-meta">${size}</span>
            ${usedBadge}
        `;

        if (!used) {
            const delBtn = makeActionBtn('Delete', 'stop', async () => {
                if (!confirm(`Delete image ${tags}?`)) return;
                const res = await apiFetch(`/docker/images/${encodeURIComponent(img.id)}`, { method: 'DELETE' });
                if (res.ok) loadImages();
            });
            card.appendChild(delBtn);
        }

        list.appendChild(card);
    }
}

// ── Server resources ──────────────────────────────────────────────────────────

let resourceEventSource = null;

function startResourceStream() {
    if (resourceEventSource) return;
    const key = getApiKey();
    resourceEventSource = new EventSource(`/server-resources/stream?api_key=${encodeURIComponent(key)}`);
    resourceEventSource.onmessage = (e) => {
        const d = JSON.parse(e.data);
        document.getElementById('cpu-value').textContent = `${d.cpu_percentage.toFixed(1)}%`;
        document.getElementById('cpu-bar').style.width = `${d.cpu_percentage}%`;
        document.getElementById('mem-value').textContent = `${d.memory_usage.toFixed(1)}%`;
        document.getElementById('mem-bar').style.width = `${d.memory_usage}%`;
        document.getElementById('disk-value').textContent = `${d.disk_used_gb} / ${d.disk_total_gb} GB (${d.disk_percent.toFixed(1)}%)`;
        document.getElementById('disk-bar').style.width = `${d.disk_percent}%`;
    };
}

function stopResourceStream() {
    if (resourceEventSource) {
        resourceEventSource.close();
        resourceEventSource = null;
    }
}

// ── Boot ──────────────────────────────────────────────────────────────────────

if (getApiKey()) {
    hideLockScreen();
    refreshTree();
} else {
    showLockScreen();
}
