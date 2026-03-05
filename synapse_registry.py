import sqlite3
import json
import os
import torch
import torch.nn as nn
from typing import List, Dict, Optional, Any
from datetime import datetime

class SynapseRegistry:
    """
    Phase 6 Foundation: SQL-backed registry for the Calyx Marketplace.
    Tracks model metadata, IPFS CIDs, and performance metrics.
    """
    def __init__(self, db_path: str = "neuromorphic_env/marketplace.db", storage_dir: str = "synapses"):
        self.db_path = db_path
        self.storage_dir = storage_dir
        
        if not os.path.exists(os.path.dirname(self.db_path)):
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir, exist_ok=True)
            
        self._init_db()

    def _init_db(self):
        """ Initializes the SQLite tables for marketplace metadata. """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main Synapse Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS synapses (
                synapse_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                author_id TEXT NOT NULL,
                version TEXT NOT NULL,
                category TEXT,
                description TEXT,
                cid TEXT, -- IPFS Content Identifier
                architecture TEXT, -- e.g. 'LIF-3-8-2'
                energy_score REAL DEFAULT 0.0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        """)
        
        # Performance/Validation Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS synapse_stats (
                synapse_id TEXT PRIMARY KEY,
                total_inferences INTEGER DEFAULT 0,
                avg_latency_ms REAL DEFAULT 0.0,
                total_spikes INTEGER DEFAULT 0,
                FOREIGN KEY (synapse_id) REFERENCES synapses(synapse_id)
            )
        """)
        
        conn.commit()
        conn.close()

    def save_synapse(self, synapse_id: str, model: nn.Module, metadata: dict):
        """Saves the model weights and metadata to disk and SQL."""
        synapse_path = os.path.join(self.storage_dir, f"{synapse_id}.pt")
        
        # Save weights
        torch.save(model.state_dict(), synapse_path)
        
        # Also register in SQL
        sql_meta = {
            "synapse_id": synapse_id,
            "name": metadata.get("name", synapse_id),
            "author_id": metadata.get("author_id", "local_node"),
            "version": metadata.get("version", "1.0.0"),
            "category": metadata.get("category", "general"),
            "description": metadata.get("description", ""),
            "architecture": metadata.get("architecture", "SNN")
        }
        self.register_synapse(sql_meta)

    def register_synapse(self, metadata: Dict[str, Any]):
        """
        Adds or updates a synapse in the SQL registry.
        Expected keys: synapse_id, name, author_id, version, category, description, cid, architecture
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO synapses 
            (synapse_id, name, author_id, version, category, description, cid, architecture)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metadata['synapse_id'],
            metadata['name'],
            metadata['author_id'],
            metadata['version'],
            metadata.get('category', 'general'),
            metadata.get('description', ''),
            metadata.get('cid', ''),
            metadata.get('architecture', 'SNN')
        ))
        
        # Initialize stats if new
        cursor.execute("""
            INSERT OR IGNORE INTO synapse_stats (synapse_id) VALUES (?)
        """, (metadata['synapse_id'],))
        
        conn.commit()
        conn.close()
        print(f"[SQL-REGISTRY] Registered synapse: {metadata['name']} ({metadata['synapse_id']})")

    def save_weights(self, synapse_id: str, model: nn.Module):
        """ Saves model weights to local storage. """
        path = os.path.join(self.storage_dir, f"{synapse_id}.pt")
        torch.save(model.state_dict(), path)
        print(f"[SQL-REGISTRY] Weights saved for {synapse_id}")

    def load_synapse(self, synapse_id: str, model: nn.Module) -> Optional[Dict[str, Any]]:
        """ Loads weights and returns metadata from SQL. """
        # Load weights
        path = os.path.join(self.storage_dir, f"{synapse_id}.pt")
        if not os.path.exists(path):
            print(f"[WARN] No weights found for {synapse_id}")
            return None
            
        model.load_state_dict(torch.load(path))
        
        # Fetch metadata
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM synapses WHERE synapse_id = ?", (synapse_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None

    def list_synapses(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """ Returns a list of all registered synapses. """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if category:
            cursor.execute("SELECT * FROM synapses WHERE category = ? AND is_active = 1", (category,))
        else:
            cursor.execute("SELECT * FROM synapses WHERE is_active = 1")
            
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    def search_synapses(self, query: str) -> List[Dict[str, Any]]:
        """ 
        Task #11: Full-text search for the Marketplace.
        Searches across name, description, and category.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        search_term = f"%{query}%"
        cursor.execute("""
            SELECT * FROM synapses 
            WHERE is_active = 1 
            AND (name LIKE ? OR description LIKE ? OR category LIKE ?)
            ORDER BY energy_score DESC
        """, (search_term, search_term, search_term))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

# --- Verification Test ---
if __name__ == "__main__":
    reg = SynapseRegistry()
    
    # Mock data
    test_meta = {
        "synapse_id": "sentiment_alpha_v1",
        "name": "Sentiment Alpha",
        "author_id": "PC_MASTER",
        "version": "1.0.0",
        "category": "NLP",
        "description": "High-efficiency spiking sentiment analysis.",
        "architecture": "3-8-2-LIF"
    }
    
    reg.register_synapse(test_meta)
    
    available = reg.list_synapses()
    print(f"\n--- Marketplace Catalog ({len(available)} items) ---")
    for s in available:
        print(f"[{s['category']}] {s['name']} v{s['version']} by {s['author_id']}")
    
    if os.path.exists("neuromorphic_env/marketplace.db"):
        print("\nSUCCESS: Phase 6 SQL Registry initialized.")
