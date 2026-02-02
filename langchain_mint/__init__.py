"""
LangChain MINT Integration
==========================
Earn MINT tokens for LangChain agent execution via FoundryNet.

Usage (Middleware - recommended for v1):
    from langchain_mint import MintMiddleware
    
    middleware = MintMiddleware(keypair_path="~/.config/solana/id.json")
    agent = AgentExecutor(..., middleware=[middleware])

Usage (Callback - legacy):
    from langchain_mint import MintCallback
    
    callback = MintCallback(keypair_path="~/.config/solana/id.json")
    agent = AgentExecutor(..., callbacks=[callback])

Links:
    - GitHub: https://github.com/FoundryNet/langchain-mint
    - Dashboard: https://foundrynet.github.io/foundry_net_MINT/
"""

from .middleware import MintMiddleware
from .callback import MintCallback, with_mint

__version__ = "2.0.0"
__all__ = ["MintMiddleware", "MintCallback", "with_mint"]
