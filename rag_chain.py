import os
from langchain_community.llms import Ollama
import chromadb

class RAGChain:
    def __init__(self, model_name="Phi", temperature=0.1, max_tokens=2048, num_ctx=4096):
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens  # Maximum tokens to generate (affects response length)
        self.num_ctx = num_ctx  # Context window size (affects memory usage)
        self.ollama = Ollama(
            model=model_name, 
            temperature=temperature,
            num_predict=max_tokens,  # Ollama uses num_predict for max tokens
            num_ctx=num_ctx
        )
        self.client = chromadb.PersistentClient(path="chroma_db")
        self.collection = self.client.get_or_create_collection(
            name="documents",
        )
    
    def switch_model(self, new_model_name):
        """Switch to a different Ollama model"""
        self.model_name = new_model_name
        self._update_ollama()
        print(f"Switched to model: {new_model_name}")
    
    def set_temperature(self, temperature):
        """Update the temperature parameter (0.0-2.0, lower = more focused/coherent)"""
        self.temperature = max(0.0, min(2.0, float(temperature)))
        self._update_ollama()
        print(f"Temperature set to: {self.temperature}")
    
    def set_performance(self, max_tokens=None, num_ctx=None):
        """Update performance parameters (lower = faster, less memory)"""
        if max_tokens is not None:
            self.max_tokens = max(128, min(4096, int(max_tokens)))  # Range: 128-4096 tokens
        if num_ctx is not None:
            self.num_ctx = max(1024, min(8192, int(num_ctx)))  # Range: 1024-8192 context
        self._update_ollama()
        print(f"Performance set: max_tokens={self.max_tokens}, num_ctx={self.num_ctx}")
    
    def _update_ollama(self):
        """Recreate Ollama instance with current parameters"""
        self.ollama = Ollama(
            model=self.model_name,
            temperature=self.temperature,
            num_predict=self.max_tokens,
            num_ctx=self.num_ctx
        )

    def retrieve(self, query, top_k=1):
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            include=["documents"]
        )
        return results["documents"][0]

    def rag_ask_streaming(self, query):
        retrieved_docs = self.retrieve(query, top_k=2)
        context = "\n".join(retrieved_docs)
        prompt = f"Use the following context to answer the question concisely. Context: {context} \n Question: {query} \nAnswer:"

        print("Answer (streaming): ", end="", flush=True)
        try:
            for chunk in self.ollama.stream(prompt):
                print(chunk, end="", flush=True)
        except AttributeError:
            print("\nStreaming is not supported by this Ollama implementation.")
        print()