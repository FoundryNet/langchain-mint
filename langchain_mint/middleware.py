"""
LangChain MINT Middleware
=========================
Earn MINT tokens for LangChain agent execution via FoundryNet.

Uses Agent Middleware pattern (langchain v1 semantics).

Usage:
    from langchain_mint import MintMiddleware
    from langchain.agents import AgentExecutor
    
    middleware = MintMiddleware(keypair_path="~/.config/solana/id.json")
    
    agent = AgentExecutor(
        agent=my_agent,
        tools=my_tools,
        middleware=[middleware]
    )
"""

import time
import json
import hashlib
from typing import Any, Dict, Optional
from pathlib import Path
from dataclasses import dataclass, field

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

# Anchor discriminator for record_job (snake_case)
RECORD_JOB_DISCRIMINATOR = bytes([54, 124, 168, 158, 236, 237, 107, 206])


@dataclass
class MintMiddleware:
    """
    LangChain Agent Middleware that settles MINT for agent execution.
    
    Tracks execution time via before_agent/after_agent hooks and
    settles MINT tokens on the FoundryNet protocol.
    """
    
    keypair_path: Optional[str] = None
    keypair_bytes: Optional[bytes] = None
    rpc_endpoint: str = DEFAULT_RPC
    complexity: int = 1000
    job_name: Optional[str] = None
    min_duration: int = 1
    verbose: bool = True
    
    _start_time: Optional[float] = field(default=None, init=False, repr=False)
    _keypair: Optional[Keypair] = field(default=None, init=False, repr=False)
    _client: Optional[Client] = field(default=None, init=False, repr=False)
    
    def __post_init__(self):
        """Initialize keypair and RPC client."""
        self._client = Client(self.rpc_endpoint)
        
        if self.keypair_path:
            with open(Path(self.keypair_path).expanduser(), "r") as f:
                data = json.load(f)
            self._keypair = Keypair.from_bytes(bytes(data))
        elif self.keypair_bytes:
            self._keypair = Keypair.from_bytes(self.keypair_bytes)
        else:
            raise ValueError("Must provide keypair_path or keypair_bytes")
        
        if self.verbose:
            print(f"[MINT] Middleware initialized: {self._keypair.pubkey()}")
    
    def before_agent(self, input: Dict[str, Any]) -> Dict[str, Any]:
        """Called before agent execution. Starts the timer."""
        self._start_time = time.time()
        if self.verbose:
            print(f"[MINT] Agent started")
        return input
    
    def after_agent(self, input: Dict[str, Any], output: Dict[str, Any]) -> Dict[str, Any]:
        """Called after agent execution. Settles MINT tokens."""
        if self._start_time is None:
            return output
        
        duration = int(time.time() - self._start_time)
        self._start_time = None
        
        if duration < self.min_duration:
            if self.verbose:
                print(f"[MINT] Skipping (duration {duration}s < {self.min_duration}s min)")
            return output
        
        self._settle(duration)
        return output
    
    def _settle(self, duration: int):
        """Record job on-chain and earn MINT."""
        try:
            job_name = self.job_name or f"langchain-agent-{int(time.time())}"
            job_hash = self._generate_job_hash(job_name, duration)
            
            tx = self._build_record_job_tx(job_hash, duration, self.complexity)
            signature = self._client.send_transaction(tx, self._keypair).value
            
            base_reward = duration * 0.005 * (self.complexity / 1000)
            
            if self.verbose:
                print(f"[MINT] ✓ Settled ~{base_reward:.3f} MINT ({duration}s)")
                print(f"[MINT]   TX: https://solscan.io/tx/{signature}")
                
        except Exception as e:
            if self.verbose:
                print(f"[MINT] Settlement failed: {e}")
    
    def _generate_job_hash(self, job_name: str, duration: int) -> str:
        data = f"{job_name}-{time.time()}-{duration}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]
    
    def _build_record_job_tx(self, job_hash: str, duration: int, complexity: int) -> Transaction:
        machine_pda, _ = PublicKey.find_program_address(
            [b"machine", bytes(self._keypair.pubkey())],
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
            AccountMeta(self._keypair.pubkey(), is_signer=True, is_writable=False),
            AccountMeta(self._keypair.pubkey(), is_signer=True, is_writable=True),
            AccountMeta(SYS_PROGRAM_ID, is_signer=False, is_writable=False),
        ]
        
        ix = Instruction(MINT_PROGRAM_ID, bytes(data), accounts)
        recent_blockhash = self._client.get_latest_blockhash().value.blockhash
        
        tx = Transaction.new_signed_with_payer(
            [ix],
            self._keypair.pubkey(),
            [self._keypair],
            recent_blockhash
        )
        
        return tx
