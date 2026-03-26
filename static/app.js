let currentPath = '';
let currentFilePath = null;
let monacoEditor = null;

// ── Directory listing ────────────────────────────────────────────────────────

async function loadDirectory(path) {
    currentPath = path;

    const res = await fetch(`/api/files/?path=${encodeURIComponent(path)}`);
    if (!res.ok) {
        showStatus(`Failed to load directory: ${res.status}`, true);
        return;
    }

    const entries = await res.json();

    updateBreadcrumb(path);

    const list = document.getElementById('file-list');
    list.innerHTML = '';

    // ".." back navigation
    if (path !== '') {
        const up = document.createElement('div');
        up.className = 'file-item up';
        up.innerHTML = `<span class="item-name">../</span>`;
        up.addEventListener('click', () => loadDirectory(parentPath(path)));
        list.appendChild(up);
    }

    // Sort: folders first, then files
    entries.sort((a, b) => {
        if (a.type === b.type) return a.name.localeCompare(b.name);
        return a.type === 'directory' ? -1 : 1;
    });

    for (const entry of entries) {
        const fullPath = path ? `${path}/${entry.name}` : entry.name;
        const item = document.createElement('div');
        item.className = `file-item ${entry.type === 'directory' ? 'folder' : 'file'}`;

        const label = entry.type === 'directory' ? `${entry.name}/` : entry.name;
        item.innerHTML = `<span class="item-name">${label}</span>`;

        if (entry.type === 'directory') {
            item.addEventListener('click', () => loadDirectory(fullPath));
        } else {
            item.addEventListener('click', () => loadFile(fullPath));
        }

        // Delete button (only shown on hover via CSS)
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'delete-btn';
        deleteBtn.textContent = 'Delete';
        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            deleteEntry(fullPath, entry.name);
        });

        item.appendChild(deleteBtn);
        list.appendChild(item);
    }
}

function parentPath(path) {
    const idx = path.lastIndexOf('/');
    return idx === -1 ? '' : path.substring(0, idx);
}

function updateBreadcrumb(path) {
    const el = document.getElementById('breadcrumb');
    if (!path) {
        el.innerHTML = '<span>/</span>';
        return;
    }
    const parts = path.split('/');
    let built = '';
    let html = '<span style="cursor:pointer" onclick="loadDirectory(\'\')">/ </span>';
    for (const part of parts) {
        built = built ? `${built}/${part}` : part;
        const snap = built;
        html += `<span style="cursor:pointer" onclick="loadDirectory('${snap}')">${part} / </span>`;
    }
    el.innerHTML = html;
}

// ── File read / edit ─────────────────────────────────────────────────────────

async function loadFile(path) {
    const res = await fetch(`/api/files/content?file=${encodeURIComponent(path)}`);
    if (!res.ok) {
        showStatus(`Failed to load file: ${res.status}`, true);
        return;
    }

    const data = await res.json();
    currentFilePath = path;

    document.getElementById('editor-filename').textContent = path;
    document.getElementById('editor-container').style.display = 'block';

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

// ── Save ─────────────────────────────────────────────────────────────────────

document.getElementById('save-btn').addEventListener('click', async () => {
    if (!monacoEditor || !currentFilePath) return;

    const res = await fetch('/api/files/content', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: currentFilePath, content: monacoEditor.getValue() }),
    });

    showStatus(res.ok ? 'Saved.' : `Save failed: ${res.status}`, !res.ok);
});

// ── Close editor ─────────────────────────────────────────────────────────────

document.getElementById('close-btn').addEventListener('click', () => {
    document.getElementById('editor-container').style.display = 'none';
    currentFilePath = null;
});

// ── Delete ───────────────────────────────────────────────────────────────────

async function deleteEntry(path, name) {
    if (!confirm(`Delete "${name}"?`)) return;

    const res = await fetch(`/api/files/?path=${encodeURIComponent(path)}`, {
        method: 'DELETE',
    });

    if (res.ok) {
        loadDirectory(currentPath);
    } else {
        showStatus(`Delete failed: ${res.status}`, true);
    }
}

// ── Status message ────────────────────────────────────────────────────────────

function showStatus(msg, isError = false) {
    let el = document.getElementById('status-msg');
    if (!el) {
        el = document.createElement('div');
        el.id = 'status-msg';
        document.getElementById('editor-container').appendChild(el);
    }
    el.textContent = msg;
    el.className = isError ? 'error' : '';
    setTimeout(() => { el.textContent = ''; }, 3000);
}

// ── Boot ─────────────────────────────────────────────────────────────────────

loadDirectory('');
