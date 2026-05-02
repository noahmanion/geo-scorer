import os
from dotenv import load_dotenv

load_dotenv()

def test_anthropic():
    from anthropic import Anthropic
    client =Anthropic()
    msg = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=20,
        messages=[{"role": "user", "content": "Say 'pong' and stop"}]
    )
    print("anthropic", msg.content[0].text)

def test_openai():
    from openai import OpenAI
    client = OpenAI()
    resp = client.chat.completions.create(
        model="gpt-5.5",
        max_completion_tokens=20,
        messages=[{"role": "user", "content": "Say 'pong' and stop"}]
    )
    print("openai", resp.choices[0].message.content)

def test_gemini():
    from google import genai
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Say 'pong' and stop."
    )
    print("gemini", resp.text.strip())

def test_perplexity():
    from perplexity import Perplexity
    client = Perplexity()
    resp = client.chat.completions.create(
       model="sonar-pro",
       messages=[{"role": "user", "content": "Say 'pong' and stop"}]
    )
    print("perplexity", resp.choices[0].message.content)

def test_firecrawl():
    from firecrawl import Firecrawl
    app = Firecrawl(api_key=os.environ["FIRECRAWL_API_KEY"])
    result = app.scrape("https://example.com", formats=["markdown"])
    md = result.markdown if hasattr(result, "markdown") else result ["markdown"]
    print("firecrawl: scraped ", len(md), "chars of markdown")

if __name__ == "__main__":
   for name, fn in [
       ("anthropic", test_anthropic),
       ("openai", test_openai),
       ("gemini", test_gemini),
       ("perplexity", test_perplexity),
       ("firecrawl", test_firecrawl)
    
   ]:
       try:
        fn()
       except Exception as e:
        print(f"{name}: FAILED -> {type(e).__name__}: {e}")