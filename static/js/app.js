document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

let currentSearchMode = 'auto';

function initApp() {
    setupModeSelector();
    setupSearchForm();
    setupChatSystem();
    setupModalHandlers();
    loadPersonalizedRecommendations();
}

function setupModeSelector() {
    const modeBtns = document.querySelectorAll('.mode-btn');
    const searchInput = document.getElementById('searchInput');
    if (!modeBtns || !searchInput) return;

    modeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            modeBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentSearchMode = btn.getAttribute('data-mode') || 'auto';
            if (currentSearchMode === 'similar') {
                searchInput.placeholder = "Enter creator handle (e.g. 'taylorswift' or 'cristiano')...";
            } else {
                searchInput.placeholder = "Search topics, niches, or influencers (e.g. 'cristiano', 'fitness', 'tech')...";
            }
        });
    });
}

function setupSearchForm() {
    const searchForm = document.getElementById('searchForm');
    const searchInput = document.getElementById('searchInput');
    const searchSubmitBtn = document.getElementById('searchSubmitBtn');
    const categorySelect = document.getElementById('categoryFilter');
    const tierSelect = document.getElementById('tierFilter');
    const engagementSelect = document.getElementById('engagementFilter');

    if (!searchForm || !searchInput) return;

    const performSearchAction = async () => {
        const query = searchInput.value.trim();
        const cat = categorySelect ? categorySelect.value || null : null;
        const tier = tierSelect ? tierSelect.value || null : null;
        const eng = engagementSelect && engagementSelect.value ? parseFloat(engagementSelect.value) : null;

        if (!query && !cat && !tier && !eng) return;

        const payload = {
            query: query,
            mode: currentSearchMode,
            category: cat,
            follower_tier: tier,
            min_engagement: eng,
            top_k: 8
        };

        await executeSearch(payload);
    };

    searchForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        await performSearchAction();
    });

    if (searchSubmitBtn) {
        searchSubmitBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            await performSearchAction();
        });
    }

    searchInput.addEventListener('keydown', async (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            await performSearchAction();
        }
    });

    if (categorySelect) {
        categorySelect.addEventListener('change', () => performSearchAction());
    }
    if (tierSelect) {
        tierSelect.addEventListener('change', () => performSearchAction());
    }
    if (engagementSelect) {
        engagementSelect.addEventListener('change', () => performSearchAction());
    }
}

async function executeSearch(payload) {
    const resultsContainer = document.getElementById('searchResultsList');
    const statusText = document.getElementById('searchStatusText');
    if (!resultsContainer) return;

    resultsContainer.innerHTML = `
        <div class="empty-state">
            <div class="stat-icon" style="margin: 0 auto 0.75rem;"><i data-lucide="loader"></i></div>
            <div class="empty-state-title">Searching Creator Catalog...</div>
            <div class="empty-state-desc">Finding optimal matches for your campaign criteria</div>
        </div>
    `;
    if (window.lucide) lucide.createIcons();

    try {
        const res = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (statusText) {
            statusText.innerText = `${data.count || 0} creators found`;
        }

        renderSearchResults(data.results || [], payload.query);
        loadPersonalizedRecommendations();
    } catch (err) {
        resultsContainer.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-title" style="color: var(--danger);">Search Error</div>
                <div class="empty-state-desc">Unable to retrieve creator results. Please try again.</div>
            </div>
        `;
    }
}

function renderSearchResults(creators, query) {
    const container = document.getElementById('searchResultsList');
    if (!container) return;

    if (!creators || creators.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-title">No Creators Found</div>
                <div class="empty-state-desc">No creators matched your query. Try broadening your criteria or search topic.</div>
            </div>
        `;
        return;
    }

    container.innerHTML = creators.map(c => `
        <div class="result-card">
            <div class="result-left">
                <div class="creator-avatar">${(c.full_name || c.username || 'C').charAt(0).toUpperCase()}</div>
                <div class="creator-info">
                    <div style="display: flex; align-items: center; gap: 0.4rem;">
                        <span class="creator-name">${escapeHtml(c.full_name || c.username)}</span>
                        <span class="creator-handle">@${escapeHtml(c.username)}</span>
                    </div>
                    <div class="result-meta-row">
                        <span class="badge-category">${escapeHtml(c.category || 'General')}</span>
                        <span class="result-pill"><i data-lucide="users" style="width: 14px; height: 14px;"></i><strong>${escapeHtml(c.followers_formatted)}</strong> followers</span>
                        <span class="result-pill"><i data-lucide="activity" style="width: 14px; height: 14px;"></i><strong style="color: var(--success);">${escapeHtml(c.engagement_formatted)}</strong> engagement</span>
                        <span class="result-pill">${escapeHtml(c.follower_tier || '')}</span>
                    </div>
                </div>
            </div>
            <div class="result-actions">
                <button class="btn btn-secondary btn-sm" onclick="showCreatorModal('${escapeHtml(c.username)}')">
                    <span>View Profile</span>
                </button>
                <button class="btn btn-primary btn-sm" onclick="searchSimilarCreator('${escapeHtml(c.username)}')">
                    <span>Find Similar</span>
                </button>
            </div>
        </div>
    `).join('');

    if (window.lucide) lucide.createIcons();
}

async function loadPersonalizedRecommendations() {
    const grid = document.getElementById('recommendationsGrid');
    const summaryBadge = document.getElementById('userSummaryBadge');
    if (!grid) return;

    try {
        const res = await fetch('/api/recommendations');
        const data = await res.json();
        const recs = data.recommendations || [];

        if (summaryBadge && data.user_summary) {
            summaryBadge.innerText = data.user_summary;
            if (summaryBadge.parentElement && summaryBadge.parentElement.parentElement) {
                summaryBadge.parentElement.parentElement.style.display = 'inline-flex';
            }
        }

        if (recs.length === 0) {
            grid.innerHTML = '<div style="grid-column: 1 / -1; font-size: 0.85rem; color: var(--text-muted); text-align: center; padding: 1rem;">No recommendations generated yet. Start a search or ask the AI assistant!</div>';
            return;
        }

        grid.innerHTML = recs.slice(0, 5).map(c => `
            <div class="rec-card" onclick="showCreatorModal('${escapeHtml(c.username)}')">
                <div>
                    <div class="rec-card-header">
                        <div class="creator-avatar">${(c.full_name || c.username || 'C').charAt(0).toUpperCase()}</div>
                        <div class="creator-info">
                            <div class="creator-name" title="${escapeHtml(c.full_name || c.username)}">${escapeHtml(c.full_name || c.username)}</div>
                            <div class="creator-handle">@${escapeHtml(c.username)}</div>
                        </div>
                    </div>
                    <div class="badge-category">${escapeHtml(c.category || 'General')}</div>
                    <div class="rec-metrics">
                        <div class="rec-metric-item">
                            <span class="metric-label">Followers</span>
                            <span class="metric-value">${escapeHtml(c.followers_formatted)}</span>
                        </div>
                        <div class="rec-metric-item">
                            <span class="metric-label">Engagement</span>
                            <span class="metric-value eng">${escapeHtml(c.engagement_formatted)}</span>
                        </div>
                    </div>
                </div>
                <div class="rec-reason" title="${escapeHtml(c.match_reason || '')}">
                    ${escapeHtml(c.match_reason || 'Personalized for you')}
                </div>
            </div>
        `).join('');

        if (window.lucide) lucide.createIcons();
    } catch (e) {
    }
}

function setupChatSystem() {
    const chatForm = document.getElementById('chatForm');
    const chatInput = document.getElementById('chatInput');
    const chatSendBtn = document.getElementById('chatSendBtn');
    const chatMessages = document.getElementById('chatMessages');
    const suggestionPills = document.querySelectorAll('.suggestion-pill');

    if (!chatForm || !chatInput || !chatMessages) return;

    loadChatHistory();

    const sendChatMessage = async () => {
        const msg = chatInput.value.trim();
        if (!msg) return;

        appendUserMessage(msg);
        chatInput.value = '';

        const loaderId = appendLoadingIndicator();

        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: msg })
            });
            const data = await res.json();
            removeMessageElement(loaderId);

            appendAiMessage(data.reply || '', data.recommendations || []);

            if (data.summary) {
                const summaryEl = document.getElementById('chatSummaryDisplay');
                if (summaryEl) {
                    summaryEl.innerText = data.summary;
                    summaryEl.parentElement.style.display = 'flex';
                }
            }

            if (data.updated_user_recommendations && data.updated_user_recommendations.length > 0) {
                renderRecommendationsDirect(data.updated_user_recommendations);
            } else {
                loadPersonalizedRecommendations();
            }
        } catch (err) {
            removeMessageElement(loaderId);
            appendAiMessage("I encountered an issue processing your request. Please try asking again.", []);
        }
    };

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        await sendChatMessage();
    });

    if (chatSendBtn) {
        chatSendBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            await sendChatMessage();
        });
    }

    chatInput.addEventListener('keydown', async (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            await sendChatMessage();
        }
    });

    suggestionPills.forEach(pill => {
        pill.addEventListener('click', async () => {
            const text = pill.innerText.replace(/^[✨🔍🎯💡]\s*/, '').trim();
            chatInput.value = text;
            await sendChatMessage();
        });
    });
}

function renderRecommendationsDirect(recs) {
    const grid = document.getElementById('recommendationsGrid');
    if (!grid || !recs) return;

    grid.innerHTML = recs.slice(0, 5).map(c => `
        <div class="rec-card" onclick="showCreatorModal('${escapeHtml(c.username)}')">
            <div>
                <div class="rec-card-header">
                    <div class="creator-avatar">${(c.full_name || c.username || 'C').charAt(0).toUpperCase()}</div>
                    <div class="creator-info">
                        <div class="creator-name" title="${escapeHtml(c.full_name || c.username)}">${escapeHtml(c.full_name || c.username)}</div>
                        <div class="creator-handle">@${escapeHtml(c.username)}</div>
                    </div>
                </div>
                <div class="badge-category">${escapeHtml(c.category || 'General')}</div>
                <div class="rec-metrics">
                    <div class="rec-metric-item">
                        <span class="metric-label">Followers</span>
                        <span class="metric-value">${escapeHtml(c.followers_formatted)}</span>
                    </div>
                    <div class="rec-metric-item">
                        <span class="metric-label">Engagement</span>
                        <span class="metric-value eng">${escapeHtml(c.engagement_formatted)}</span>
                    </div>
                </div>
            </div>
            <div class="rec-reason" title="${escapeHtml(c.match_reason || '')}">
                ${escapeHtml(c.match_reason || 'Personalized for you')}
            </div>
        </div>
    `).join('');

    if (window.lucide) lucide.createIcons();
}

async function loadChatHistory() {
    try {
        const res = await fetch('/api/chat/history');
        const data = await res.json();
        const history = data.history || [];
        const container = document.getElementById('chatMessages');
        if (!container) return;

        if (history.length === 0) {
            container.innerHTML = `
                <div class="message-row ai-msg">
                    <div class="msg-avatar"><i data-lucide="sparkles" style="width: 16px; height: 16px;"></i></div>
                    <div class="msg-bubble">
                        Hello! I am your AI Creator Intelligence Advisor. Ask me for creator suggestions, campaign strategies, or lookalike recommendations.
                    </div>
                </div>
            `;
            if (window.lucide) lucide.createIcons();
            return;
        }

        container.innerHTML = '';
        history.forEach(m => {
            if (m.role === 'user') {
                appendUserMessage(m.content);
            } else {
                appendAiMessage(m.content, []);
            }
        });
    } catch (e) {
    }
}

function appendUserMessage(text) {
    const container = document.getElementById('chatMessages');
    if (!container) return;

    const row = document.createElement('div');
    row.className = 'message-row user-msg';
    row.innerHTML = `
        <div class="msg-avatar"><i data-lucide="user" style="width: 14px; height: 14px;"></i></div>
        <div class="msg-bubble">${escapeHtml(text)}</div>
    `;
    container.appendChild(row);
    if (window.lucide) lucide.createIcons();
    container.scrollTop = container.scrollHeight;
}

function appendAiMessage(text, recommendations) {
    const container = document.getElementById('chatMessages');
    if (!container) return;

    const safeText = String(text || '').replace(/\n/g, '<br>');
    const recsHtml = recommendations && recommendations.length > 0 ? `
        <div class="chat-rec-chips">
            ${recommendations.map(r => `
                <span class="chat-rec-chip" onclick="searchSimilarCreator('${escapeHtml(r.username)}')">
                    <i data-lucide="user-check" style="width: 12px; height: 12px;"></i>
                    @${escapeHtml(r.username)} (${escapeHtml(r.category || 'Creator')})
                </span>
            `).join('')}
        </div>
    ` : '';

    const row = document.createElement('div');
    row.className = 'message-row ai-msg';
    row.innerHTML = `
        <div class="msg-avatar"><i data-lucide="sparkles" style="width: 16px; height: 16px;"></i></div>
        <div class="msg-bubble">
            <div>${safeText}</div>
            ${recsHtml}
        </div>
    `;
    container.appendChild(row);
    if (window.lucide) lucide.createIcons();
    container.scrollTop = container.scrollHeight;
}

function appendLoadingIndicator() {
    const container = document.getElementById('chatMessages');
    if (!container) return '';

    const id = 'loader_' + Date.now();
    const row = document.createElement('div');
    row.id = id;
    row.className = 'message-row ai-msg';
    row.innerHTML = `
        <div class="msg-avatar"><i data-lucide="sparkles" style="width: 16px; height: 16px;"></i></div>
        <div class="msg-bubble" style="color: var(--text-muted); font-style: italic;">
            Analyzing creator catalog and strategy...
        </div>
    `;
    container.appendChild(row);
    if (window.lucide) lucide.createIcons();
    container.scrollTop = container.scrollHeight;
    return id;
}

function removeMessageElement(id) {
    if (!id) return;
    const el = document.getElementById(id);
    if (el) el.remove();
}

function setupModalHandlers() {
    const modal = document.getElementById('creatorModal');
    const closeBtn = document.getElementById('closeModalBtn');
    if (!modal) return;

    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            modal.style.display = 'none';
        });
    }

    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });
}

async function showCreatorModal(username) {
    const modal = document.getElementById('creatorModal');
    const body = document.getElementById('modalBody');
    if (!modal || !body) return;

    modal.style.display = 'flex';
    body.innerHTML = `
        <div style="text-align: center; padding: 2rem;">
            <div>Loading creator details for @${escapeHtml(username)}...</div>
        </div>
    `;

    try {
        const res = await fetch(`/api/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: username, mode: 'similar', top_k: 4 })
        });
        const data = await res.json();
        const lookalikes = data.results || [];

        body.innerHTML = `
            <div style="display: flex; align-items: center; gap: 1rem; padding-bottom: 1rem; border-bottom: 1px solid var(--border-color);">
                <div class="creator-avatar" style="width: 56px; height: 56px; font-size: 1.4rem;">
                    ${username.charAt(0).toUpperCase()}
                </div>
                <div>
                    <h3 style="font-size: 1.15rem; font-weight: 700;">@${escapeHtml(username)}</h3>
                    <div style="font-size: 0.85rem; color: var(--text-muted);">Influencer Profile</div>
                </div>
            </div>

            <div>
                <h4 style="font-size: 0.88rem; font-weight: 700; margin-bottom: 0.5rem;">Algorithmic Lookalikes in Same Niche</h4>
                <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                    ${lookalikes.length > 0 ? lookalikes.map(l => `
                        <div style="display: flex; align-items: center; justify-content: space-between; padding: 0.65rem 0.85rem; border: 1px solid var(--border-color); border-radius: var(--radius-sm); background-color: var(--bg-subtle);">
                            <div>
                                <strong style="font-size: 0.85rem;">@${escapeHtml(l.username)}</strong>
                                <span style="font-size: 0.75rem; color: var(--text-muted); margin-left: 0.5rem;">${escapeHtml(l.category)}</span>
                            </div>
                            <div style="display: flex; align-items: center; gap: 0.75rem; font-size: 0.78rem;">
                                <span>${escapeHtml(l.followers_formatted)} followers</span>
                                <span style="color: var(--success); font-weight: 600;">${escapeHtml(l.engagement_formatted)}</span>
                            </div>
                        </div>
                    `).join('') : '<div style="font-size: 0.82rem; color: var(--text-muted);">No lookalikes found.</div>'}
                </div>
            </div>
        `;
    } catch (e) {
        body.innerHTML = `<div style="color: var(--danger); padding: 1rem;">Unable to load profile data.</div>`;
    }
}

function searchSimilarCreator(username) {
    const searchInput = document.getElementById('searchInput');
    const searchForm = document.getElementById('searchForm');
    const modal = document.getElementById('creatorModal');
    if (modal) modal.style.display = 'none';

    if (searchInput) {
        const modeBtns = document.querySelectorAll('.mode-btn');
        modeBtns.forEach(b => {
            if (b.getAttribute('data-mode') === 'similar') {
                b.click();
            }
        });
        searchInput.value = username;
        executeSearch({
            query: username,
            mode: 'similar',
            top_k: 8
        });
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}
