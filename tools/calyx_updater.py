import os
import subprocess
import sys

def update_calyx():
    """
    Calyx Updater: Pulls latest ecosystem changes from GitHub to the Calyx directory.
    This replaces the desktop app for the current Phase 2 Sprint.
    """
    print("🔄 --- Calyx Updater ---")
    
    # Check if the repo exists
    repo_url = "https://github.com/<ORG_NAME>/<REPO_NAME>"
    
    # 1. Check for remote updates
    try:
        print(f"📡 Checking remote: {repo_url}...")
        subprocess.run(["git", "fetch", "origin"], check=True)
        
        # 2. Check for local changes
        status = subprocess.check_output(["git", "status", "--porcelain"]).decode().strip()
        if status:
            print("⚠️ Local changes detected. Stashing to pull updates safely...")
            subprocess.run(["git", "stash"], check=True)
            
        # 3. Pull latest from master
        print("🚀 Pulling latest changes from master...")
        subprocess.run(["git", "pull", "origin", "master"], check=True)
        
        # 4. Re-apply local changes if any
        if status:
            print("🔄 Re-applying your local work...")
            subprocess.run(["git", "stash", "pop"], check=True)
            
        print("\n✅ Calyx is now up-to-date with GitHub.")
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Git error: {e}")
        print("💡 Hint: Ensure you have 'git' installed and the remote 'origin' is set.")
    except FileNotFoundError:
        print("\n❌ Git not found. Please install Git to use the Calyx Updater.")

if __name__ == "__main__":
    update_calyx()
