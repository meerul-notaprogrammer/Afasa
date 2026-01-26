"""
AFASA 2.0 - JWT Authentication Middleware
Validates Keycloak tokens and extracts tenant_id
"""
import httpx
from jose import jwt, JWTError
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from functools import lru_cache
from typing import Optional
from pydantic import BaseModel

from .settings import get_settings

security = HTTPBearer()


class TokenPayload(BaseModel):
    sub: str
    tenant_id: str
    email: Optional[str] = None
    realm_access: Optional[dict] = None
    
    @property
    def roles(self) -> list[str]:
        if self.realm_access and "roles" in self.realm_access:
            return self.realm_access["roles"]
        return []
    
    def has_role(self, role: str) -> bool:
        return role in self.roles


_jwks_cache: Optional[dict] = None


async def get_jwks() -> dict:
    """Fetch JWKS from Keycloak (cached)"""
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache
    
    settings = get_settings()
    jwks_url = f"{settings.oidc_issuer_url}/protocol/openid-connect/certs"
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(jwks_url, timeout=10.0)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        return _jwks_cache


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenPayload:
    """Verify JWT and extract claims"""
    settings = get_settings()
    token = credentials.credentials
    
    try:
        jwks = await get_jwks()
        
        # Decode header to get kid
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        
        # Find matching key
        rsa_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                rsa_key = key
                break
        
        if not rsa_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find matching key"
            )
        
        # Verify token
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=settings.oidc_audience,
            issuer=settings.oidc_issuer_url
        )
        
        # Extract tenant_id
        tenant_id = payload.get("tenant_id")
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing tenant_id claim"
            )
        
        return TokenPayload(
            sub=payload.get("sub", ""),
            tenant_id=tenant_id,
            email=payload.get("email"),
            realm_access=payload.get("realm_access")
        )
    
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )


def require_role(role: str):
    """Dependency to require a specific role"""
    async def role_checker(token: TokenPayload = Depends(verify_token)):
        if not token.has_role(role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' required"
            )
        return token
    return role_checker
