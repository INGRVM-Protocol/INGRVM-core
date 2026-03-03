import torch
from typing import Dict, Tuple

class ContextMemory:
    """
    Manages isolated neural states (short-term memory) for multiple mesh users.
    Prevents 'Context Contamination' between different conversation threads.
    """
    def __init__(self):
        # Maps SessionID -> (mem1, mem2)
        self.brain_states: Dict[str, Tuple[torch.Tensor, torch.Tensor]] = {}

    def get_state(self, session_id: str, default_states: Tuple[torch.Tensor, torch.Tensor]):
        """Retrieves or initializes the memory for a specific session."""
        if session_id not in self.brain_states:
            print(f"[MEMORY] Initializing NEW context for Session: {session_id}")
            self.brain_states[session_id] = default_states
        return self.brain_states[session_id]

    def save_state(self, session_id: str, states: Tuple[torch.Tensor, torch.Tensor]):
        """Commits the updated brain state back to the memory palace."""
        self.brain_states[session_id] = states

    def clear_context(self, session_id: str):
        if session_id in self.brain_states:
            del self.brain_states[session_id]
            print(f"[MEMORY] Context cleared for Session: {session_id}")

# --- Verification Test ---
if __name__ == "__main__":
    memory = ContextMemory()
    
    # 1. Simulate two different users
    user_a = "SESSION_RED"
    user_b = "SESSION_BLUE"
    
    # Initial dummy states
    initial_state = (torch.tensor([0.0]), torch.tensor([0.0]))
    
    # 2. Update User A's brain state
    state_a = memory.get_state(user_a, initial_state)
    updated_a = (torch.tensor([0.85]), torch.tensor([0.1])) # Brain charged up
    memory.save_state(user_a, updated_a)
    
    # 3. Check User B (Should still be initial)
    state_b = memory.get_state(user_b, initial_state)
    
    print(f"--- Context Separation Test ---")
    print(f"User A State (Membrane): {memory.get_state(user_a, initial_state)[0].item()}")
    print(f"User B State (Membrane): {state_b[0].item()}")
    
    if memory.get_state(user_a, initial_state)[0].item() != state_b[0].item():
        print("\nSUCCESS: Context Memory Palace is isolated and secure.")
