import React from 'react'
import ReactDOM from 'react-dom/client'
import { AuthProvider } from 'react-oidc-context'
import App from './App'
import './index.css'

const oidcConfig = {
    authority: import.meta.env.VITE_OIDC_ISSUER_URL || 'http://localhost:8080/realms/afasa',
    client_id: import.meta.env.VITE_OIDC_CLIENT_ID || 'afasa-portal',
    redirect_uri: window.location.origin + '/portal/',
    post_logout_redirect_uri: window.location.origin + '/portal/',
    scope: 'openid profile email',
    automaticSilentRenew: true
}

ReactDOM.createRoot(document.getElementById('root')).render(
    <React.StrictMode>
        <AuthProvider {...oidcConfig}>
            <App />
        </AuthProvider>
    </React.StrictMode>
)
