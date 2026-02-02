"""
LangChain MINT Integration
==========================
Earn MINT tokens for LangChain agent execution via FoundryNet.

Your agents work. Your agents earn.

Usage:
    from langchain_mint import MintCallback
    
    callback = MintCallback(keypair_path="~/.config/solana/id.json")
    agent = AgentExecutor(..., callbacks=[callback])
    
    # Or wrap any chain:
    from langchain_mint import with_mint
    chain = with_mint(my_chain, keypair_path="...")

Links:
    - GitHub: https://github.com/foundrynet
    - Dashboard: https://foundrynet.github.io/foundry_net_MINT/
"""

from .callback import MintCallback, with_mint

__version__ = "1.0.0"
__all__ = ["MintCallback", "with_mint"]
