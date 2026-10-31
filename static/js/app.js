/**
 * CreatorLens Frontend Application Logic
 */

document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const searchInput = document.getElementById("searchInput");
    const searchSubmitBtn = document.getElementById("searchSubmitBtn");
    const clearSearchBtn = document.getElementById("clearSearchBtn");
    const toggleFilterBtn = document.getElementById("toggleFilterBtn");
    const filterPanel = document.getElementById("filterPanel");
    const intentBanner = document.getElementById("intentBanner");
    const intentText = document.getElementById("intentText");
    const searchStateIcon = document.getElementById("searchStateIcon");
    
    // Tabs
    const tabAuto = document.getElementById("tabAuto");
    const tabQuery = document.getElementById("tabQuery");
    const tabSimilar = document.getElementById("tabSimilar");
    let currentMode = "auto"; // 'auto', 'query', 'similar'

    // Filters
    const tierSelect = document.getElementById("tierSelect");
    const categorySelect = document.getElementById("categorySelect");
    const topKSelect = document.getElementById("topKSelect");
    const minEngInput = document.getElementById("minEngInput");
    const engValDisplay = document.getElementById("engValDisplay");

    // Sections & Grid
    const resultsSection = document.getElementById("resultsSection");
    const resultsHeader = document.getElementById("resultsHeader");
    const resultsTitle = document.getElementById("resultsTitle");
    const resultsMeta = document.getElementById("resultsMeta");
    const cardsGrid = document.getElementById("cardsGrid");
    const emptyState = document.getElementById("emptyState");
    const loadingState = document.getElementById("loadingState");
    const headerCatalogCount = document.getElementById("headerCatalogCount");

    // Modal
    const addCreatorModal = document.getElementById("addCreatorModal");
    const openAddModalBtn = document.getElementById("openAddModalBtn");
    const closeAddModalBtn = document.getElementById("closeAddModalBtn");
    const cancelAddModalBtn = document.getElementById("cancelAddModalBtn");
    const addCreatorForm = document.getElementById("addCreatorForm");

    // Toast
    const toast = document.getElementById("toastNotification");
    const toastMessage = document.getElementById("toastMessage");

    // -------------------------------------------------------------
    // Search Mode Tab Handling
    // -------------------------------------------------------------
    const setMode = (mode) => {
        currentMode = mode;
        [tabAuto, tabQuery, tabSimilar].forEach(tab => tab.classList.remove("active"));
        if (mode === "auto") {
            tabAuto.classList.add("active");
            searchInput.placeholder = "Try 'football soccer athletes' or 'similar taylorswift'...";
        } else if (mode === "query") {
            tabQuery.classList.add("active");
            searchInput.placeholder = "Search topics (e.g. 'high engagement tech gadget reviews')...";
        } else if (mode === "similar") {
            tabSimilar.classList.add("active");
            searchInput.placeholder = "Enter creator handle (e.g. 'taylorswift' or 'cristiano')...";
        }
        detectIntent(searchInput.value);
    };

    tabAuto.addEventListener("click", () => setMode("auto"));
    tabQuery.addEventListener("click", () => setMode("query"));
    tabSimilar.addEventListener("click", () => setMode("similar"));

    // -------------------------------------------------------------
    // Dynamic Intent Detection as User Types
    // -------------------------------------------------------------
    const detectIntent = (text) => {
        const val = text.trim();
        if (!val) {
            intentBanner.style.display = "none";
            clearSearchBtn.style.display = "none";
            return;
        }

        clearSearchBtn.style.display = "flex";

        if (currentMode === "similar") {
            intentBanner.style.display = "inline-flex";
            intentText.innerHTML = `Mode: <strong>Lookalike Search</strong> for <code>@${val.replace('@', '')}</code>`;
            return;
        }

        const similarMatch = val.match(/^(?:similar\s+to|similar|like|lookalikes?\s+for|lookalikes?)\s+[@]?([a-zA-Z0-9._]+)$/i);
        if (similarMatch) {
            intentBanner.style.display = "inline-flex";
            intentText.innerHTML = `Auto-Detected: <strong>Lookalike Search</strong> for <code>@${similarMatch[1]}</code>`;
        } else if (currentMode === "auto") {
            intentBanner.style.display = "inline-flex";
            intentText.innerHTML = `Auto-Detected: <strong>Semantic Query</strong>`;
        } else {
            intentBanner.style.display = "none";
        }
    };

    searchInput.addEventListener("input", (e) => detectIntent(e.target.value));

    clearSearchBtn.addEventListener("click", () => {
        searchInput.value = "";
        clearSearchBtn.style.display = "none";
        intentBanner.style.display = "none";
        searchInput.focus();
    });

    // -------------------------------------------------------------
    // Filter Panel Toggle & Sliders
    // -------------------------------------------------------------
    toggleFilterBtn.addEventListener("click", () => {
        const isHidden = filterPanel.style.display === "none";
        filterPanel.style.display = isHidden ? "block" : "none";
        toggleFilterBtn.classList.toggle("active", isHidden);
    });

    minEngInput.addEventListener("input", (e) => {
        engValDisplay.textContent = `${parseFloat(e.target.value).toFixed(1)}%`;
    });

    // -------------------------------------------------------------
    // Preset Quick Search Pills
    // -------------------------------------------------------------
    document.querySelectorAll(".preset-pill").forEach(pill => {
        pill.addEventListener("click", () => {
            const query = pill.getAttribute("data-query");
            searchInput.value = query;
            setMode("auto");
            detectIntent(query);
            executeSearch();
        });
    });

    // -------------------------------------------------------------
    // Metric Formatters
    // -------------------------------------------------------------
    const formatFollowers = (num) => {
        if (!num || isNaN(num) || num <= 0) return "0";
        if (num >= 1_000_000_000) return (num / 1_000_000_000).toFixed(1) + "B";
        if (num >= 1_000_000) return (num / 1_000_000).toFixed(1) + "M";
        if (num >= 1_000) return (num / 1_000).toFixed(1) + "K";
        return num.toLocaleString();
    };

    const getInitials = (name, uname) => {
        const target = name && name.trim() ? name.trim() : uname;
        const parts = target.split(/\s+/);
        if (parts.length >= 2) {
            return (parts[0][0] + parts[1][0]).toUpperCase();
        }
        return target.slice(0, 2).toUpperCase();
    };

    // -------------------------------------------------------------
    // Execute Search API
    // -------------------------------------------------------------
    const executeSearch = async () => {
        const queryText = searchInput.value.trim();
        if (!queryText) {
            searchInput.focus();
            return;
        }

        // Show loading state
        emptyState.style.display = "none";
        resultsHeader.style.display = "none";
        cardsGrid.innerHTML = "";
        loadingState.style.display = "block";

        const minEngVal = parseFloat(minEngInput.value);

        const payload = {
            query: queryText,
            mode: currentMode,
            category: categorySelect.value || null,
            follower_tier: tierSelect.value || null,
            min_engagement: minEngVal > 0 ? (minEngVal / 100) : null,
            top_k: parseInt(topKSelect.value) || 5
        };

        try {
            const res = await fetch("/api/recommend", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            loadingState.style.display = "none";

            if (!res.ok) {
                showToast(data.detail || "Search request failed", "error");
                renderErrorState(data.detail || "Unable to retrieve recommendations.");
                return;
            }

            renderResults(data);
        } catch (err) {
            loadingState.style.display = "none";
            showToast("Network error contacting recommendation engine", "error");
            renderErrorState("Network connection failed. Please ensure main.py is running.");
        }
    };

    searchSubmitBtn.addEventListener("click", executeSearch);
    searchInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") executeSearch();
    });

    // -------------------------------------------------------------
    // Render Results & Creator Cards
    // -------------------------------------------------------------
    const renderResults = (data) => {
        const results = data.results || [];
        cardsGrid.innerHTML = "";

        if (results.length === 0) {
            resultsHeader.style.display = "none";
            emptyState.style.display = "block";
            emptyState.innerHTML = `
                <div class="empty-icon"><i data-lucide="search-x"></i></div>
                <h3>No creators matched this criteria</h3>
                <p>Try widening your follower filters, lowering the minimum engagement rate, or adjusting your query.</p>
            `;
            lucide.createIcons();
            return;
        }

        // Setup Header
        resultsHeader.style.display = "flex";
        if (data.type === "similarity") {
            resultsTitle.innerHTML = `Lookalike Creators Similar to <strong>@${data.target_creator}</strong>`;
            resultsMeta.textContent = `Found ${results.length} lookalike creators with matching tone & audience`;
        } else {
            resultsTitle.innerHTML = `Top Creators for <em>"${data.query}"</em>`;
            resultsMeta.textContent = `Found ${results.length} matching creators ranked by semantic relevance & performance`;
        }

        results.forEach((c) => {
            const card = document.createElement("div");
            card.className = "creator-card";

            const fullName = c.full_name || c.username;
            const initials = getInitials(fullName, c.username);
            const followersFormatted = formatFollowers(c.followers);
            const engRatePercent = ((c.engagement_rate || 0) * 100).toFixed(2);
            
            // Engagement color class
            let engClass = "eng-normal";
            if (c.engagement_rate >= 0.02) engClass = "eng-high";
            else if (c.engagement_rate >= 0.01) engClass = "eng-mid";

            // Match Score Pill
            let matchLabel = "";
            if (c.similarity_score !== undefined) {
                matchLabel = `Sim: ${(c.similarity_score * 100).toFixed(0)}%`;
            } else if (c.composite_score !== undefined) {
                matchLabel = `Score: ${(c.composite_score * 100).toFixed(0)}%`;
            }

            card.innerHTML = `
                <div>
                    <div class="card-header">
                        <div class="creator-avatar">${initials}</div>
                        ${matchLabel ? `<div class="match-pill"><i data-lucide="sparkle"></i>${matchLabel}</div>` : ""}
                    </div>

                    <div class="creator-info">
                        <h4 class="creator-name">${fullName}</h4>
                        <div class="creator-handle">@${c.username}</div>
                        <span class="category-tag">${c.category || "General"}</span>
                    </div>

                    <p class="creator-bio">${c.bio || "Verified creator profile active in this niche."}</p>
                </div>

                <div>
                    <div class="metrics-row">
                        <div class="metric-item">
                            <span class="metric-label">Followers</span>
                            <span class="metric-value">${followersFormatted}</span>
                            <span class="tier-badge">${c.follower_tier || "Active"}</span>
                        </div>
                        <div class="metric-item">
                            <span class="metric-label">Engagement</span>
                            <span class="metric-value ${engClass}">${engRatePercent}%</span>
                            <span class="tier-badge">60-Day Avg</span>
                        </div>
                    </div>

                    <div class="card-actions">
                        <button class="btn btn-secondary lookalike-btn" data-target="${c.username}" title="Find similar creators">
                            <i data-lucide="users"></i>
                            <span>Find Similar</span>
                        </button>
                        <a href="https://instagram.com/${c.username}" target="_blank" rel="noopener noreferrer" class="btn btn-secondary" title="View Instagram">
                            <i data-lucide="external-link"></i>
                            <span>Profile</span>
                        </a>
                    </div>
                </div>
            `;

            cardsGrid.appendChild(card);
        });

        // Attach Lookalike Click Listeners
        cardsGrid.querySelectorAll(".lookalike-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const targetUser = btn.getAttribute("data-target");
                searchInput.value = `similar ${targetUser}`;
                setMode("similar");
                detectIntent(searchInput.value);
                executeSearch();
                window.scrollTo({ top: resultsSection.offsetTop - 100, behavior: "smooth" });
            });
        });

        lucide.createIcons();
    };

    const renderErrorState = (msg) => {
        resultsHeader.style.display = "none";
        emptyState.style.display = "block";
        emptyState.innerHTML = `
            <div class="empty-icon" style="color: var(--danger);"><i data-lucide="alert-circle"></i></div>
            <h3>Search Request Issue</h3>
            <p>${msg}</p>
        `;
        lucide.createIcons();
    };

    // -------------------------------------------------------------
    // Modal: Add Creator Ingestion
    // -------------------------------------------------------------
    openAddModalBtn.addEventListener("click", () => {
        addCreatorModal.style.display = "flex";
        document.getElementById("newUsername").focus();
    });

    const closeModal = () => {
        addCreatorModal.style.display = "none";
        addCreatorForm.reset();
    };

    closeAddModalBtn.addEventListener("click", closeModal);
    cancelAddModalBtn.addEventListener("click", closeModal);
    addCreatorModal.addEventListener("click", (e) => {
        if (e.target === addCreatorModal) closeModal();
    });

    addCreatorForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const username = document.getElementById("newUsername").value.trim();
        if (!username) return;

        const submitBtn = document.getElementById("submitAddCreatorBtn");
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span>Indexing...</span>`;

        const payload = {
            username: username,
            name: document.getElementById("newName").value.trim() || null,
            category: document.getElementById("newCategory").value.trim() || null,
            followers: parseFloat(document.getElementById("newFollowers").value) || 0,
            engagement_rate: (parseFloat(document.getElementById("newEngRate").value) || 0) / 100,
            bio: document.getElementById("newBio").value.trim() || null,
            token: document.getElementById("newApifyToken").value.trim() || null
        };

        try {
            const res = await fetch("/api/add-creator", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            submitBtn.disabled = false;
            submitBtn.innerHTML = `<i data-lucide="plus"></i><span>Index Creator</span>`;
            lucide.createIcons();

            if (!res.ok) {
                showToast(data.detail || "Failed to add creator", "error");
                return;
            }

            closeModal();
            showToast(`@${username} successfully indexed!`);
            
            // Refresh stats
            const statsRes = await fetch("/api/stats");
            const stats = await statsRes.json();
            headerCatalogCount.textContent = stats.total_creators;

            // Automatically search for the newly added creator
            searchInput.value = `similar ${username}`;
            setMode("similar");
            executeSearch();
        } catch (err) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `<i data-lucide="plus"></i><span>Index Creator</span>`;
            showToast("Network error submitting creator", "error");
        }
    });

    // -------------------------------------------------------------
    // Toast Notification Utility
    // -------------------------------------------------------------
    let toastTimeout;
    const showToast = (message, type = "success") => {
        clearTimeout(toastTimeout);
        toastMessage.textContent = message;
        toast.style.display = "flex";
        toast.style.borderColor = type === "error" ? "var(--danger)" : "var(--border-subtle)";
        
        toastTimeout = setTimeout(() => {
            toast.style.display = "none";
        }, 4000);
    };
});
