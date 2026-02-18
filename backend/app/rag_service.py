import os
import glob
import numpy as np
import faiss
from typing import List, Dict, Any
import logging
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self, knowledge_dir: str, client=None):
        self.knowledge_dir = knowledge_dir
        self.client = client
        self.embed_model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self.encoder = SentenceTransformer(self.embed_model_name)
        self.index = None
        self.documents = []
        
    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 150) -> List[str]:
        """Split text into overlapping chunks with specified size and overlap."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start += chunk_size - overlap
        return chunks

    def ingest(self):
        """Read files, chunk, embed, and index."""
        files = glob.glob(os.path.join(self.knowledge_dir, "*.txt")) + \
                glob.glob(os.path.join(self.knowledge_dir, "*.md"))
        
        all_chunks = []
        self.documents = []
        
        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    filename = os.path.basename(file_path)
                    chunks = self._chunk_text(content, chunk_size=1000, overlap=150)
                    
                    for i, chunk_text in enumerate(chunks):
                        chunk_id = f"{filename}#chunk{i}"
                        self.documents.append({
                            "id": chunk_id,
                            "content": chunk_text,
                            "source": filename
                        })
                        all_chunks.append(chunk_text)
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
        
        if not all_chunks:
            logger.warning("No knowledge documents found.")
            return

        logger.info(f"Generating embeddings for {len(all_chunks)} chunks...")
        
        # Generate embeddings using sentence transformers
        embeddings = self.encoder.encode(all_chunks, convert_to_numpy=True).astype('float32')
        
        # Build FAISS index
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings)
        logger.info("RAG Index built successfully.")

    def retrieve(self, query: str, top_k: int = 4, threshold: float = 0.25) -> List[Dict[str, Any]]:
        """Retrieve relevant chunks for the query."""
        if self.index is None or not self.documents:
            return []
            
        # Embed query using sentence transformers
        query_embedding = self.encoder.encode([query], convert_to_numpy=True).astype('float32')
        
        # Search index
        distances, indices = self.index.search(query_embedding, top_k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            # Convert L2 distance to similarity score (higher is better)
            # FAISS L2 distance, so we convert to similarity: similarity = 1 / (1 + distance)
            similarity = 1 / (1 + distances[0][i])
            
            if idx != -1 and idx < len(self.documents) and similarity >= threshold:
                results.append(self.documents[idx])
        
        return results