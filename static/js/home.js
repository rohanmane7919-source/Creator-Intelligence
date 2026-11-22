/**
 * Creator Intelligence - Home Page Interactive Logic
 * Handles live interactive search, ROI campaign calculator, FAQ accordion, and creator preview modals.
 */

function safeCreateIcons() {
    try {
        if (window.lucide && typeof window.lucide.createIcons === 'function') {
            window.lucide.createIcons();
        }
    } catch (e) {
        console.warn('Lucide icons error:', e);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    safeCreateIcons();
    initHeroLiveSearch();
    initRoiCalculator();
    initFaqAccordion();
    initModalHandlers();
});

/* ==========================================================================
   1. Live Interactive Catalog Search (Hero / Demo Section)
   ========================================================================== */
let homeSearchMode = 'auto';

function initHeroLiveSearch() {
    const input = document.getElementById('homeSearchInput');
    const submitBtn = document.getElementById('homeSearchBtn');
    const modeBtns = document.querySelectorAll('.home-mode-btn');
    const pills = document.querySelectorAll('.suggestion-chip');
    const categorySelect = document.getElementById('homeCategorySelect');

    if (!input) return;

    // Mode Toggle (Topic vs Lookalike)
    modeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            modeBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            homeSearchMode = btn.getAttribute('data-mode') || 'auto';
            if (homeSearchMode === 'similar') {
                input.placeholder = "Enter creator handle to find lookalikes (e.g. 'cristiano', 'kyliejenner')...";
            } else {
                input.placeholder = "Search topics, categories, or keywords (e.g. 'sports', 'fitness', 'tech')...";
            }
        });
    });

    // Suggestion Chips
    pills.forEach(pill => {
        pill.addEventListener('click', () => {
            const val = pill.getAttribute('data-query');
            const mode = pill.getAttribute('data-mode') || 'auto';
            
            // Switch mode if chip specifies
            modeBtns.forEach(b => {
                if (b.getAttribute('data-mode') === mode) {
                    b.click();
                }
            });

            input.value = val;
            executeHomeSearch(val, mode, categorySelect ? categorySelect.value : null);
        });
    });

    // Category dropdown
    if (categorySelect) {
        categorySelect.addEventListener('change', () => {
            executeHomeSearch(input.value.trim(), homeSearchMode, categorySelect.value);
        });
    }

    // Submit button
    if (submitBtn) {
        submitBtn.addEventListener('click', (e) => {
            e.preventDefault();
            executeHomeSearch(input.value.trim(), homeSearchMode, categorySelect ? categorySelect.value : null);
        });
    }

    // Enter key
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            executeHomeSearch(input.value.trim(), homeSearchMode, categorySelect ? categorySelect.value : null);
        }
    });
}

async function executeHomeSearch(query, mode, category) {
    const grid = document.getElementById('homeCreatorsGrid');
    const countBadge = document.getElementById('homeResultCount');
    if (!grid) return;

    grid.innerHTML = `
        <div class="home-search-loading">
            <div class="spinner-circle"></div>
            <p>Scanning vector index and scoring creators...</p>
        </div>
    `;

    try {
        const payload = {
            query: query || "",
            mode: mode || "auto",
            category: category || null,
            top_k: 8
        };

        const res = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!res.ok) throw new Error('Search failed');
        const data = await res.json();
        const results = data.results || [];

        if (countBadge) {
            countBadge.innerText = `${results.length} Matches Found`;
            countBadge.style.display = 'inline-flex';
        }

        renderHomeCreators(results, query);
    } catch (err) {
        console.error(err);
        grid.innerHTML = `
            <div class="home-search-empty">
                <i data-lucide="alert-circle" style="width: 32px; height: 32px; color: var(--danger);"></i>
                <h4>Unable to complete live search</h4>
                <p>Please try a different keyword or category.</p>
            </div>
        `;
        safeCreateIcons();
    }
}

function renderHomeCreators(creators, query) {
    const grid = document.getElementById('homeCreatorsGrid');
    if (!grid) return;

    if (!creators || creators.length === 0) {
        grid.innerHTML = `
            <div class="home-search-empty">
                <div class="empty-icon-wrap"><i data-lucide="search-x"></i></div>
                <h4>No creators matched "${escapeHtml(query || 'filter')}"</h4>
                <p>Try searching broader terms like "tech", "sports", "fitness", or try lookalike search for "@cristiano".</p>
            </div>
        `;
        safeCreateIcons();
        return;
    }

    grid.innerHTML = creators.map(c => {
        const initial = (c.username || 'C')[0].toUpperCase();
        const verified = c.is_verified ? `<span class="verified-badge" title="Verified Creator"><i data-lucide="badge-check"></i></span>` : '';
        const matchReason = c.match_reason ? `<div class="card-match-reason"><i data-lucide="check" style="width: 12px; height: 12px;"></i> <span>${escapeHtml(c.match_reason)}</span></div>` : '';

        return `
            <div class="creator-showcase-card" onclick="openHomeCreatorModal('${escapeHtml(c.username)}')">
                <div class="card-top-row">
                    <div class="creator-avatar-wrap">
                        <div class="creator-avatar-badge">${initial}</div>
                    </div>
                    <span class="card-tier-pill">${escapeHtml(c.follower_tier || 'Creator')}</span>
                </div>

                <div class="creator-info-block">
                    <div class="creator-name-line">
                        <h4 class="creator-display-name">${escapeHtml(c.full_name || c.username)}</h4>
                        ${verified}
                    </div>
                    <div class="creator-handle-text">@${escapeHtml(c.username)}</div>
                    <span class="creator-category-chip">${escapeHtml(c.category || 'Creator')}</span>
                </div>

                <p class="creator-bio-snippet">${escapeHtml(c.bio || 'Influencer with active community engagement and proven brand collaboration affinity.')}</p>

                ${matchReason}

                <div class="creator-metrics-row">
                    <div class="metric-item">
                        <span class="metric-val">${c.followers_formatted || '0'}</span>
                        <span class="metric-lbl">Followers</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-val metric-eng">${c.engagement_formatted || '0.0%'}</span>
                        <span class="metric-lbl">Engagement</span>
                    </div>
                </div>

                <div class="card-footer-action">
                    <button type="button" class="btn-card-preview">
                        <span>View Deep Intel</span>
                        <i data-lucide="chevron-right" style="width: 14px; height: 14px;"></i>
                    </button>
                </div>
            </div>
        `;
    }).join('');

    safeCreateIcons();
}

/* ==========================================================================
   2. Campaign ROI & Reach Simulator
   ========================================================================== */
function initRoiCalculator() {
    const budgetSlider = document.getElementById('roiBudgetSlider');
    const budgetDisplay = document.getElementById('roiBudgetValue');
    const tierSelect = document.getElementById('roiTierSelect');

    const outCreators = document.getElementById('calcCreators');
    const outReach = document.getElementById('calcReach');
    const outEngagements = document.getElementById('calcEngagements');
    const outValue = document.getElementById('calcValue');

    if (!budgetSlider || !budgetDisplay) return;

    const tierMetrics = {
        'nano': { avgCost: 250, avgFollowers: 7000, avgEngRate: 0.048, cpe: 0.85 },
        'micro': { avgCost: 800, avgFollowers: 45000, avgEngRate: 0.034, cpe: 0.65 },
        'mid': { avgCost: 3500, avgFollowers: 250000, avgEngRate: 0.026, cpe: 0.55 },
        'macro': { avgCost: 9000, avgFollowers: 750000, avgEngRate: 0.019, cpe: 0.50 },
        'mega': { avgCost: 25000, avgFollowers: 3000000, avgEngRate: 0.014, cpe: 0.45 },
        'mixed': { avgCost: 2000, avgFollowers: 180000, avgEngRate: 0.031, cpe: 0.60 }
    };

    function updateCalculator() {
        const budget = parseInt(budgetSlider.value, 10);
        const tier = tierSelect ? tierSelect.value : 'mixed';
        const config = tierMetrics[tier] || tierMetrics['mixed'];

        // Format Budget Display
        budgetDisplay.innerText = `$${budget.toLocaleString()}`;

        // Compute numbers
        const estimatedCreators = Math.max(1, Math.round(budget / config.avgCost));
        const estimatedReach = estimatedCreators * config.avgFollowers * 0.72; // conservative unique reach factor
        const estimatedEngagements = Math.round(estimatedReach * config.avgEngRate);
        const projectedValue = Math.round(budget * (1.8 + (config.avgEngRate * 25)));

        if (outCreators) outCreators.innerText = estimatedCreators.toString();
        if (outReach) outReach.innerText = formatNumberCompact(estimatedReach);
        if (outEngagements) outEngagements.innerText = formatNumberCompact(estimatedEngagements);
        if (outValue) outValue.innerText = `$${formatNumberCompact(projectedValue)}`;
    }

    budgetSlider.addEventListener('input', updateCalculator);
    if (tierSelect) tierSelect.addEventListener('change', updateCalculator);

    // Initial run
    updateCalculator();
}

function formatNumberCompact(num) {
    if (!num || isNaN(num)) return '0';
    if (num >= 1_000_000) return (num / 1_000_000).toFixed(1) + 'M';
    if (num >= 1_000) return (num / 1_000).toFixed(1) + 'K';
    return Math.round(num).toString();
}

/* ==========================================================================
   3. FAQ Accordion Logic
   ========================================================================== */
function initFaqAccordion() {
    const faqItems = document.querySelectorAll('.faq-item');
    faqItems.forEach(item => {
        const header = item.querySelector('.faq-question');
        if (!header) return;

        header.addEventListener('click', () => {
            const isOpen = item.classList.contains('active');
            
            // Close all items
            faqItems.forEach(i => i.classList.remove('active'));

            // Toggle clicked item
            if (!isOpen) {
                item.classList.add('active');
            }
        });
    });
}

/* ==========================================================================
   4. Creator Intelligence Preview Modal
   ========================================================================== */
async function openHomeCreatorModal(username) {
    const modal = document.getElementById('homeCreatorModal');
    const modalBody = document.getElementById('homeModalBody');
    if (!modal || !modalBody) return;

    modalBody.innerHTML = `
        <div style="text-align: center; padding: 2.5rem; color: var(--text-muted);">
            <div>Loading status metrics for @${escapeHtml(username)}...</div>
        </div>
    `;
    modal.style.display = 'flex';

    try {
        const res = await fetch(`/api/creator/${encodeURIComponent(username)}`);
        if (!res.ok) throw new Error('Creator not found');
        const data = await res.json();
        const creator = data.creator;

        if (!creator) {
            modalBody.innerHTML = `
                <div style="text-align: center; padding: 2rem; color: var(--danger);">
                    <h4>Creator Profile Not Found</h4>
                    <p>Could not retrieve data for @${escapeHtml(username)}.</p>
                </div>
            `;
            return;
        }

        const initial = (creator.full_name || creator.username || 'C')[0].toUpperCase();
        const lookalikes = creator.lookalikes || [];

        modalBody.innerHTML = `
            <div class="modal-creator-header">
                <div class="creator-avatar-badge" style="width: 54px; height: 54px; font-size: 1.3rem;">${initial}</div>
                <div class="modal-creator-meta">
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <h3 class="modal-creator-title">${escapeHtml(creator.full_name || creator.username)}</h3>
                        ${creator.is_verified ? '<span class="verified-tag"><i data-lucide="check" style="width: 12px; height: 12px;"></i> Verified</span>' : ''}
                    </div>
                    <div class="creator-handle-text">@${escapeHtml(creator.username)} &bull; <span class="creator-category-chip">${escapeHtml(creator.category || 'Creator')}</span></div>
                    <span class="card-tier-pill" style="margin-top: 0.35rem;">${escapeHtml(creator.follower_tier || 'Tier')}</span>
                </div>
            </div>

            ${creator.bio ? `<div class="modal-bio-quote">${escapeHtml(creator.bio)}</div>` : ''}

            <div class="modal-stats-grid">
                <div class="modal-stat-box">
                    <div class="modal-stat-num tabular-nums">${creator.followers_formatted || '0'}</div>
                    <div class="modal-stat-lbl">Followers (${Number(creator.followers || 0).toLocaleString()})</div>
                </div>
                <div class="modal-stat-box">
                    <div class="modal-stat-num tabular-nums" style="color: var(--success);">${creator.engagement_formatted || '0.0%'}</div>
                    <div class="modal-stat-lbl">Engagement Rate</div>
                </div>
                <div class="modal-stat-box">
                    <div class="modal-stat-num tabular-nums">${creator.avg_likes_formatted || '0'}</div>
                    <div class="modal-stat-lbl">Average Likes</div>
                </div>
                <div class="modal-stat-box">
                    <div class="modal-stat-num tabular-nums">${creator.avg_comments_formatted || '0'}</div>
                    <div class="modal-stat-lbl">Average Comments</div>
                </div>
            </div>

            ${lookalikes.length > 0 ? `
                <div style="margin-top: 1.25rem; border-top: 1px solid var(--border-color); padding-top: 1rem;">
                    <div style="font-size: 0.82rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 0.75rem;">Niche Lookalikes</div>
                    <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                        ${lookalikes.map(l => `
                            <div style="display: flex; align-items: center; justify-content: space-between; padding: 0.5rem 0.75rem; border: 1px solid var(--border-color); border-radius: var(--radius-sm); background: var(--bg-card); cursor: pointer;" onclick="openHomeCreatorModal('${escapeHtml(l.username)}')">
                                <div style="display: flex; align-items: center; gap: 0.5rem;">
                                    <div class="creator-avatar-small" style="width: 24px; height: 24px; font-size: 0.75rem;">${(l.full_name || l.username || 'C')[0].toUpperCase()}</div>
                                    <span style="font-size: 0.82rem; font-weight: 500;">@${escapeHtml(l.username)}</span>
                                    <span style="font-size: 0.75rem; color: var(--text-muted);">${escapeHtml(l.category)}</span>
                                </div>
                                <div style="font-size: 0.78rem; font-variant-numeric: tabular-nums;">
                                    <span>${escapeHtml(l.followers_formatted)}</span>
                                    <span style="color: var(--success); font-weight: 600; margin-left: 0.4rem;">${escapeHtml(l.engagement_formatted)}</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}

            <div class="modal-actions-row" style="margin-top: 1.25rem;">
                <a href="/login" class="btn btn-primary" style="flex: 1;">
                    <i data-lucide="log-in" style="width: 15px; height: 15px;"></i>
                    <span>Sign In to Access Full Campaign Tools</span>
                </a>
                <button type="button" class="btn btn-secondary" onclick="closeHomeCreatorModal()">Close</button>
            </div>
        `;
        safeCreateIcons();
    } catch (e) {
        modalBody.innerHTML = `
            <div style="text-align: center; padding: 2rem; color: var(--danger);">
                <h4>Error loading creator preview</h4>
            </div>
        `;
    }
}

function closeHomeCreatorModal() {
    const modal = document.getElementById('homeCreatorModal');
    if (modal) modal.style.display = 'none';
}

function initModalHandlers() {
    const modal = document.getElementById('homeCreatorModal');
    const closeBtn = document.getElementById('closeHomeModalBtn');

    if (closeBtn) {
        closeBtn.addEventListener('click', closeHomeCreatorModal);
    }

    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeHomeCreatorModal();
            }
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
        .replace(/'/g, '&#039;');
}
