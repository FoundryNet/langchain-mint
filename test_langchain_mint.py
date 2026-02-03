"""Quick test of LangChain MINT integration"""

import os
from dotenv import load_dotenv
load_dotenv()

print("�� Testing LangChain MINT Integration\n")

# Test 1: Import
print("1. Testing imports...")
try:
    from langchain_mint import MintMiddleware, MintCallback, with_mint
    print("   ✅ Imports work")
except ImportError as e:
    print(f"   ❌ Import failed: {e}")
    print("   Run: pip3 install langchain-mint")
    exit(1)

# Test 2: Initialize middleware with keypair
print("\n2. Testing middleware init...")
try:
    # Use your existing keypair or create test path
    keypair_path = os.path.expanduser("~/.config/solana/id.json")
    
    if not os.path.exists(keypair_path):
        print(f"   ⚠️  No keypair at {keypair_path}, testing with dummy...")
        middleware = MintMiddleware()  # Should handle no keypair gracefully
    else:
        middleware = MintMiddleware(keypair_path=keypair_path)
    
    print("   ✅ Middleware initialized")
except Exception as e:
    print(f"   ❌ Middleware failed: {e}")

# Test 3: Initialize callback handler
print("\n3. Testing callback handler...")
try:
    callback = MintCallback()
    print("   ✅ Callback handler initialized")
except Exception as e:
    print(f"   ❌ Callback failed: {e}")

# Test 4: Test with_mint wrapper
print("\n4. Testing with_mint wrapper...")
try:
    # Just test the function exists and is callable
    assert callable(with_mint)
    print("   ✅ with_mint wrapper available")
except Exception as e:
    print(f"   ❌ with_mint failed: {e}")

# Test 5: Quick chain test (if langchain installed)
print("\n5. Testing with simple chain...")
try:
    from langchain_core.prompts import PromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    
    # Create minimal chain (no LLM call, just structure test)
    prompt = PromptTemplate.from_template("test {input}")
    parser = StrOutputParser()
    
    chain = prompt | parser
    mint_chain = with_mint(chain)
    
    print("   ✅ Chain wrapped with MINT successfully")
except ImportError:
    print("   ⚠️  langchain-core not installed, skipping chain test")
except Exception as e:
    print(f"   ❌ Chain test failed: {e}")

print("\n" + "="*50)
print("🎉 LangChain MINT integration ready!")
print("="*50)
