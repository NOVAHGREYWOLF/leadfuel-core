"""chats-11: credentials the model never sees. Opaque handles over a local secret store.

The design is docs/CHATS-11_CREDENTIAL_HANDLES_DESIGN.md. Its go is the owner's; until then this
package is a draft with one backend for tests (`MemoryBackend`, fake values only) and an OS-vault
backend that refuses every call.
"""
from .handles import (
    ApprovalRequest,
    CredentialHandle,
    HandleBroker,
    MemoryBackend,
    OSVaultBackend,
    OutboundGuard,
    Receipt,
    Refused,
    SecretLeak,
    Target,
    agent_tools,
)

__all__ = [
    "ApprovalRequest",
    "CredentialHandle",
    "HandleBroker",
    "MemoryBackend",
    "OSVaultBackend",
    "OutboundGuard",
    "Receipt",
    "Refused",
    "SecretLeak",
    "Target",
    "agent_tools",
]
