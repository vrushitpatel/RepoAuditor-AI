import asyncio
from app.integrations.gemini_client import GeminiClient

async def test_gemini():
  # GeminiClient will automatically use settings from app.config.settings
  # and create a default ModelConfig
  client = GeminiClient()

  # Simple test prompt
  response = await client.analyze_code(
  code_diff="""
  def login(username, password):
  query = "SELECT * FROM users WHERE username='" + username + "'"
  # SQL injection vulnerability!
  """,
  analysis_type="security"
  )

  print("Gemini Response:")
  print(response)

  # Should detect SQL injection
  assert any("sql injection" in str(finding).lower() for finding in response)
  print("✅ Gemini correctly identified SQL injection!")
if __name__ == "__main__":
  asyncio.run(test_gemini())