"""
LangChain MINT Integration
==========================
Earn MINT tokens for LangChain agent execution via FoundryNet.

Your agents work. Your agents earn.

Usage:
    from langchain_mint import MintCallback
    from langchain.agents import AgentExecutor
    
    callback = MintCallback(keypair_path="~/.config/solana/id.json")
    
    agent = AgentExecutor(..., callbacks=[callback])
    agent.invoke({"input": "do something"})
    # MINT automatically settled on completion
    
    # Or wrap any chain/runnable:
    from langchain_mint import with_mint
    
    chain = with_mint(my_chain, keypair_path="...")
    chain.invoke(...)
"""

import time
import json
import hashlib
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from pathlib import Path

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_core.agents import AgentAction, AgentFinish

from solana.rpc.api import Client
from solders.transaction import Transaction
from solders.keypair import Keypair
from solders.pubkey import Pubkey as PublicKey
SYS_PROGRAM_ID = PublicKey.from_string("11111111111111111111111111111111")
from solders.instruction import Instruction, AccountMeta

# FoundryNet Mainnet
MINT_PROGRAM_ID = PublicKey.from_string("4ZvTZ3skfeMF3ZGyABoazPa9tiudw2QSwuVKn45t2AKL")
STATE_ACCOUNT = PublicKey.from_string("2Lm7hrtqK9W5tykVu4U37nUNJiiFh6WQ1rD8ZJWXomr2")
DEFAULT_RPC = "https://api.mainnet-beta.solana.com"

RECORD_JOB_DISCRIMINATOR = bytes([0x36, 0x7c, 0xa8, 0x9e, 0xec, 0xed, 0x6b, 0xce])


class MintCallback(BaseCallbackHandler):
    """
    LangChain callback handler that settles MINT for agent execution.
    
    Tracks execution time from chain/agent start to finish and
    settles MINT tokens on the FoundryNet protocol.
    """

    def __init__(
        self,
        keypair_path: Optional[str] = None,
        keypair_bytes: Optional[bytes] = None,
        rpc_endpoint: str = DEFAULT_RPC,
        complexity: int = 1000,
        job_name: Optional[str] = None,
        min_duration: int = 1,
        verbose: bool = True,
    ):
        """
        Initialize MINT callback.
        
        Args:
            keypair_path: Path to Solana keypair JSON file
            keypair_bytes: Raw keypair bytes (alternative to path)
            rpc_endpoint: Solana RPC endpoint
            complexity: Complexity multiplier (1000 = 1.0x)
            job_name: Custom job name (default: auto-generated)
            min_duration: Minimum duration in seconds to settle
            verbose: Print settlement info
        """
        super().__init__()
        
        self.client = Client(rpc_endpoint)
        self.complexity = complexity
        self.job_name = job_name
        self.min_duration = min_duration
        self.verbose = verbose
        
        self._start_time: Optional[float] = None
        self._run_id: Optional[str] = None
        
        # Load keypair
        if keypair_path:
            with open(Path(keypair_path).expanduser(), "r") as f:
                data = json.load(f)
            self.keypair = Keypair.from_bytes(bytes(data))
        elif keypair_bytes:
            self.keypair = Keypair.from_bytes(keypair_bytes)
        else:
            raise ValueError("Must provide keypair_path or keypair_bytes")
        
        if self.verbose:
            print(f"[MINT] Callback initialized: {self.keypair.pubkey()}")

    # ─────────────────────────────────────────────────────────────
    # Chain Callbacks
    # ─────────────────────────────────────────────────────────────

    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Record chain start time."""
        if parent_run_id is None:  # Only track top-level chains
            self._start_time = time.time()
            self._run_id = str(run_id)
            if self.verbose:
                print(f"[MINT] Chain started: {serialized.get('name', 'unknown')}")

    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Settle MINT on chain completion."""
        if parent_run_id is None and self._start_time:
            self._settle(success=True)

    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Settle MINT even on error (work was done)."""
        if parent_run_id is None and self._start_time:
            self._settle(success=False)

    # ─────────────────────────────────────────────────────────────
    # Agent Callbacks (alternative entry point)
    # ─────────────────────────────────────────────────────────────

    def on_agent_action(
        self,
        action: AgentAction,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Track agent actions (start time if not already set)."""
        if self._start_time is None:
            self._start_time = time.time()
            self._run_id = str(run_id)

    def on_agent_finish(
        self,
        finish: AgentFinish,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Settle MINT on agent finish."""
        if self._start_time:
            self._settle(success=True)

    # ─────────────────────────────────────────────────────────────
    # Settlement
    # ─────────────────────────────────────────────────────────────

    def _settle(self, success: bool = True):
        """Record job on-chain and earn MINT."""
        if not self._start_time:
            return
        
        duration = int(time.time() - self._start_time)
        self._start_time = None
        
        if duration < self.min_duration:
            if self.verbose:
                print(f"[MINT] Skipping (duration {duration}s < {self.min_duration}s min)")
            return
        
        try:
            job_name = self.job_name or f"langchain-{self._run_id[:8]}"
            job_hash = self._generate_job_hash(job_name, duration)
            
            tx = self._build_record_job_tx(job_hash, duration, self.complexity)
            signature = self.client.send_transaction(tx, self.keypair).value
            
            base_reward = duration * 0.005 * (self.complexity / 1000)
            
            if self.verbose:
                status = "✓" if success else "⚠"
                print(f"[MINT] {status} Settled ~{base_reward:.3f} MINT ({duration}s)")
                print(f"[MINT]   TX: https://solscan.io/tx/{signature}")
            
        except Exception as e:
            if self.verbose:
                print(f"[MINT] Settlement failed: {e}")

    def _generate_job_hash(self, job_name: str, duration: int) -> str:
        data = f"{job_name}-{time.time()}-{duration}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]

    def _build_record_job_tx(self, job_hash: str, duration: int, complexity: int) -> Transaction:
        machine_pda, _ = PublicKey.find_program_address(
            [b"machine", bytes(self.keypair.pubkey())],
            MINT_PROGRAM_ID
        )
        job_pda, _ = PublicKey.find_program_address(
            [b"job", job_hash.encode()],
            MINT_PROGRAM_ID
        )

        job_hash_bytes = job_hash.encode("utf-8")
        data = (
            RECORD_JOB_DISCRIMINATOR +
            len(job_hash_bytes).to_bytes(4, "little") +
            job_hash_bytes +
            duration.to_bytes(8, "little") +
            complexity.to_bytes(4, "little")
        )

        accounts = [
            AccountMeta(STATE_ACCOUNT, is_signer=False, is_writable=True),
            AccountMeta(machine_pda, is_signer=False, is_writable=True),
            AccountMeta(job_pda, is_signer=False, is_writable=True),
            AccountMeta(self.keypair.pubkey(), is_signer=True, is_writable=False),
            AccountMeta(self.keypair.pubkey(), is_signer=True, is_writable=True),
            AccountMeta(SYS_PROGRAM_ID, is_signer=False, is_writable=False),
        ]

        ix = Instruction(MINT_PROGRAM_ID, bytes(data), accounts)

        recent_blockhash = self.client.get_latest_blockhash().value.blockhash
        tx = Transaction.new_signed_with_payer(
            [ix],
            self.keypair.pubkey(),
            [self.keypair],
            recent_blockhash
        )

        return tx


# ─────────────────────────────────────────────────────────────────
# Convenience wrapper
# ─────────────────────────────────────────────────────────────────

def with_mint(
    runnable,
    keypair_path: Optional[str] = None,
    keypair_bytes: Optional[bytes] = None,
    complexity: int = 1000,
    **kwargs
):
    """
    Wrap any LangChain runnable with MINT settlement.
    
    Usage:
        chain = with_mint(my_chain, keypair_path="~/.config/solana/id.json")
        chain.invoke({"input": "hello"})
    """
    callback = MintCallback(
        keypair_path=keypair_path,
        keypair_bytes=keypair_bytes,
        complexity=complexity,
        **kwargs
    )
    return runnable.with_config(callbacks=[callback])
