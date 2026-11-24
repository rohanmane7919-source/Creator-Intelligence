function safeCreateIcons() {
    try {
        if (window.lucide && typeof window.lucide.createIcons === 'function') {
            window.lucide.createIcons();
        }
    } catch (e) {
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}

let currentSearchMode = 'auto';

function initApp() {
    setupModeSelector();
    setupSearchForm();
    setupChatSystem();
    setupModalHandlers();
    loadPersonalizedRecommendations();
    safeCreateIcons();
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

    if (!searchInput) return;

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

    if (searchForm) {
        searchForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await performSearchAction();
        });
    }

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
            <div class="stat-icon" style="margin: 0 auto 0.75rem;"><i data-lucide="loader-2"></i></div>
            <div class="empty-state-title">Searching Creator Catalog...</div>
            <div class="empty-state-desc">Finding optimal matches for "${escapeHtml(payload.query || payload.category || 'criteria')}"</div>
        </div>
    `;
    safeCreateIcons();

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
        if (data.updated_user_recommendations && data.updated_user_recommendations.length > 0) {
            renderRecommendationsDirect(data.updated_user_recommendations);
        } else {
            loadPersonalizedRecommendations();
        }
        if (data.user_summary) {
            const summaryBadge = document.getElementById('userSummaryBadge');
            if (summaryBadge) {
                summaryBadge.innerText = data.user_summary;
                const containerEl = document.getElementById('userSummaryBadgeContainer');
                if (containerEl) containerEl.style.display = 'inline-flex';
            }
        }
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
                <div class="empty-state-desc">No creators matched your query "${escapeHtml(query)}". Try broadening your search.</div>
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
                <button type="button" class="btn btn-secondary btn-sm" onclick="showCreatorModal('${escapeHtml(c.username)}')">
                    <span>View Profile</span>
                </button>
                <button type="button" class="btn btn-primary btn-sm" onclick="searchSimilarCreator('${escapeHtml(c.username)}')">
                    <span>Find Similar</span>
                </button>
            </div>
        </div>
    `).join('');

    safeCreateIcons();
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
            const containerEl = document.getElementById('userSummaryBadgeContainer');
            if (containerEl) {
                containerEl.style.display = 'inline-flex';
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

        safeCreateIcons();
    } catch (e) {
    }
}

function setupChatSystem() {
    const chatForm = document.getElementById('chatForm');
    const chatInput = document.getElementById('chatInput');
    const chatSendBtn = document.getElementById('chatSendBtn');
    const chatMessages = document.getElementById('chatMessages');
    const suggestionPills = document.querySelectorAll('.suggestion-pill');

    if (!chatInput || !chatMessages) return;

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
                    const summaryWrap = summaryEl.closest('.summary-indicator');
                    if (summaryWrap) summaryWrap.style.display = 'flex';
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

    if (chatForm) {
        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await sendChatMessage();
        });
    }

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

    safeCreateIcons();
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
                    <div class="msg-avatar"><i data-lucide="bot" style="width: 15px; height: 15px;"></i></div>
                    <div class="msg-bubble">
                        Ask a question about creators, benchmarks, or campaign matches. I'll provide direct, concise answers.
                    </div>
                </div>
            `;
            safeCreateIcons();
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
    safeCreateIcons();
    container.scrollTop = container.scrollHeight;
}

function appendAiMessage(text, recommendations) {
    const container = document.getElementById('chatMessages');
    if (!container) return;

    const safeText = String(text || '').replace(/\n/g, '<br>');
    const recsHtml = recommendations && recommendations.length > 0 ? `
        <div class="chat-rec-chips">
            ${recommendations.map(r => `
                <span class="chat-rec-chip" onclick="showCreatorModal('${escapeHtml(r.username)}')">
                    <i data-lucide="user" style="width: 12px; height: 12px;"></i>
                    @${escapeHtml(r.username)} (${escapeHtml(r.category || 'Creator')})
                </span>
            `).join('')}
        </div>
    ` : '';

    const row = document.createElement('div');
    row.className = 'message-row ai-msg';
    row.innerHTML = `
        <div class="msg-avatar"><i data-lucide="bot" style="width: 15px; height: 15px;"></i></div>
        <div class="msg-bubble">
            <div>${safeText}</div>
            ${recsHtml}
        </div>
    `;
    container.appendChild(row);
    safeCreateIcons();
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
        <div class="msg-avatar"><i data-lucide="bot" style="width: 15px; height: 15px;"></i></div>
        <div class="msg-bubble" style="color: var(--text-muted);">
            Analyzing query...
        </div>
    `;
    container.appendChild(row);
    safeCreateIcons();
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
        <div style="text-align: center; padding: 2.5rem; color: var(--text-muted);">
            <div>Loading status metrics for @${escapeHtml(username)}...</div>
        </div>
    `;

    try {
        const res = await fetch(`/api/creator/${encodeURIComponent(username)}`);
        if (!res.ok) throw new Error('Creator not found');
        const data = await res.json();
        const c = data.creator;
        if (!c) throw new Error('Invalid creator response');

        const initial = (c.full_name || c.username || 'C').charAt(0).toUpperCase();
        const lookalikes = c.lookalikes || [];

        const lookalikesHtml = lookalikes.length > 0 ? `
            <div class="creator-modal-lookalikes-section">
                <h4 class="creator-modal-subtitle">Niche Lookalikes</h4>
                <div class="creator-modal-lookalikes-list">
                    ${lookalikes.map(l => `
                        <div class="lookalike-row" onclick="showCreatorModal('${escapeHtml(l.username)}')">
                            <div class="lookalike-left">
                                <div class="creator-avatar-small">${(l.full_name || l.username || 'C').charAt(0).toUpperCase()}</div>
                                <div>
                                    <div class="lookalike-handle">@${escapeHtml(l.username)}</div>
                                    <div class="lookalike-sub">${escapeHtml(l.category || 'Creator')}</div>
                                </div>
                            </div>
                            <div class="lookalike-right">
                                <span class="tabular-nums">${escapeHtml(l.followers_formatted)}</span>
                                <span class="lookalike-eng tabular-nums">${escapeHtml(l.engagement_formatted)}</span>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        ` : '';

        body.innerHTML = `
            <div class="creator-modal-content">
                <div class="creator-modal-header">
                    <div class="creator-avatar" style="width: 54px; height: 54px; font-size: 1.3rem;">
                        ${initial}
                    </div>
                    <div class="creator-modal-title-wrap">
                        <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
                            <h3 class="creator-modal-name">${escapeHtml(c.full_name || c.username)}</h3>
                            ${c.is_verified ? '<span class="verified-tag"><i data-lucide="check" style="width: 12px; height: 12px;"></i> Verified</span>' : ''}
                        </div>
                        <div class="creator-modal-meta">
                            <span class="creator-handle">@${escapeHtml(c.username)}</span>
                            <span class="badge-category">${escapeHtml(c.category)}</span>
                            <span class="result-pill">${escapeHtml(c.follower_tier)}</span>
                        </div>
                    </div>
                </div>

                ${c.bio ? `<div class="creator-modal-bio">${escapeHtml(c.bio)}</div>` : ''}

                <div class="creator-status-grid">
                    <div class="status-cell">
                        <span class="status-cell-label">Total Followers</span>
                        <span class="status-cell-value tabular-nums">${escapeHtml(c.followers_formatted)}</span>
                        <span class="status-cell-sub">Exact: ${Number(c.followers || 0).toLocaleString()}</span>
                    </div>
                    <div class="status-cell">
                        <span class="status-cell-label">Engagement Rate</span>
                        <span class="status-cell-value tabular-nums status-accent">${escapeHtml(c.engagement_formatted)}</span>
                        <span class="status-cell-sub">Active community ratio</span>
                    </div>
                    <div class="status-cell">
                        <span class="status-cell-label">Average Likes</span>
                        <span class="status-cell-value tabular-nums">${escapeHtml(c.avg_likes_formatted)}</span>
                        <span class="status-cell-sub">Per recent publication</span>
                    </div>
                    <div class="status-cell">
                        <span class="status-cell-label">Average Comments</span>
                        <span class="status-cell-value tabular-nums">${escapeHtml(c.avg_comments_formatted)}</span>
                        <span class="status-cell-sub">Interaction benchmark</span>
                    </div>
                    <div class="status-cell">
                        <span class="status-cell-label">Follower Tier</span>
                        <span class="status-cell-value">${escapeHtml(c.follower_tier)}</span>
                        <span class="status-cell-sub">Audience scale bracket</span>
                    </div>
                    <div class="status-cell">
                        <span class="status-cell-label">Cataloged Posts</span>
                        <span class="status-cell-value tabular-nums">${c.posts_count > 0 ? Number(c.posts_count).toLocaleString() : 'Indexed'}</span>
                        <span class="status-cell-sub">Tracked content volume</span>
                    </div>
                </div>

                <div class="creator-modal-actions">
                    <button type="button" class="btn btn-primary btn-sm" onclick="askAiAboutCreator('${escapeHtml(c.username)}')">
                        <i data-lucide="message-square" style="width: 14px; height: 14px;"></i>
                        <span>Ask AI about @${escapeHtml(c.username)}</span>
                    </button>
                    <button type="button" class="btn btn-secondary btn-sm" onclick="searchSimilarCreator('${escapeHtml(c.username)}')">
                        <i data-lucide="users" style="width: 14px; height: 14px;"></i>
                        <span>Find Lookalikes</span>
                    </button>
                    <a href="${escapeHtml(c.instagram_url)}" target="_blank" rel="noopener noreferrer" class="btn btn-secondary btn-sm">
                        <i data-lucide="external-link" style="width: 14px; height: 14px;"></i>
                        <span>Instagram Profile</span>
                    </a>
                </div>

                ${lookalikesHtml}
            </div>
        `;
        safeCreateIcons();
    } catch (e) {
        body.innerHTML = `
            <div style="text-align: center; padding: 2rem; color: var(--danger);">
                <div style="font-weight: 600; margin-bottom: 0.5rem;">Unable to load profile data</div>
                <div style="font-size: 0.85rem; color: var(--text-muted);">Please try again or select another creator.</div>
            </div>
        `;
    }
}

function askAiAboutCreator(username) {
    const modal = document.getElementById('creatorModal');
    if (modal) modal.style.display = 'none';

    const chatInput = document.getElementById('chatInput');
    const chatForm = document.getElementById('chatForm');
    if (chatInput && chatForm) {
        chatInput.value = `Evaluate @${username} for a brand campaign`;
        const submitEvent = new Event('submit', { cancelable: true });
        chatForm.dispatchEvent(submitEvent);
    }
}

function searchSimilarCreator(username) {
    const searchInput = document.getElementById('searchInput');
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
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}
