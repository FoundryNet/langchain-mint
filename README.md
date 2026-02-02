# langchain-mint

**Your agents work. Your agents earn.**

Earn MINT tokens for LangChain agent execution via [FoundryNet](https://github.com/foundrynet).

## Installation

```bash
pip install langchain-mint
```

## Usage

### Callback Handler

```python
from langchain_mint import MintCallback
from langchain.agents import AgentExecutor

callback = MintCallback(keypair_path="~/.config/solana/id.json")

agent = AgentExecutor(
    agent=my_agent,
    tools=my_tools,
    callbacks=[callback]  # Add MINT callback
)

result = agent.invoke({"input": "research topic X"})
# MINT automatically settled on completion
```

### Wrap Any Chain

```python
from langchain_mint import with_mint

chain = prompt | llm | parser

# Wrap with MINT settlement
mint_chain = with_mint(chain, keypair_path="~/.config/solana/id.json")

result = mint_chain.invoke({"topic": "AI agents"})
# MINT settled after chain completes
```

### Custom Complexity

```python
callback = MintCallback(
    keypair_path="~/.config/solana/id.json",
    complexity=1500,  # 1.5x multiplier for complex tasks
    job_name="research-agent",
)
```

## Earnings

| Agent Runtime | ~MINT Earned |
|---------------|--------------|
| 30 seconds | 0.15 MINT |
| 5 minutes | 1.5 MINT |
| 1 hour | 18 MINT |

Base rate: 0.005 MINT/second

## Setup

1. Generate keypair: `solana-keygen new`
2. Register machine: `foundry-client` 
3. Fund wallet with ~0.01 SOL for tx fees

## License

MIT
