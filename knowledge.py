"""Knowledge System client — every app reads + writes the ONE shared store at the hub.

The flywheel's physical home is the hub (``HUB_API_URL``): all knowledge entries
(docs/facts/learnings) and every uploaded document pull in there, scoped per customer.
A doc dropped in any app becomes knowledge for all of them.

Thin wrapper over ``service_client`` against the hub's knowledge endpoints. Entries are
typed (doc / fact / learning) and scoped (global, or to a specific ICP):

    from leadfuel_core import knowledge as K
    K.add_knowledge("cust@acme.com", "learning", "Replies fastest Tue mornings", scope="icp", icp_id=7)
    facts = K.get_knowledge("cust@acme.com", kind="fact")
"""
from __future__ import annotations

from . import service_client as SC

KINDS = ("doc", "fact", "learning")
SCOPES = ("global", "icp")


def get_knowledge(email: str, *, scope: str | None = None, kind: str | None = None,
                  icp_id=None, limit: int = 500) -> dict:
    """Read the customer's knowledge entries, optionally filtered by scope/kind/ICP."""
    return SC.call("hub", "/api/knowledge",
                   params={"email": email, "scope": scope, "kind": kind,
                           "icp_id": icp_id, "limit": limit})


def add_knowledge(email: str, kind: str, text: str, *, scope: str = "global",
                  icp_id=None, source: str | None = None) -> dict:
    """Write a typed, scoped knowledge entry. ``source`` records which app added it."""
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    return SC.call("hub", "/api/knowledge", method="POST",
                   body={"email": email, "kind": kind, "text": text,
                         "scope": scope, "icp_id": icp_id, "source": source})


def add_document(email: str, name: str, *, content: str | None = None, url: str | None = None,
                 scope: str = "global", icp_id=None, source: str | None = None) -> dict:
    """Pull a document into the hub's store (inline content or a URL reference)."""
    return SC.call("hub", "/api/documents", method="POST",
                   body={"email": email, "name": name, "content": content, "url": url,
                         "scope": scope, "icp_id": icp_id, "source": source})
