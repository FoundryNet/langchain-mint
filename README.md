# langchain-mint

**Your agents work. Your agents earn.**

Earn MINT tokens for LangChain agent execution via [FoundryNet](https://github.com/foundrynet).

## Installation
```bash
pip install langchain-mint
```

## Usage

### Agent Middleware (Recommended - LangChain v1)
```python
from langchain_mint import MintMiddleware
from langchain.agents import AgentExecutor

middleware = MintMiddleware(keypair_path="~/.config/solana/id.json")

agent = AgentExecutor(
    agent=my_agent,
    tools=my_tools,
    middleware=[middleware]  # Add MINT middleware
)

result = agent.invoke({"input": "research topic X"})
# MINT automatically settled after agent completes
```

### Callback Handler (Legacy)
```python
from langchain_mint import MintCallback

callback = MintCallback(keypair_path="~/.config/solana/id.json")
agent = AgentExecutor(..., callbacks=[callback])
```

### Wrap Any Chain
```python
from langchain_mint import with_mint

chain = prompt | llm | parser
mint_chain = with_mint(chain, keypair_path="~/.config/solana/id.json")
```

## Earnings

| Agent Runtime | ~MINT Earned |
|---------------|--------------|
| 30 seconds | 0.15 MINT |
| 5 minutes | 1.5 MINT |
| 1 hour | 18 MINT |

Base rate: 0.005 MINT/second

## Links

- [Dashboard](https://foundrynet.github.io/foundry_net_MINT/)
- [GitHub](https://github.com/FoundryNet/langchain-mint)
- [PyPI](https://pypi.org/project/foundry-client/)

## License

MIT
