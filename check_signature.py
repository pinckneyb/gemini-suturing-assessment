import google.genai

client = google.genai.Client(api_key="dummy")

print(help(client.models.generate_content)) 