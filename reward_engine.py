import sqlite3
import time
import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class SynapseLedger:
    """
    Phase 6 Foundation: Persistent SQL Ledger for $SYN Rewards.
    Replaces memory-only RewardEngine with a verifiable transaction history.
    """
    def __init__(self, db_path: str = "neuromorphic_env/ledger.db"):
        self.db_path = db_path
        if not os.path.exists(os.path.dirname(self.db_path)):
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 1. Accounts Table (Current Balances)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                node_id TEXT PRIMARY KEY,
                balance REAL DEFAULT 0.0,
                reputation REAL DEFAULT 1.0,
                total_work_spikes INTEGER DEFAULT 0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. Transactions Table (History)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id TEXT,
                receiver_id TEXT,
                amount REAL,
                tx_type TEXT, -- 'MINT', 'TRANSFER', 'REWARD', 'SLASH'
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                memo TEXT
            )
        """)
        
        conn.commit()
        conn.close()

    def mint_rewards(self, peer_id: str, amount: float, memo: str = "Epoch Reward"):
        """ Mints new $SYN and assigns it to a node. """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Update balance
        cursor.execute("""
            INSERT INTO accounts (node_id, balance) VALUES (?, ?)
            ON CONFLICT(node_id) DO UPDATE SET 
                balance = balance + EXCLUDED.balance,
                last_updated = CURRENT_TIMESTAMP
        """, (peer_id, amount))
        
        # Record transaction
        cursor.execute("""
            INSERT INTO transactions (sender_id, receiver_id, amount, tx_type, memo)
            VALUES (?, ?, ?, ?, ?)
        """, ("SYSTEM", peer_id, amount, "MINT", memo))
        
        conn.commit()
        conn.close()
        print(f"[LEDGER] Minted {amount:.4f} $SYN to {peer_id[:12]}... ({memo})")

    def transfer(self, sender_id: str, receiver_id: str, amount: float) -> bool:
        """ Transfers $SYN between two nodes. """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check balance
        cursor.execute("SELECT balance FROM accounts WHERE node_id = ?", (sender_id,))
        row = cursor.fetchone()
        if not row or row[0] < amount:
            conn.close()
            return False
            
        # Execute atomic transfer
        try:
            cursor.execute("UPDATE accounts SET balance = balance - ? WHERE node_id = ?", (amount, sender_id))
            cursor.execute("""
                INSERT INTO accounts (node_id, balance) VALUES (?, ?)
                ON CONFLICT(node_id) DO UPDATE SET balance = balance + EXCLUDED.balance
            """, (receiver_id, amount))
            
            cursor.execute("""
                INSERT INTO transactions (sender_id, receiver_id, amount, tx_type)
                VALUES (?, ?, ?, ?)
            """, (sender_id, receiver_id, amount, "TRANSFER"))
            
            conn.commit()
            success = True
        except Exception:
            conn.rollback()
            success = False
        finally:
            conn.close()
        return success

    def record_work(self, peer_id: str, spikes: int):
        """ Updates a node's work statistics and reputation. """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Reputation grows with work (max 2.0)
        cursor.execute("""
            INSERT INTO accounts (node_id, total_work_spikes, reputation) VALUES (?, ?, 1.01)
            ON CONFLICT(node_id) DO UPDATE SET 
                total_work_spikes = total_work_spikes + EXCLUDED.total_work_spikes,
                reputation = MIN(2.0, reputation + 0.005),
                last_updated = CURRENT_TIMESTAMP
        """, (peer_id, spikes))
        
        conn.commit()
        conn.close()

    def slash_node(self, peer_id: str, penalty_syn: float = 5.0, rep_burn: float = 0.1, memo: str = "Validation Failure"):
        """ 
        Phase 6 Task #16: Reputation Burn (Slashing).
        Penalizes a node for malicious or incorrect behavior.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 1. Reduce Balance (Minimum 0)
        cursor.execute("""
            UPDATE accounts 
            SET balance = MAX(0.0, balance - ?),
                reputation = MAX(0.5, reputation - ?),
                last_updated = CURRENT_TIMESTAMP
            WHERE node_id = ?
        """, (penalty_syn, rep_burn, peer_id))
        
        # 2. Record Slashed Transaction
        cursor.execute("""
            INSERT INTO transactions (sender_id, receiver_id, amount, tx_type, memo)
            VALUES (?, ?, ?, ?, ?)
        """, (peer_id, "BURN_ADDRESS", -penalty_syn, "SLASH", memo))
        
        conn.commit()
        conn.close()
        print(f"[LEDGER] SLASHTAG: {peer_id[:12]}... Burned {penalty_syn} $SYN. Rep Burn: -{rep_burn}")

    def get_balance(self, node_id: str) -> float:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM accounts WHERE node_id = ?", (node_id,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else 0.0

    def get_top_nodes(self, limit: int = 10) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM accounts ORDER BY balance DESC LIMIT ?", (limit,))
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

# --- Verification Test ---
if __name__ == "__main__":
    ledger = SynapseLedger()
    
    # 1. Simulate Work & Reward
    test_node = "12D3KooW_MASTER_NODE_ALPHA"
    ledger.record_work(test_node, spikes=1000)
    ledger.mint_rewards(test_node, amount=50.0, memo="Bootstrap Bonus")
    
    # 2. Simulate Transfer
    receiver = "12D3KooW_MOBILE_NODE_BETA"
    if ledger.transfer(test_node, receiver, 15.0):
        print(f"SUCCESS: Transferred 15.0 $SYN to {receiver[:12]}...")
        
    # 3. Display Balances
    print("\n--- Current Ledger State ---")
    for node in ledger.get_top_nodes():
        print(f"Node: {node['node_id'][:12]}... | Balance: {node['balance']:.2f} $SYN | Rep: {node['reputation']:.2f}")
    
    if os.path.exists("neuromorphic_env/ledger.db"):
        print("\nSUCCESS: Phase 6 Virtual Ledger functional.")
