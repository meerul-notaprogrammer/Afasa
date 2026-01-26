# Phase 5: Personal Web App (Thin Control Plane)

> **Status**: FINAL PHASE - FRONTEND
> **Prerequisite**: Phase 4 complete (all backend systems working)
> **Duration**: 2-3 weeks

---

## Objective

Build the farmer-facing portal as a **thin control-plane UI**. ThingsBoard remains the primary visualization layer. The portal embeds TB dashboards and adds AFASA-specific widgets for AI context, approvals, and onboarding.

---

## Non-Negotiables

❌ **DO NOT:**
- Rebuild TB charts/widgets in React
- Stream RTSP in the browser directly
- Store camera credentials in frontend
- Embed TB admin sessions

✅ **DO:**
- Embed TB dashboards via short-lived tokens
- Show AFASA-specific context (AI assessments, approvals)
- Provide device management UI
- Handle settings and configuration

---

## Build Order

| Order | Component | Description |
|-------|-----------|-------------|
| 1 | Auth + App Shell | Keycloak login + layout |
| 2 | Main Dashboard | TB embed + galleries + tasks |
| 3 | Devices | Camera/NVR/IoT management |
| 4 | Rules & Approvals | Governance UI |
| 5 | Settings | Retention, alerts, AI policy |
| 6 | Reports | List + download |
| 7 | Audit Logs | View + filter |

---

## 1) Project Setup

### Tech Stack
```json
{
  "build": "Vite",
  "framework": "React",
  "routing": "React Router",
  "data": "TanStack Query",
  "styling": "Tailwind CSS",
  "auth": "Keycloak JS"
}
```

### Project Structure
```
services/portal/
├── Dockerfile
├── nginx.conf
├── package.json
├── vite.config.ts
├── tailwind.config.js
├── index.html
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── auth/
│   │   ├── keycloak.ts
│   │   └── AuthProvider.tsx
│   ├── api/
│   │   ├── client.ts
│   │   └── hooks/
│   │       ├── useMe.ts
│   │       ├── useSnapshots.ts
│   │       ├── useTasks.ts
│   │       └── ...
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppShell.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── TopBar.tsx
│   │   ├── ui/
│   │   │   ├── Button.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Toast.tsx
│   │   │   └── ...
│   │   └── widgets/
│   │       ├── TBEmbed.tsx
│   │       ├── SnapshotCard.tsx
│   │       ├── TaskCard.tsx
│   │       └── ApprovalCard.tsx
│   └── pages/
│       ├── Dashboard.tsx
│       ├── Devices.tsx
│       ├── Rules.tsx
│       ├── Tasks.tsx
│       ├── Reports.tsx
│       ├── Settings.tsx
│       └── AuditLogs.tsx
```

---

## 2) Authentication (Step 1)

### Keycloak Configuration

```typescript
// src/auth/keycloak.ts
import Keycloak from 'keycloak-js';

export const keycloak = new Keycloak({
  url: import.meta.env.VITE_OIDC_ISSUER_URL,
  realm: 'afasa',
  clientId: import.meta.env.VITE_OIDC_CLIENT_ID,
});

export async function initAuth() {
  const authenticated = await keycloak.init({
    onLoad: 'login-required',
    pkceMethod: 'S256',
    checkLoginIframe: false,
  });
  
  return authenticated;
}

export function getToken(): string | undefined {
  return keycloak.token;
}

export function getTenantId(): string | undefined {
  const parsed = keycloak.tokenParsed as { tenant_id?: string };
  return parsed?.tenant_id;
}
```

### Auth Provider

```typescript
// src/auth/AuthProvider.tsx
import { createContext, useContext, useEffect, useState } from 'react';
import { keycloak, initAuth } from './keycloak';

interface AuthContext {
  isAuthenticated: boolean;
  tenantId: string | null;
  token: string | null;
  logout: () => void;
}

const AuthContext = createContext<AuthContext | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [tenantId, setTenantId] = useState<string | null>(null);
  
  useEffect(() => {
    initAuth().then((authenticated) => {
      setIsAuthenticated(authenticated);
      if (authenticated) {
        setTenantId((keycloak.tokenParsed as any)?.tenant_id);
      }
    });
  }, []);
  
  if (!isAuthenticated) {
    return <div>Loading...</div>;
  }
  
  return (
    <AuthContext.Provider value={{
      isAuthenticated,
      tenantId,
      token: keycloak.token ?? null,
      logout: () => keycloak.logout(),
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext)!;
```

---

## 3) App Shell Layout (Step 1)

### Design
```
┌─────────────────────────────────────────────────────┐
│  [🌱 AFASA]  [Tenant Name]  [━━▓░░░]  [🔍]  [👤▾]  │
├───────┬─────────────────────────────────────────────┤
│       │                                             │
│  📊   │          MAIN CONTENT AREA                  │
│  🎥   │                                             │
│  ⚙️   │          (React Router Outlet)              │
│  📋   │                                             │
│  📁   │                                             │
│  🔧   │                                             │
│  📜   │                                             │
│       │                                             │
└───────┴─────────────────────────────────────────────┘
```

### Implementation

```typescript
// src/components/layout/AppShell.tsx
export function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  
  return (
    <div className="min-h-screen bg-gray-900">
      <TopBar onMenuClick={() => setSidebarOpen(!sidebarOpen)} />
      
      <Sidebar 
        isOpen={sidebarOpen} 
        onClose={() => setSidebarOpen(false)} 
      />
      
      <main className="lg:pl-64 pt-16">
        <div className="p-6">
          <Outlet />
        </div>
      </main>
      
      <Toaster />
    </div>
  );
}
```

---

## 4) Main Dashboard (Step 2)

### Sections

| Section | Component | API |
|---------|-----------|-----|
| A | TB Embed (Primary) | `POST /api/tb/embed-token` |
| B | Live Views (Optional) | MediaMTX HLS |
| C | AI Panel | `GET /api/assessments/latest` |
| D | Snapshot Gallery | `GET /api/snapshots` |
| E | Tasks | `GET /api/tasks?status=open` |
| F | Pending Approvals | `GET /api/rule-proposals?status=pending` |

### TB Embed Component

```typescript
// src/components/widgets/TBEmbed.tsx
export function TBEmbed() {
  const { data, isLoading } = useEmbedToken();
  
  if (isLoading) return <Skeleton className="h-96" />;
  
  return (
    <div className="rounded-lg overflow-hidden border border-gray-700">
      <iframe
        src={data?.url}
        className="w-full h-96"
        title="ThingsBoard Dashboard"
        sandbox="allow-scripts allow-same-origin"
      />
    </div>
  );
}
```

### Dashboard Page

```typescript
// src/pages/Dashboard.tsx
export function Dashboard() {
  return (
    <div className="space-y-6">
      {/* Section A: ThingsBoard */}
      <Card>
        <CardHeader>
          <CardTitle>Farm Overview</CardTitle>
        </CardHeader>
        <CardContent>
          <TBEmbed />
        </CardContent>
      </Card>
      
      {/* Grid: Snapshots, Tasks, Approvals */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <SnapshotGallery />
        <TaskList />
        <PendingApprovals />
      </div>
      
      {/* AI Panel */}
      <AIAssessmentPanel />
    </div>
  );
}
```

---

## 5) Devices Page (Step 3)

### Tabs
- Cameras
- NVRs
- IoT (UbiBot)
- ThingsBoard

### Camera Add Wizard

```typescript
// src/pages/Devices/AddCameraModal.tsx
export function AddCameraModal() {
  const [mode, setMode] = useState<'nvr' | 'single'>('single');
  
  return (
    <Dialog>
      <DialogContent>
        <Tabs value={mode} onValueChange={setMode}>
          <TabsList>
            <TabsTrigger value="single">Single Camera</TabsTrigger>
            <TabsTrigger value="nvr">I have NVR</TabsTrigger>
          </TabsList>
          
          <TabsContent value="single">
            <SingleCameraForm />
          </TabsContent>
          
          <TabsContent value="nvr">
            <NVRForm />
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
```

---

## 6) Rules & Approvals (Step 4)

### Rule Proposal Card

```typescript
// src/components/widgets/ApprovalCard.tsx
export function ApprovalCard({ proposal }: { proposal: RuleProposal }) {
  const approveMutation = useApproveProposal();
  const rejectMutation = useRejectProposal();
  
  return (
    <Card className={cn(
      "border-l-4",
      proposal.safety_classification === 'safe' 
        ? "border-l-green-500" 
        : "border-l-amber-500"
    )}>
      <CardHeader>
        <div className="flex items-center gap-2">
          <RobotIcon className="text-blue-400" />
          <CardTitle>{proposal.name}</CardTitle>
        </div>
      </CardHeader>
      
      <CardContent>
        <p className="text-gray-400 mb-4">{proposal.reason}</p>
        
        <div className="flex gap-4 text-sm">
          <span>Confidence: {(proposal.confidence * 100).toFixed(0)}%</span>
          <span>Target: {proposal.target_device?.name}</span>
        </div>
      </CardContent>
      
      <CardFooter className="flex gap-2">
        <Button 
          variant="outline" 
          onClick={() => rejectMutation.mutate({ id: proposal.id })}
        >
          Reject
        </Button>
        <Button 
          onClick={() => approveMutation.mutate({ id: proposal.id })}
        >
          Approve
        </Button>
      </CardFooter>
    </Card>
  );
}
```

---

## 7) Settings (Step 5)

### Sections
- AI Behavior
- Retention
- Alerts
- Integrations
- Security

### Implementation

```typescript
// src/pages/Settings.tsx
export function Settings() {
  return (
    <div className="max-w-2xl space-y-8">
      <AISettings />
      <RetentionSettings />
      <AlertSettings />
      <IntegrationSettings />
      <SecuritySettings />
    </div>
  );
}
```

---

## 8) Design System

### Colors (Tailwind)

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#10B981',
          dark: '#059669',
        },
        accent: '#F59E0B',
        danger: '#EF4444',
        background: {
          DEFAULT: '#111827',
          card: '#1F2937',
        },
      },
    },
  },
};
```

### Typography

```css
/* src/index.css */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

body {
  font-family: 'Inter', sans-serif;
}
```

---

## Verification Checklist

| # | Criterion | Status |
|---|-----------|--------|
| 5.1 | Login via Keycloak works | ⬜ |
| 5.2 | User lands on dashboard without tenant select | ⬜ |
| 5.3 | App shell renders correctly | ⬜ |
| 5.4 | TB dashboard embeds correctly | ⬜ |
| 5.5 | Snapshot gallery shows latest | ⬜ |
| 5.6 | Tasks section visible | ⬜ |
| 5.7 | Pending approvals visible | ⬜ |
| 5.8 | Device list loads | ⬜ |
| 5.9 | Camera can be added | ⬜ |
| 5.10 | UbiBot can be connected | ⬜ |
| 5.11 | Rules list loads | ⬜ |
| 5.12 | Approve/reject works | ⬜ |
| 5.13 | Settings persist | ⬜ |
| 5.14 | Reports downloadable | ⬜ |
| 5.15 | Audit logs visible | ⬜ |

**FAIL if:** Frontend reimplements ThingsBoard dashboards.

---

## Deliverables

1. Complete portal with all pages
2. Keycloak authentication working
3. API integration via TanStack Query
4. Responsive design (mobile-friendly)
5. Premium "Tactical Industrial" aesthetic

---

## References

- [Frontend Specification](../FRONTEND_SPEC.md)
- [API Contract](../API_CONTRACT.md)
- [MVP Acceptance Checklist](../MVP_ACCEPTANCE_CHECKLIST.md) - Phase 4 criteria
