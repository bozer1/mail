/**
 * AI E-posta Asistanı - Frontend JavaScript
 */

const API = 'http://localhost:8000/api';

// Uygulama durumu
const state = {
    emails: [],
    currentEmail: null,
    currentResponseId: null,
    currentFilter: 'all',
    searchQuery: '',
    page: 0,
    limit: 20,
    total: 0,
    stats: {}
};

// Kategori renk haritası
const CAT_COLORS = {
    'İş': '#6366f1', 'Kişisel': '#10b981', 'Finansal': '#f59e0b',
    'Spam': '#ef4444', 'Haber Bülteni': '#0ea5e9', 'Destek/Teknik': '#8b5cf6',
    'Kampanya/Reklam': '#f97316', 'Eğitim': '#06b6d4', 'Sağlık': '#ec4899',
    'Seyahat': '#14b8a6', 'Sosyal Medya': '#a855f7', 'Diğer': '#64748b'
};

const PRIORITY_LABELS = { 1: '↓ Çok Düşük', 2: '↓ Düşük', 3: '⁻ Orta', 4: '↑ Yüksek', 5: '⚠ Acil' };

// =================== BAŞLATMA ===================

document.addEventListener('DOMContentLoaded', async () => {
    await initApp();
});

async function initApp() {
    const overlay = document.getElementById('loading-overlay');
    const progress = document.getElementById('loading-progress');
    const loadingText = document.getElementById('loading-text');

    const steps = [
        { text: 'API bağlantısı kontrol ediliyor...', pct: 30 },
        { text: 'E-postalar yükleniyor...', pct: 60 },
        { text: 'İstatistikler hesaplanıyor...', pct: 85 },
        { text: 'Hazır!', pct: 100 }
    ];

    for (const step of steps) {
        loadingText.textContent = step.text;
        progress.style.width = step.pct + '%';
        await sleep(400);
    }

    await loadEmails();
    await loadStats();

    overlay.classList.add('fade-out');
    setTimeout(() => overlay.style.display = 'none', 500);
}

// =================== E-POSTA YÜKLEMESİ ===================

async function loadEmails() {
    showListLoading(true);

    const params = new URLSearchParams({
        skip: state.page * state.limit,
        limit: state.limit
    });

    if (state.searchQuery) params.append('search', state.searchQuery);

    // Filtre ayarları
    switch (state.currentFilter) {
        case 'unread': params.append('is_read', 'false'); break;
        case 'starred': params.append('is_starred', 'true'); break;
        case 'response': params.append('requires_response', 'true'); break;
        case 'spam':
            params.delete('is_archived');
            // Spam özel sorgu gerektirir
            break;
        case 'archive': params.append('is_archived', 'true'); break;
        default:
            if (state.currentFilter.startsWith('cat:')) {
                params.append('category', state.currentFilter.replace('cat:', ''));
            }
    }

    try {
        let url = `${API}/emails?${params}`;
        if (state.currentFilter === 'spam') {
            url = `${API}/emails?is_spam=true&limit=${state.limit}&skip=${state.page * state.limit}`;
        }

        const res = await fetch(url);
        const data = await res.json();

        state.emails = data.emails || [];
        state.total = data.total || 0;

        renderEmailList();
        updatePagination();
        document.getElementById('email-count').textContent = `${state.total} e-posta`;

    } catch (err) {
        showNotification('E-postalar yüklenemedi: ' + err.message, 'error');
        showEmptyState();
    } finally {
        showListLoading(false);
    }
}

function renderEmailList() {
    const list = document.getElementById('email-list');

    if (state.emails.length === 0) {
        showEmptyState();
        list.innerHTML = '';
        return;
    }

    document.getElementById('empty-state').classList.add('hidden');
    document.getElementById('pagination').classList.remove('hidden');

    list.innerHTML = state.emails.map(email => createEmailCard(email)).join('');
}

function createEmailCard(email) {
    const isUnread = !email.is_read;
    const isSpam = email.is_spam;
    const priority = email.priority || 0;
    const priorityClass = priority >= 5 ? 'urgent-priority' : priority >= 4 ? 'high-priority' : '';
    const starClass = email.is_starred ? 'starred' : '';

    const avatarColor = CAT_COLORS[email.category] || '#6366f1';
    const senderInit = (email.sender_name || email.sender || '?')[0].toUpperCase();
    const displayName = email.sender_name || email.sender.split('@')[0];
    const timeStr = formatTime(email.received_at);

    const catKey = (email.category || 'Diğer').split('/')[0].trim();
    const catClass = `cat-${catKey}`;

    let badges = '';
    if (email.category) {
        badges += `<span class="cat-badge ${catClass}">${email.category}</span>`;
    }
    if (email.priority) {
        const pLabel = PRIORITY_LABELS[email.priority] || `P${email.priority}`;
        badges += `<span class="priority-badge pri-${email.priority}">${pLabel}</span>`;
    }
    if (email.sentiment) {
        badges += `<span class="sentiment-badge sent-${email.sentiment}">${email.sentiment}</span>`;
    }
    if (email.requires_response) {
        badges += `<span class="response-needed"><i class="fas fa-reply"></i>Yanıt Gerekli</span>`;
    }

    const preview = email.summary || email.body.substring(0, 120).replace(/\n/g, ' ');

    return `
    <div class="email-card ${isUnread ? 'unread' : ''} ${isSpam ? 'spam-card' : ''} ${priorityClass}"
         onclick="openEmail(${email.id})"
         data-id="${email.id}">
        <div class="email-avatar" style="background:${avatarColor}">${senderInit}</div>
        <div class="email-card-content">
            <div class="email-card-header">
                <span class="sender-name">${escHtml(displayName)}</span>
                <span class="email-time">${timeStr}</span>
            </div>
            <div class="email-subject">${escHtml(email.subject)}</div>
            <div class="email-preview">${escHtml(preview)}</div>
            ${badges ? `<div class="email-card-footer">${badges}</div>` : ''}
        </div>
        <i class="fas fa-star email-star ${starClass}" onclick="toggleStarCard(event, ${email.id})"></i>
    </div>`;
}

// =================== E-POSTA DETAYI ===================

async function openEmail(id) {
    // Seçili kartı vurgula
    document.querySelectorAll('.email-card').forEach(c => c.classList.remove('selected'));
    document.querySelector(`[data-id="${id}"]`)?.classList.add('selected');

    try {
        const res = await fetch(`${API}/emails/${id}`);
        const email = await res.json();
        state.currentEmail = email;
        state.currentResponseId = null;

        renderEmailDetail(email);
        document.getElementById('email-detail').classList.remove('hidden');

        // Okundu işaretini güncelle
        const card = document.querySelector(`[data-id="${id}"]`);
        if (card) card.classList.remove('unread');

    } catch (err) {
        showNotification('E-posta açılamadı', 'error');
    }
}

function renderEmailDetail(email) {
    const avatarColor = CAT_COLORS[email.category] || '#6366f1';
    const senderInit = (email.sender_name || email.sender || '?')[0].toUpperCase();
    const displayName = email.sender_name || email.sender.split('@')[0];

    document.getElementById('detail-subject').textContent = email.subject;
    document.getElementById('detail-avatar').style.background = avatarColor;
    document.getElementById('detail-avatar').textContent = senderInit;
    document.getElementById('detail-sender-name').textContent = displayName;
    document.getElementById('detail-sender-email').textContent = email.sender;
    document.getElementById('detail-date').textContent = formatFullDate(email.received_at);
    document.getElementById('email-body').textContent = email.body;

    // Yıldız butonu güncelle
    const starBtn = document.getElementById('star-btn');
    starBtn.querySelector('i').style.color = email.is_starred ? '#f59e0b' : '';

    // AI Analiz sonuçları
    renderAIAnalysis(email);

    // Yanıt bölümünü sıfırla
    document.getElementById('response-container').classList.add('hidden');
    document.getElementById('response-text').value = '';
}

function renderAIAnalysis(email) {
    const aiDiv = document.getElementById('ai-analysis');

    if (!email.category && !email.summary) {
        aiDiv.style.display = 'none';
        document.getElementById('classify-btn-container').classList.remove('hidden');
        return;
    }

    aiDiv.style.display = 'block';
    document.getElementById('classify-btn-container').classList.add('hidden');

    // Kategori badge
    const catKey = (email.category || 'Diğer').split('/')[0].trim();
    const catBadge = document.getElementById('badge-category');
    catBadge.textContent = email.category || '';
    catBadge.className = `cat-badge cat-${catKey}`;
    catBadge.style.display = email.category ? '' : 'none';

    // Öncelik badge
    const priBadge = document.getElementById('badge-priority');
    if (email.priority) {
        priBadge.textContent = PRIORITY_LABELS[email.priority] || `P${email.priority}`;
        priBadge.className = `priority-badge pri-${email.priority}`;
        priBadge.style.display = '';
    } else {
        priBadge.style.display = 'none';
    }

    // Duygu badge
    const sentBadge = document.getElementById('badge-sentiment');
    if (email.sentiment) {
        sentBadge.textContent = email.sentiment;
        sentBadge.className = `sentiment-badge sent-${email.sentiment}`;
        sentBadge.style.display = '';
    } else {
        sentBadge.style.display = 'none';
    }

    // Özet
    document.getElementById('ai-summary').textContent = email.summary
        ? `"${email.summary}"`
        : '';

    // Etiketler
    const tagsDiv = document.getElementById('ai-tags');
    if (email.tags && email.tags.length > 0) {
        tagsDiv.innerHTML = email.tags
            .map(t => `<span class="ai-tag">#${t}</span>`)
            .join('');
    } else {
        tagsDiv.innerHTML = '';
    }

    // Aciliyet uyarısı
    const urgencyDiv = document.getElementById('urgency-reason');
    if (email.urgency_reason) {
        urgencyDiv.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${email.urgency_reason}`;
        urgencyDiv.classList.remove('hidden');
    } else {
        urgencyDiv.classList.add('hidden');
    }

    // Güven skoru göster
    if (email.confidence) {
        const pct = Math.round(email.confidence * 100);
        aiDiv.title = `AI Güven Skoru: %${pct}`;
    }
}

function closeDetail() {
    document.getElementById('email-detail').classList.add('hidden');
    document.querySelectorAll('.email-card').forEach(c => c.classList.remove('selected'));
    state.currentEmail = null;
}

// =================== AI OPERASYONLARI ===================

async function classifyCurrentEmail() {
    if (!state.currentEmail) return;

    const btn = document.getElementById('classify-btn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner rotating"></i> Analiz ediliyor...';

    try {
        const res = await fetch(`${API}/emails/${state.currentEmail.id}/classify`, {
            method: 'POST'
        });
        const data = await res.json();

        if (!res.ok) throw new Error(data.detail || 'Analiz hatası');

        state.currentEmail = data.email;
        renderAIAnalysis(data.email);
        updateEmailInList(data.email);
        showNotification('E-posta başarıyla analiz edildi!', 'success');

    } catch (err) {
        showNotification('Analiz hatası: ' + err.message, 'error');
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-magic"></i> AI ile Analiz Et';
        document.getElementById('classify-btn-container').classList.remove('hidden');
    }
}

async function generateResponse() {
    if (!state.currentEmail) return;

    const btn = document.getElementById('generate-btn');
    const tone = document.getElementById('response-tone').value;
    const language = document.getElementById('response-lang').value;
    const context = document.getElementById('extra-context').value;

    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner rotating"></i> Yanıt üretiliyor...';

    try {
        const res = await fetch(`${API}/emails/${state.currentEmail.id}/generate-response`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email_id: state.currentEmail.id,
                tone, language,
                additional_context: context || null
            })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Yanıt üretme hatası');

        state.currentResponseId = data.response.id;
        document.getElementById('response-text').value = data.response.response_text;
        document.getElementById('response-container').classList.remove('hidden');
        showNotification('Yanıt başarıyla üretildi!', 'success');

    } catch (err) {
        showNotification('Yanıt üretme hatası: ' + err.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-wand-magic-sparkles"></i> Yanıt Üret';
    }
}

async function sendResponse() {
    if (!state.currentResponseId) return;

    try {
        const res = await fetch(`${API}/responses/${state.currentResponseId}/send`, {
            method: 'POST'
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Gönderme hatası');
        showNotification('Yanıt başarıyla gönderildi!', 'success');
    } catch (err) {
        showNotification('Gönderme hatası: ' + err.message, 'error');
    }
}

function copyResponse() {
    const text = document.getElementById('response-text').value;
    navigator.clipboard.writeText(text).then(() => {
        showNotification('Yanıt panoya kopyalandı', 'success');
    });
}

async function batchClassify() {
    const unclassified = state.emails
        .filter(e => !e.category)
        .map(e => e.id);

    if (unclassified.length === 0) {
        showNotification('Tüm e-postalar zaten sınıflandırılmış', 'info');
        return;
    }

    showNotification(`${unclassified.length} e-posta sınıflandırılıyor...`, 'info');

    try {
        const res = await fetch(`${API}/emails/batch-classify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email_ids: unclassified })
        });
        const data = await res.json();
        showNotification(`${data.results.length} e-posta sınıflandırıldı!`, 'success');
        await loadEmails();
        await loadStats();
    } catch (err) {
        showNotification('Toplu sınıflandırma hatası: ' + err.message, 'error');
    }
}

// =================== E-POSTA EYLEMLER ===================

async function toggleStar() {
    if (!state.currentEmail) return;
    const newValue = !state.currentEmail.is_starred;
    await updateEmail(state.currentEmail.id, { is_starred: newValue });
    state.currentEmail.is_starred = newValue;
    document.getElementById('star-btn').querySelector('i').style.color = newValue ? '#f59e0b' : '';
    updateEmailInList({ ...state.currentEmail, is_starred: newValue });
}

async function toggleStarCard(event, id) {
    event.stopPropagation();
    const email = state.emails.find(e => e.id === id);
    if (!email) return;
    await updateEmail(id, { is_starred: !email.is_starred });
    email.is_starred = !email.is_starred;
    const starEl = event.currentTarget;
    starEl.classList.toggle('starred', email.is_starred);
}

async function archiveEmail() {
    if (!state.currentEmail) return;
    await updateEmail(state.currentEmail.id, { is_archived: true });
    showNotification('E-posta arşivlendi', 'success');
    closeDetail();
    await loadEmails();
}

async function deleteCurrentEmail() {
    if (!state.currentEmail) return;
    if (!confirm('Bu e-postayı silmek istediğinizden emin misiniz?')) return;

    try {
        const res = await fetch(`${API}/emails/${state.currentEmail.id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error('Silme hatası');
        showNotification('E-posta silindi', 'success');
        closeDetail();
        state.emails = state.emails.filter(e => e.id !== state.currentEmail.id);
        state.total--;
        renderEmailList();
        await loadStats();
    } catch (err) {
        showNotification('Silme hatası: ' + err.message, 'error');
    }
}

async function updateEmail(id, data) {
    try {
        const res = await fetch(`${API}/emails/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return await res.json();
    } catch (err) {
        showNotification('Güncelleme hatası', 'error');
    }
}

// =================== FİLTRELEME ===================

function filterEmails(type, element) {
    // Nav item güncelle
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    if (element) element.classList.add('active');

    state.currentFilter = type;
    state.page = 0;

    const titles = {
        'all': 'Gelen Kutusu',
        'unread': 'Okunmamış E-postalar',
        'starred': 'Yıldızlı E-postalar',
        'response': 'Yanıt Bekleyen',
        'spam': 'Spam Kutusu',
        'archive': 'Arşiv'
    };
    document.getElementById('list-title').textContent = titles[type] || type.replace('cat:', '');

    loadEmails();
}

function showArchive() {
    filterEmails('archive', null);
}

let searchTimeout;
function searchEmails(query) {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        state.searchQuery = query;
        state.page = 0;
        loadEmails();
    }, 400);
}

// =================== DEMO & IMAP ===================

async function loadDemoData() {
    const btn = document.getElementById('demo-btn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner rotating"></i> <span>Yükleniyor...</span>';

    try {
        const res = await fetch(`${API}/demo/load?count=10`, { method: 'POST' });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Yükleme hatası');
        showNotification(data.message, 'success');
        await loadEmails();
        await loadStats();
    } catch (err) {
        showNotification('Demo yükleme hatası: ' + err.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-database"></i> <span>Demo Verileri Yükle</span>';
    }
}

async function fetchFromIMAP() {
    showNotification('IMAP bağlantısı kuruluyor...', 'info');
    try {
        const res = await fetch(`${API}/imap/fetch?limit=20`, { method: 'POST' });
        const data = await res.json();
        showNotification(data.message, data.added > 0 ? 'success' : 'info');
        if (data.added > 0) {
            await loadEmails();
            await loadStats();
        }
    } catch (err) {
        showNotification('IMAP bağlantı hatası: ' + err.message, 'error');
    }
}

// =================== E-POSTA EKLEME FORMU ===================

function showComposeModal() {
    document.getElementById('compose-modal').classList.remove('hidden');
    document.getElementById('compose-sender').focus();
}

async function submitEmail() {
    const sender = document.getElementById('compose-sender').value.trim();
    const senderName = document.getElementById('compose-sender-name').value.trim();
    const subject = document.getElementById('compose-subject').value.trim();
    const body = document.getElementById('compose-body').value.trim();

    if (!sender || !subject || !body) {
        showNotification('Lütfen tüm zorunlu alanları doldurun', 'error');
        return;
    }

    try {
        const res = await fetch(`${API}/emails?auto_classify=true`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sender, sender_name: senderName || null,
                recipient: 'kullanici@mail.com',
                subject, body
            })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Hata');

        closeModal('compose-modal');
        showNotification('E-posta eklendi ve analiz edildi!', 'success');

        // Formu temizle
        ['compose-sender', 'compose-sender-name', 'compose-subject', 'compose-body']
            .forEach(id => document.getElementById(id).value = '');

        await loadEmails();
        await loadStats();
        openEmail(data.id);

    } catch (err) {
        showNotification('E-posta eklenemedi: ' + err.message, 'error');
    }
}

// =================== İSTATİSTİKLER ===================

async function loadStats() {
    try {
        const res = await fetch(`${API}/stats`);
        state.stats = await res.json();
        updateStatBadges();
    } catch (err) {
        console.error('İstatistik yüklenemedi:', err);
    }
}

function updateStatBadges() {
    const s = state.stats;
    document.getElementById('stat-total').textContent = s.total || 0;
    document.getElementById('stat-unread').textContent = s.unread || 0;
    document.getElementById('stat-response').textContent = s.requires_response || 0;

    // Badge'ler
    const badgeAll = document.getElementById('badge-all');
    if (badgeAll) badgeAll.textContent = s.unread > 0 ? s.unread : '';

    const badgeUnread = document.getElementById('badge-unread');
    if (badgeUnread) badgeUnread.textContent = s.unread > 0 ? s.unread : '';

    const badgeResponse = document.getElementById('badge-response');
    if (badgeResponse) badgeResponse.textContent = s.requires_response > 0 ? s.requires_response : '';

    // Kategori listesi
    renderCategoryList(s.by_category || {});
}

function renderCategoryList(categories) {
    const container = document.getElementById('category-list');
    const sorted = Object.entries(categories).sort((a, b) => b[1] - a[1]);

    container.innerHTML = sorted.map(([cat, count]) => {
        const color = CAT_COLORS[cat] || '#64748b';
        return `
        <div class="category-item" onclick="filterByCategory('${cat}')">
            <div style="display:flex;align-items:center;gap:6px">
                <div class="category-dot" style="background:${color}"></div>
                <span>${cat}</span>
            </div>
            <span class="cat-count">${count}</span>
        </div>`;
    }).join('');
}

function filterByCategory(cat) {
    state.currentFilter = `cat:${cat}`;
    state.page = 0;
    document.getElementById('list-title').textContent = cat;
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    loadEmails();
}

async function showStats() {
    await loadStats();
    const s = state.stats;
    const modal = document.getElementById('stats-modal');
    const content = document.getElementById('stats-content');

    const maxCat = Math.max(...Object.values(s.by_category || {}), 1);
    const maxPri = Math.max(...Object.values(s.by_priority || {}), 1);

    const catBars = Object.entries(s.by_category || {})
        .sort((a, b) => b[1] - a[1])
        .map(([cat, cnt]) => {
            const w = Math.round((cnt / maxCat) * 100);
            const color = CAT_COLORS[cat] || '#64748b';
            return `
            <div class="chart-bar">
                <span class="bar-label">${cat}</span>
                <div class="bar-fill" style="width:${w}%;background:${color}"></div>
                <span class="bar-value">${cnt}</span>
            </div>`;
        }).join('');

    const priBars = [5, 4, 3, 2, 1].map(p => {
        const cnt = s.by_priority?.[p] || 0;
        const w = Math.round((cnt / maxPri) * 100);
        const colors = { 5: '#ef4444', 4: '#f59e0b', 3: '#6366f1', 2: '#10b981', 1: '#94a3b8' };
        return `
        <div class="chart-bar">
            <span class="bar-label">${PRIORITY_LABELS[p]}</span>
            <div class="bar-fill" style="width:${w}%;background:${colors[p]}"></div>
            <span class="bar-value">${cnt}</span>
        </div>`;
    }).join('');

    content.innerHTML = `
    <div class="stats-grid">
        <div class="stat-card">
            <div class="number">${s.total || 0}</div>
            <div class="label">Toplam E-posta</div>
        </div>
        <div class="stat-card">
            <div class="number" style="color:#ef4444">${s.unread || 0}</div>
            <div class="label">Okunmamış</div>
        </div>
        <div class="stat-card">
            <div class="number" style="color:#f59e0b">${s.requires_response || 0}</div>
            <div class="label">Yanıt Bekleyen</div>
        </div>
        <div class="stat-card">
            <div class="number" style="color:#10b981">${s.starred || 0}</div>
            <div class="label">Yıldızlı</div>
        </div>
        <div class="stat-card">
            <div class="number" style="color:#ef4444">${s.spam || 0}</div>
            <div class="label">Spam</div>
        </div>
        <div class="stat-card">
            <div class="number" style="color:#6366f1">
                ${Object.keys(s.by_category || {}).length}
            </div>
            <div class="label">Farklı Kategori</div>
        </div>
    </div>
    <div class="chart-section">
        <h4><i class="fas fa-th-large"></i> Kategori Dağılımı</h4>
        ${catBars || '<p style="color:var(--text-dim);font-size:13px">Henüz veri yok</p>'}
    </div>
    <div class="chart-section">
        <h4><i class="fas fa-sort-amount-up"></i> Öncelik Dağılımı</h4>
        ${priBars}
    </div>`;

    modal.classList.remove('hidden');
}

// =================== YARDIMCI FONKSİYONLAR ===================

async function refreshEmails() {
    const icon = document.getElementById('refresh-icon');
    icon.classList.add('rotating');
    await loadEmails();
    await loadStats();
    setTimeout(() => icon.classList.remove('rotating'), 500);
}

function updateEmailInList(updatedEmail) {
    const idx = state.emails.findIndex(e => e.id === updatedEmail.id);
    if (idx !== -1) {
        state.emails[idx] = { ...state.emails[idx], ...updatedEmail };
        const card = document.querySelector(`[data-id="${updatedEmail.id}"]`);
        if (card) {
            card.outerHTML = createEmailCard(state.emails[idx]);
        }
    }
}

function showListLoading(show) {
    document.getElementById('list-loading').classList.toggle('hidden', !show);
}

function showEmptyState() {
    document.getElementById('empty-state').classList.remove('hidden');
    document.getElementById('pagination').classList.add('hidden');
}

function updatePagination() {
    const totalPages = Math.ceil(state.total / state.limit);
    const pag = document.getElementById('pagination');

    if (totalPages <= 1) { pag.classList.add('hidden'); return; }

    pag.classList.remove('hidden');
    document.getElementById('page-info').textContent =
        `Sayfa ${state.page + 1} / ${totalPages}`;
    document.getElementById('prev-btn').disabled = state.page === 0;
    document.getElementById('next-btn').disabled = state.page >= totalPages - 1;
}

function prevPage() {
    if (state.page > 0) { state.page--; loadEmails(); }
}
function nextPage() {
    const totalPages = Math.ceil(state.total / state.limit);
    if (state.page < totalPages - 1) { state.page++; loadEmails(); }
}

function closeModal(id) {
    document.getElementById(id).classList.add('hidden');
}

let notifTimeout;
function showNotification(msg, type = 'info') {
    const el = document.getElementById('notification');
    const icons = { success: '✓', error: '✗', info: 'ℹ' };
    el.textContent = `${icons[type] || ''} ${msg}`;
    el.className = `notification ${type}`;
    el.classList.remove('hidden');
    clearTimeout(notifTimeout);
    notifTimeout = setTimeout(() => el.classList.add('hidden'), 4000);
}

function formatTime(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    const now = new Date();
    const diff = now - d;
    if (diff < 3600000) return `${Math.floor(diff / 60000)} dk önce`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)} sa önce`;
    if (diff < 172800000) return 'Dün';
    return d.toLocaleDateString('tr-TR', { day: '2-digit', month: 'short' });
}

function formatFullDate(dateStr) {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleString('tr-TR', {
        day: '2-digit', month: 'long', year: 'numeric',
        hour: '2-digit', minute: '2-digit'
    });
}

function escHtml(str) {
    const d = document.createElement('div');
    d.appendChild(document.createTextNode(str || ''));
    return d.innerHTML;
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Klavye kısayolları
document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
        if (!document.getElementById('stats-modal').classList.contains('hidden')) closeModal('stats-modal');
        else if (!document.getElementById('compose-modal').classList.contains('hidden')) closeModal('compose-modal');
        else closeDetail();
    }
});
