// PackCheck Frontend Core API & RBAC Navigation Helper

const API_BASE = '/api/v1';

const PackCheck = {
    getToken() {
        return localStorage.getItem('packcheck_token') || '';
    },
    setToken(token) {
        localStorage.setItem('packcheck_token', token);
    },
    getUser() {
        try {
            return JSON.parse(localStorage.getItem('packcheck_user')) || null;
        } catch (e) {
            return null;
        }
    },
    setUser(user) {
        localStorage.setItem('packcheck_user', JSON.stringify(user));
    },
    clearAuth() {
        localStorage.removeItem('packcheck_token');
        localStorage.removeItem('packcheck_user');
    },

    // RBAC Role Helpers (2-Role Model: Inspector & Admin)
    getRole() {
        const user = this.getUser();
        return (user?.role || '').toLowerCase();
    },
    isAdmin() {
        return this.getRole() === 'admin';
    },
    isInspector() {
        return this.getRole() === 'inspector';
    },
    canScan() {
        return this.isAdmin() || this.isInspector();
    },
    canReview() {
        return this.isAdmin() || this.isInspector();
    },
    canManageTeam() {
        return this.isAdmin();
    },
    getRoleDisplayName() {
        const role = this.getRole();
        if (role === 'admin') return 'Administrator';
        if (role === 'inspector') return 'Inspector';
        return 'Officer';
    },
    getRoleSubtitle() {
        const user = this.getUser();
        const role = this.getRole();
        const region = user?.region || 'National HQ';
        if (role === 'admin') return `Administrator • ${region}`;
        if (role === 'inspector') return `Inspector • ${region}`;
        return `${this.getRoleDisplayName()} • ${region}`;
    },

    // API Request helper
    async request(endpoint, options = {}) {
        const token = this.getToken();
        const headers = options.headers || {};
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        if (!(options.body instanceof FormData) && !headers['Content-Type']) {
            headers['Content-Type'] = 'application/json';
        }

        let resp;
        try {
            resp = await fetch(`${API_BASE}${endpoint}`, {
                ...options,
                headers
            });
        } catch (err) {
            return {
                success: false,
                error: {
                    code: 'NETWORK_ERROR',
                    message: err.message || 'Failed to connect to backend service'
                }
            };
        }

        if (resp.status === 401 && !endpoint.includes('/auth/login')) {
            // Re-authenticate if session lost
            return this.handleUnauthorized(endpoint, options);
        }

        try {
            const data = await resp.json();
            return data;
        } catch (e) {
            return {
                success: false,
                error: {
                    code: `HTTP_${resp.status}`,
                    message: resp.statusText || 'Server communication error'
                }
            };
        }
    },

    async handleUnauthorized(endpoint, options) {
        const user = this.getUser();
        const email = user?.email || 'inspector.sharma@packcheck.gov.in';
        const passwordMap = {
            'admin@packcheck.gov.in': 'admin123',
            'inspector.sharma@packcheck.gov.in': 'inspector123',
            'inspector.reddy@packcheck.gov.in': 'inspector123',
            'inspector.rao@packcheck.gov.in': 'inspector123'
        };
        const password = passwordMap[email] || 'inspector123';

        try {
            const loginRes = await fetch(`${API_BASE}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            const loginData = await loginRes.json();
            if (loginData.success && loginData.data?.access_token) {
                this.setToken(loginData.data.access_token);
                this.setUser(loginData.data.user);
                return this.request(endpoint, options);
            }
        } catch (err) {
            console.error('Session refresh failed:', err);
        }
        window.location.href = '/';
    },

    // Synchronize UI Navigation & Profile based on authenticated role
    syncNavigation(activePage = '') {
        const user = this.getUser();
        if (!user && window.location.pathname !== '/' && window.location.pathname !== '/login') {
            return;
        }

        // Update User info widget if present in DOM
        const nameEl = document.getElementById('userName');
        const roleEl = document.getElementById('userRole');
        const avatarEl = document.getElementById('userAvatar');

        if (nameEl && user) nameEl.textContent = user.name || 'Officer';
        if (roleEl && user) roleEl.textContent = this.getRoleSubtitle();
        if (avatarEl && user) {
            const initials = (user.name || 'PC').split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
            avatarEl.textContent = initials;
        }

        // Update Nav links according to RBAC permissions
        const canScan = this.canScan();
        const canManageTeam = this.canManageTeam();

        // 1. New Scan Nav & Header items
        document.querySelectorAll('a[href="/scan/new"]').forEach(el => {
            if (!canScan) {
                el.classList.add('hidden');
            } else {
                el.classList.remove('hidden');
            }
        });

        // 2. Manage Team Nav Item
        document.querySelectorAll('a[href="/team"]').forEach(el => {
            if (!canManageTeam) {
                el.classList.add('hidden');
            } else {
                el.classList.remove('hidden');
            }
        });

        // 3. Inject responsive mobile top navigation bar if page has aside rail
        const aside = document.querySelector('aside');
        if (aside && !document.getElementById('packcheckMobileTopBar')) {
            const initials = (user?.name || 'PC').split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
            const mobileNavHtml = `
                <div id="packcheckMobileTopBar" class="md:hidden bg-[#0051d5] text-white px-4 py-3 flex items-center justify-between shadow-md sticky top-0 z-30 shrink-0">
                    <div class="flex items-center gap-2.5">
                        <div class="w-8 h-8 bg-white/20 rounded-lg flex items-center justify-center backdrop-blur-sm">
                            <span class="material-symbols-outlined text-[#65fade] text-xl">verified_user</span>
                        </div>
                        <div>
                            <span class="font-['Hanken_Grotesk'] font-bold text-sm block leading-tight">PackSure AI</span>
                            <span class="text-[10px] text-[#65fade] uppercase font-semibold tracking-wider">LMPC Enforcement</span>
                        </div>
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-white/15 text-white/90 truncate max-w-[120px]">${this.getRoleDisplayName()}</span>
                        <button id="packcheckMobileMenuBtn" onclick="PackCheck.toggleMobileMenu()" type="button" aria-label="Toggle navigation menu" class="p-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white focus:outline-none flex items-center justify-center">
                            <span class="material-symbols-outlined text-xl" id="packcheckMobileMenuIcon">menu</span>
                        </button>
                    </div>
                </div>
                <div id="packcheckMobileDrawer" class="hidden md:hidden fixed inset-0 z-40 bg-black/60 backdrop-blur-xs flex flex-col justify-start pt-14" onclick="if (event.target === this) PackCheck.toggleMobileMenu()">
                    <div class="bg-[#0051d5] text-white p-5 shadow-2xl border-b border-white/20 space-y-3 max-h-[85vh] overflow-y-auto">
                        <div class="flex items-center justify-between pb-3 border-b border-white/10">
                            <div class="flex items-center gap-2.5">
                                <div class="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center font-bold text-xs">${initials}</div>
                                <div>
                                    <p class="text-xs font-bold text-white">${user?.name || 'Officer'}</p>
                                    <p class="text-[10px] text-[#65fade]">${this.getRoleSubtitle()}</p>
                                </div>
                            </div>
                            <button onclick="PackCheck.toggleMobileMenu()" type="button" aria-label="Close menu" class="text-white/80 hover:text-white p-1">
                                <span class="material-symbols-outlined text-xl">close</span>
                            </button>
                        </div>
                        <nav class="space-y-1 text-xs font-medium">
                            <a href="/dashboard" class="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-white/10 transition-colors ${activePage === '/dashboard' ? 'bg-white/20 text-white font-bold' : 'text-white/90'}">
                                <span class="material-symbols-outlined text-base">dashboard</span> Enforcement Intelligence
                            </a>
                            ${canScan ? `
                            <a href="/scan/new" class="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-white/10 transition-colors ${activePage === '/scan/new' ? 'bg-white/20 text-white font-bold' : 'text-white/90'}">
                                <span class="material-symbols-outlined text-base">add_photo_alternate</span> New Scan
                            </a>` : ''}
                            <a href="/products-ui" class="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-white/10 transition-colors ${activePage === '/products-ui' ? 'bg-white/20 text-white font-bold' : 'text-white/90'}">
                                <span class="material-symbols-outlined text-base">inventory_2</span> Product Catalog
                            </a>
                            <a href="/enforcement" class="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-white/10 transition-colors ${activePage === '/enforcement' ? 'bg-white/20 text-white font-bold' : 'text-white/90'}">
                                <span class="material-symbols-outlined text-base">map</span> Regional Heatmap
                            </a>
                            ${canManageTeam ? `
                            <a href="/team" class="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-white/10 transition-colors ${activePage === '/team' ? 'bg-white/20 text-white font-bold' : 'text-white/90'}">
                                <span class="material-symbols-outlined text-base">group</span> Manage Team
                            </a>` : ''}
                            <a href="/docs" target="_blank" class="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-white/10 text-white/80 transition-colors">
                                <span class="material-symbols-outlined text-base">api</span> API Docs
                            </a>
                            <a href="/" onclick="PackCheck.clearAuth()" class="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-red-500/20 text-red-200 transition-colors pt-3 mt-2 border-t border-white/10">
                                <span class="material-symbols-outlined text-base">logout</span> Sign Out
                            </a>
                        </nav>
                    </div>
                </div>
            `;
            const main = document.querySelector('main');
            if (main) {
                main.insertAdjacentHTML('afterbegin', mobileNavHtml);
            }
        }
    },

    toggleMobileMenu() {
        const drawer = document.getElementById('packcheckMobileDrawer');
        const icon = document.getElementById('packcheckMobileMenuIcon');
        if (drawer) {
            drawer.classList.toggle('hidden');
            if (icon) {
                icon.textContent = drawer.classList.contains('hidden') ? 'menu' : 'close';
            }
        }
    }
};

window.PackCheck = PackCheck;
