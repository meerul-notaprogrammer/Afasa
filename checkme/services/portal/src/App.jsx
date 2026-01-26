import { useAuth } from 'react-oidc-context'
import { BrowserRouter, Routes, Route, Link, useLocation, useNavigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider, useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, useEffect, createContext, useContext } from 'react'

// Create query client
const queryClient = new QueryClient()

// API Context
const ApiContext = createContext(null)

function useApi() {
    const auth = useAuth()

    const fetchApi = async (path, options = {}) => {
        const baseUrl = import.meta.env.VITE_PUBLIC_BASE_URL || ''
        const response = await fetch(`${baseUrl}${path}`, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${auth.user?.access_token}`,
                ...options.headers,
            },
        })
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`)
        }
        return response.json()
    }

    return { fetchApi }
}

// ============================================================================
// Dashboard Component
// ============================================================================
function Dashboard() {
    const { fetchApi } = useApi()

    const { data: tasks } = useQuery({
        queryKey: ['tasks', 'open'],
        queryFn: () => fetchApi('/api/ops/tasks?status=open'),
        staleTime: 30000,
    })

    const { data: proposals } = useQuery({
        queryKey: ['proposals', 'pending'],
        queryFn: () => fetchApi('/api/ops/rules/proposals?status=pending'),
        staleTime: 30000,
    })

    const { data: snapshots } = useQuery({
        queryKey: ['snapshots'],
        queryFn: () => fetchApi('/api/media/snapshots?limit=10'),
        staleTime: 30000,
    })

    return (
        <div className="fade-in space-y-6">
            <h1 className="text-2xl font-bold mb-6">🌱 Farm Dashboard</h1>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard icon="📸" label="Snapshots Today" value={snapshots?.length || 0} color="green" />
                <StatCard icon="🔍" label="Detections" value={8} color="blue" />
                <StatCard icon="📋" label="Open Tasks" value={tasks?.length || 0} color="orange" />
                <StatCard icon="⚡" label="Pending Rules" value={proposals?.length || 0} color="red" />
            </div>

            {/* ThingsBoard Embed */}
            <div className="glass-card">
                <h2 className="text-lg font-semibold mb-4">📊 ThingsBoard Dashboard</h2>
                <div className="bg-background rounded-lg h-64 flex items-center justify-center border border-border">
                    <p className="text-gray-400">ThingsBoard Dashboard will be embedded here</p>
                </div>
            </div>

            {/* Two Column Layout */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Tasks */}
                <div className="glass-card">
                    <h2 className="text-lg font-semibold mb-4">📋 Today's Tasks</h2>
                    {tasks?.length > 0 ? (
                        <div className="space-y-2">
                            {tasks.slice(0, 5).map(task => (
                                <div key={task.id} className="p-3 bg-background rounded-lg flex justify-between items-center">
                                    <div>
                                        <span className={`badge badge-${task.priority <= 2 ? 'danger' : 'warning'} mr-2`}>
                                            {task.priority <= 2 ? 'High' : 'Medium'}
                                        </span>
                                        <span>{task.title}</span>
                                    </div>
                                    <span className="text-sm text-gray-400">{task.source}</span>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p className="text-gray-400">No open tasks</p>
                    )}
                </div>

                {/* Pending Approvals */}
                <div className="glass-card">
                    <h2 className="text-lg font-semibold mb-4">⚡ Pending Approvals</h2>
                    {proposals?.length > 0 ? (
                        <div className="space-y-2">
                            {proposals.slice(0, 5).map(proposal => (
                                <div key={proposal.id} className="p-3 bg-background rounded-lg">
                                    <div className="flex justify-between items-start">
                                        <div>
                                            <span className="font-medium">{proposal.intent_type}</span>
                                            <p className="text-sm text-gray-400">
                                                Confidence: {(proposal.confidence * 100).toFixed(0)}%
                                            </p>
                                        </div>
                                        <div className="flex gap-2">
                                            <button className="btn btn-sm btn-primary">Approve</button>
                                            <button className="btn btn-sm btn-secondary">Reject</button>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p className="text-gray-400">No pending approvals</p>
                    )}
                </div>
            </div>
        </div>
    )
}

function StatCard({ icon, label, value, color }) {
    const colors = {
        green: 'from-green-500/20 to-green-600/10',
        blue: 'from-blue-500/20 to-blue-600/10',
        orange: 'from-orange-500/20 to-orange-600/10',
        red: 'from-red-500/20 to-red-600/10',
    }

    return (
        <div className={`stat-card bg-gradient-to-br ${colors[color]}`}>
            <div className="text-3xl mb-2">{icon}</div>
            <div className="text-3xl font-bold">{value}</div>
            <div className="text-sm text-gray-400">{label}</div>
        </div>
    )
}

// ============================================================================
// Devices Page
// ============================================================================
function Devices() {
    const { fetchApi } = useApi()
    const [activeTab, setActiveTab] = useState('cameras')

    const { data: devices, isLoading } = useQuery({
        queryKey: ['devices'],
        queryFn: () => fetchApi('/api/devices'),
    })

    const tabs = ['cameras', 'nvr', 'iot', 'thingsboard']

    return (
        <div className="fade-in">
            <h1 className="text-2xl font-bold mb-6">📹 Devices</h1>

            {/* Tabs */}
            <div className="flex gap-2 mb-6">
                {tabs.map(tab => (
                    <button
                        key={tab}
                        className={`px-4 py-2 rounded-lg capitalize ${activeTab === tab
                                ? 'bg-primary text-white'
                                : 'bg-background-card text-gray-400 hover:bg-background-hover'
                            }`}
                        onClick={() => setActiveTab(tab)}
                    >
                        {tab}
                    </button>
                ))}
            </div>

            <div className="glass-card">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-lg font-semibold capitalize">{activeTab}</h2>
                    <button className="btn btn-primary">+ Add {activeTab.slice(0, -1)}</button>
                </div>

                {isLoading ? (
                    <p className="text-gray-400">Loading...</p>
                ) : devices?.items?.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {devices.items.map(device => (
                            <div key={device.id} className="p-4 bg-background rounded-lg border border-border">
                                <div className="flex justify-between items-start mb-2">
                                    <span className="font-medium">{device.name}</span>
                                    <span className={`badge ${device.status === 'online' ? 'badge-success' : 'badge-danger'}`}>
                                        {device.status}
                                    </span>
                                </div>
                                <p className="text-sm text-gray-400">{device.location || 'No location'}</p>
                                <p className="text-xs text-gray-500 mt-2">Type: {device.type}</p>
                            </div>
                        ))}
                    </div>
                ) : (
                    <p className="text-gray-400">No {activeTab} found. Click "Add" to add one.</p>
                )}
            </div>
        </div>
    )
}

// ============================================================================
// Tasks Page
// ============================================================================
function Tasks() {
    const { fetchApi } = useApi()
    const queryClient = useQueryClient()

    const { data: tasks, isLoading } = useQuery({
        queryKey: ['tasks'],
        queryFn: () => fetchApi('/api/ops/tasks'),
    })

    const completeMutation = useMutation({
        mutationFn: (taskId) => fetchApi(`/api/ops/tasks/${taskId}/complete`, { method: 'POST' }),
        onSuccess: () => queryClient.invalidateQueries(['tasks']),
    })

    return (
        <div className="fade-in">
            <h1 className="text-2xl font-bold mb-6">📋 Tasks</h1>
            <div className="glass-card">
                <table className="data-table">
                    <thead>
                        <tr>
                            <th>Priority</th>
                            <th>Task</th>
                            <th>Source</th>
                            <th>Status</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {isLoading ? (
                            <tr><td colSpan="5" className="text-center text-gray-400">Loading...</td></tr>
                        ) : tasks?.length > 0 ? (
                            tasks.map(task => (
                                <tr key={task.id}>
                                    <td>
                                        <span className={`badge badge-${task.priority <= 2 ? 'danger' : task.priority <= 3 ? 'warning' : 'info'}`}>
                                            {task.priority <= 2 ? 'High' : task.priority <= 3 ? 'Medium' : 'Low'}
                                        </span>
                                    </td>
                                    <td>{task.title}</td>
                                    <td><span className="capitalize">{task.source}</span></td>
                                    <td><span className="capitalize">{task.status}</span></td>
                                    <td>
                                        {task.status === 'open' && (
                                            <button
                                                className="btn btn-sm btn-secondary"
                                                onClick={() => completeMutation.mutate(task.id)}
                                                disabled={completeMutation.isPending}
                                            >
                                                Complete
                                            </button>
                                        )}
                                    </td>
                                </tr>
                            ))
                        ) : (
                            <tr><td colSpan="5" className="text-center text-gray-400">No tasks</td></tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    )
}

// ============================================================================
// Rules Page
// ============================================================================
function Rules() {
    const { fetchApi } = useApi()
    const queryClient = useQueryClient()

    const { data: proposals } = useQuery({
        queryKey: ['proposals'],
        queryFn: () => fetchApi('/api/ops/rules/proposals'),
    })

    const approveMutation = useMutation({
        mutationFn: (id) => fetchApi(`/api/ops/rules/proposals/${id}/approve`, { method: 'POST' }),
        onSuccess: () => queryClient.invalidateQueries(['proposals']),
    })

    const rejectMutation = useMutation({
        mutationFn: (id) => fetchApi(`/api/ops/rules/proposals/${id}/reject`, { method: 'POST' }),
        onSuccess: () => queryClient.invalidateQueries(['proposals']),
    })

    return (
        <div className="fade-in">
            <h1 className="text-2xl font-bold mb-6">⚡ AI Rules & Approvals</h1>

            <div className="glass-card">
                <h3 className="text-lg font-semibold mb-4">Pending Proposals</h3>
                {proposals?.filter(p => p.status === 'pending').length > 0 ? (
                    <div className="space-y-4">
                        {proposals.filter(p => p.status === 'pending').map(proposal => (
                            <div key={proposal.id} className="p-4 bg-background rounded-lg border-l-4 border-primary">
                                <div className="flex justify-between items-start">
                                    <div>
                                        <h4 className="font-medium mb-2">🤖 {proposal.intent_type}</h4>
                                        <p className="text-sm text-gray-400 mb-2">
                                            {JSON.stringify(proposal.proposed_rule)}
                                        </p>
                                        <p className="text-sm text-primary">
                                            Confidence: {(proposal.confidence * 100).toFixed(0)}%
                                        </p>
                                    </div>
                                    <div className="flex gap-2">
                                        <button
                                            className="btn btn-primary"
                                            onClick={() => approveMutation.mutate(proposal.id)}
                                            disabled={approveMutation.isPending}
                                        >
                                            Approve
                                        </button>
                                        <button
                                            className="btn btn-secondary"
                                            onClick={() => rejectMutation.mutate(proposal.id)}
                                            disabled={rejectMutation.isPending}
                                        >
                                            Reject
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <p className="text-gray-400">No pending proposals</p>
                )}
            </div>
        </div>
    )
}

// ============================================================================
// Reports Page
// ============================================================================
function Reports() {
    const { fetchApi } = useApi()

    const { data: reports, isLoading } = useQuery({
        queryKey: ['reports'],
        queryFn: () => fetchApi('/api/report/reports'),
    })

    const generateMutation = useMutation({
        mutationFn: (type) => fetchApi('/api/report/generate', {
            method: 'POST',
            body: JSON.stringify({ type, format: 'pdf' })
        }),
    })

    return (
        <div className="fade-in">
            <h1 className="text-2xl font-bold mb-6">📊 Reports</h1>

            <div className="glass-card mb-6">
                <h3 className="text-lg font-semibold mb-4">Generate Report</h3>
                <div className="flex gap-2">
                    <button
                        className="btn btn-primary"
                        onClick={() => generateMutation.mutate('daily')}
                        disabled={generateMutation.isPending}
                    >
                        Daily Report
                    </button>
                    <button
                        className="btn btn-secondary"
                        onClick={() => generateMutation.mutate('weekly')}
                        disabled={generateMutation.isPending}
                    >
                        Weekly Report
                    </button>
                    <button
                        className="btn btn-secondary"
                        onClick={() => generateMutation.mutate('monthly')}
                        disabled={generateMutation.isPending}
                    >
                        Monthly Report
                    </button>
                </div>
            </div>

            <div className="glass-card">
                <h3 className="text-lg font-semibold mb-4">Generated Reports</h3>
                {isLoading ? (
                    <p className="text-gray-400">Loading...</p>
                ) : reports?.length > 0 ? (
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Type</th>
                                <th>Status</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {reports.map(report => (
                                <tr key={report.id}>
                                    <td>{new Date(report.created_at).toLocaleDateString()}</td>
                                    <td>{report.format?.toUpperCase()}</td>
                                    <td><span className="badge badge-success">{report.status}</span></td>
                                    <td>
                                        {report.status === 'ready' && (
                                            <button className="btn btn-sm btn-primary">Download</button>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                ) : (
                    <p className="text-gray-400">No reports generated yet</p>
                )}
            </div>
        </div>
    )
}

// ============================================================================
// Settings Page
// ============================================================================
function Settings() {
    const { fetchApi } = useApi()
    const queryClient = useQueryClient()

    const { data: settings } = useQuery({
        queryKey: ['settings'],
        queryFn: () => fetchApi('/api/settings'),
    })

    const [aiSettings, setAiSettings] = useState({
        ai_rule_creation: 'suggest_only',
        max_daily_rule_changes: 3,
    })

    useEffect(() => {
        if (settings) {
            setAiSettings({
                ai_rule_creation: settings.ai_rule_creation,
                max_daily_rule_changes: settings.max_daily_rule_changes,
            })
        }
    }, [settings])

    const saveMutation = useMutation({
        mutationFn: () => fetchApi('/api/settings/ai', {
            method: 'POST',
            body: JSON.stringify(aiSettings)
        }),
        onSuccess: () => queryClient.invalidateQueries(['settings']),
    })

    return (
        <div className="fade-in">
            <h1 className="text-2xl font-bold mb-6">⚙️ Settings</h1>

            <div className="glass-card max-w-2xl">
                <h3 className="text-lg font-semibold mb-6">AI Governance</h3>

                <div className="space-y-4">
                    <div>
                        <label className="block text-sm text-gray-400 mb-2">AI Rule Creation</label>
                        <select
                            className="input w-full"
                            value={aiSettings.ai_rule_creation}
                            onChange={(e) => setAiSettings({ ...aiSettings, ai_rule_creation: e.target.value })}
                        >
                            <option value="suggest_only">Suggest Only (Requires Approval)</option>
                            <option value="allow">Allow Auto-Activation</option>
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm text-gray-400 mb-2">Max Daily Rule Changes</label>
                        <input
                            type="number"
                            className="input w-full"
                            value={aiSettings.max_daily_rule_changes}
                            onChange={(e) => setAiSettings({ ...aiSettings, max_daily_rule_changes: parseInt(e.target.value) })}
                        />
                    </div>

                    <button
                        className="btn btn-primary"
                        onClick={() => saveMutation.mutate()}
                        disabled={saveMutation.isPending}
                    >
                        {saveMutation.isPending ? 'Saving...' : 'Save Settings'}
                    </button>
                </div>
            </div>
        </div>
    )
}

// ============================================================================
// Audit Logs Page
// ============================================================================
function AuditLogs() {
    const { fetchApi } = useApi()

    const { data: logs, isLoading } = useQuery({
        queryKey: ['audit'],
        queryFn: () => fetchApi('/api/audit?limit=50'),
    })

    return (
        <div className="fade-in">
            <h1 className="text-2xl font-bold mb-6">📜 Audit Logs</h1>

            <div className="glass-card">
                <table className="data-table">
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Actor</th>
                            <th>Action</th>
                            <th>Target</th>
                            <th>Details</th>
                        </tr>
                    </thead>
                    <tbody>
                        {isLoading ? (
                            <tr><td colSpan="5" className="text-center text-gray-400">Loading...</td></tr>
                        ) : logs?.length > 0 ? (
                            logs.map(log => (
                                <tr key={log.id}>
                                    <td>{new Date(log.occurred_at).toLocaleString()}</td>
                                    <td>
                                        <span className="capitalize">{log.actor_type}</span>
                                        {log.actor_id && <span className="text-gray-500 text-sm ml-1">({log.actor_id.substring(0, 8)}...)</span>}
                                    </td>
                                    <td><span className="font-mono text-sm">{log.action}</span></td>
                                    <td>{log.target_type}</td>
                                    <td>
                                        {log.reason && <span className="text-sm text-gray-400">{log.reason}</span>}
                                        {log.confidence && <span className="badge badge-info ml-2">{(log.confidence * 100).toFixed(0)}%</span>}
                                    </td>
                                </tr>
                            ))
                        ) : (
                            <tr><td colSpan="5" className="text-center text-gray-400">No audit logs</td></tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    )
}

// ============================================================================
// Sidebar Navigation
// ============================================================================
function Sidebar({ user, onLogout }) {
    const location = useLocation()

    const navItems = [
        { path: '/portal/', icon: '🏠', label: 'Dashboard' },
        { path: '/portal/devices', icon: '📹', label: 'Devices' },
        { path: '/portal/tasks', icon: '📋', label: 'Tasks' },
        { path: '/portal/rules', icon: '⚡', label: 'AI Rules' },
        { path: '/portal/reports', icon: '📊', label: 'Reports' },
        { path: '/portal/settings', icon: '⚙️', label: 'Settings' },
        { path: '/portal/audit', icon: '📜', label: 'Audit Logs' }
    ]

    return (
        <aside className="sidebar">
            <div className="logo">
                <div className="logo-icon">🌱</div>
                <span className="logo-text">AFASA</span>
            </div>

            <nav>
                <ul className="nav-menu">
                    {navItems.map(item => (
                        <li className="nav-item" key={item.path}>
                            <Link
                                to={item.path}
                                className={`nav-link ${location.pathname === item.path ? 'active' : ''}`}
                            >
                                <span>{item.icon}</span>
                                <span>{item.label}</span>
                            </Link>
                        </li>
                    ))}
                </ul>
            </nav>

            <div className="mt-auto pt-6 border-t border-border">
                <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-full bg-primary flex items-center justify-center font-semibold">
                        {user?.profile?.email?.[0]?.toUpperCase() || '?'}
                    </div>
                    <div>
                        <div className="font-medium text-sm">{user?.profile?.email || 'User'}</div>
                        <div className="text-xs text-gray-400">Tenant Admin</div>
                    </div>
                </div>
                <button className="btn btn-secondary w-full" onClick={onLogout}>
                    Logout
                </button>
            </div>
        </aside>
    )
}

// ============================================================================
// Login Page
// ============================================================================
function LoginPage({ onLogin }) {
    return (
        <div className="login-container">
            <div className="login-card fade-in">
                <div className="login-logo">🌱</div>
                <h1 className="login-title">AFASA 2.0</h1>
                <p className="login-subtitle">AI-Powered Agricultural Monitoring</p>
                <button className="btn btn-primary w-full" onClick={onLogin}>
                    Sign In with Keycloak
                </button>
            </div>
        </div>
    )
}

// ============================================================================
// Main App
// ============================================================================
function AppContent() {
    const auth = useAuth()

    if (auth.isLoading) {
        return (
            <div className="login-container">
                <div className="login-card">
                    <div className="login-logo animate-pulse">🌱</div>
                    <p className="text-gray-400">Loading...</p>
                </div>
            </div>
        )
    }

    if (!auth.isAuthenticated) {
        return <LoginPage onLogin={() => auth.signinRedirect()} />
    }

    return (
        <BrowserRouter>
            <div className="app-container">
                <Sidebar user={auth.user} onLogout={() => auth.signoutRedirect()} />
                <main className="main-content">
                    <Routes>
                        <Route path="/portal/" element={<Dashboard />} />
                        <Route path="/portal/devices" element={<Devices />} />
                        <Route path="/portal/tasks" element={<Tasks />} />
                        <Route path="/portal/rules" element={<Rules />} />
                        <Route path="/portal/reports" element={<Reports />} />
                        <Route path="/portal/settings" element={<Settings />} />
                        <Route path="/portal/audit" element={<AuditLogs />} />
                        <Route path="/portal/*" element={<Dashboard />} />
                    </Routes>
                </main>
            </div>
        </BrowserRouter>
    )
}

function App() {
    return (
        <QueryClientProvider client={queryClient}>
            <AppContent />
        </QueryClientProvider>
    )
}

export default App
