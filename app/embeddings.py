from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")

text = "My laptop is not connecting to WiFi."

embedding = model.encode(text)

print("Embedding created successfully.")
print("Vector size:", len(embedding))
print("First 5 values:", embedding[:5])  