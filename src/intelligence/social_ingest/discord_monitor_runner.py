#!/usr/bin/env python3
"""
Discord Monitor Runner

External script that calls discord_monitor.py every 15 seconds and compares output
to detect new messages. This avoids the infinite loop issues we had with built-in monitoring.

Usage:
    python discord_monitor_runner.py

This script:
1. Gets initial reference message
2. Runs every 15 seconds
3. Compares output to detect changes
4. Processes new token data when changes detected
"""

import subprocess
import sys
import time
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DiscordMonitorRunner:
    """External runner for Discord monitoring"""
    
    def __init__(self, check_interval=15):
        self.check_interval = check_interval
        self.discord_script = "src/intelligence/social_ingest/discord_monitor.py"
        self.previous_output = None
        self.running = False
        self.seen_contracts = set()  # Track unique contract addresses
        
        print(f"🤖 Discord Monitor Runner initialized")
        print(f"   - Script: {self.discord_script}")
        print(f"   - Check interval: {check_interval} seconds")
        print(f"   - Working directory: {os.getcwd()}")
    
    def run_discord_monitor(self):
        """Run the Discord monitor script and return output"""
        try:
            result = subprocess.run([
                sys.executable, self.discord_script
            ], capture_output=True, text=True, cwd=os.getcwd())
            
            if result.stderr:
                print(f"⚠️  Discord script stderr: {result.stderr}")
            
            return result.stdout.strip()
            
        except Exception as e:
            print(f"❌ Error running Discord script: {e}")
            return None
    
    def process_new_token_data(self, output):
        """Process new token data when changes are detected"""
        try:
            if not output:
                print("   (Empty output)")
                return
            
            # Try to parse JSON output - look for JSON in the output
            json_start = output.find('{')
            if json_start != -1:
                json_part = output[json_start:]
                try:
                    data = json.loads(json_part)
                    
                    if data.get('status') == 'new_tokens_found':
                        tokens = data.get('tokens', [])
                        
                        # Check for new unique contract addresses
                        new_tokens = []
                        for token in tokens:
                            contract = token.get('contract')
                            if contract and contract not in self.seen_contracts:
                                new_tokens.append(token)
                                self.seen_contracts.add(contract)
                        
                        if new_tokens:
                            print(f"   🆕 Found {len(new_tokens)} NEW tokens!")
                            
                            for token in new_tokens:
                                print(f"      💎 {token.get('ticker', 'UNKNOWN')} - {token.get('contract', 'N/A')}")
                                print(f"         MC: ${token.get('market_cap', 'N/A'):,}" if token.get('market_cap') else "         MC: N/A")
                                print(f"         Liq: ${token.get('liquidity', 'N/A'):,}" if token.get('liquidity') else "         Liq: N/A")
                                print(f"         TXNS: {token.get('transactions', 'N/A')}")
                                print(f"         Holders: {token.get('holders', 'N/A')}")
                                print()
                            
                            # Here is where we would create strands and send to trading system
                            print("   📝 Would create strands and send to Universal Learning System")
                        else:
                            print(f"   ℹ️  Found {len(tokens)} tokens, but all already seen")
                        
                    elif data.get('status') == 'error':
                        print(f"   ❌ Discord script error: {data.get('error')}")
                    else:
                        print(f"   ℹ️  Status: {data.get('status', 'unknown')}")
                        
                except json.JSONDecodeError as e:
                    print(f"   ❌ JSON parse error: {e}")
                    print(f"   📄 Raw output: {output[:200]}{'...' if len(output) > 200 else ''}")
            else:
                print(f"   📄 No JSON found in output: {output[:200]}{'...' if len(output) > 200 else ''}")
                
        except Exception as e:
            print(f"   ❌ Error processing token data: {e}")
    
    def start_monitoring(self):
        """Start monitoring Discord for new messages"""
        print(f"🚀 Starting Discord monitoring...")
        print(f"📊 Will check every {self.check_interval} seconds")
        print(f"⏱️  Press Ctrl+C to stop")
        print("=" * 60)
        
        # Get initial reference
        print("📋 Getting initial reference message...")
        self.previous_output = self.run_discord_monitor()
        
        if self.previous_output is None:
            print("❌ Failed to get initial reference. Exiting.")
            return
        
        print("✅ Initial reference captured")
        print(f"📄 Reference: {self.previous_output[:100]}{'...' if len(self.previous_output) > 100 else ''}")
        print()
        
        self.running = True
        check_count = 0
        
        try:
            while self.running:
                check_count += 1
                print(f"🔍 Check #{check_count} - {datetime.now().strftime('%H:%M:%S')}")
                
                # Run Discord monitor
                current_output = self.run_discord_monitor()
                
                if current_output is None:
                    print("   ❌ Failed to get current output")
                    continue
                
                # Compare with previous output
                if current_output != self.previous_output:
                    print("🆕 CHANGE DETECTED!")
                    print("=" * 40)
                    print(current_output)
                    print("=" * 40)
                    
                    # Process the new token data
                    self.process_new_token_data(current_output)
                    
                    print("🆕 END OF CHANGE")
                else:
                    print("   (No changes)")
                
                # Update reference
                self.previous_output = current_output
                
                # Wait for next check
                if self.running:
                    print(f"⏰ Waiting {self.check_interval} seconds...\n")
                    time.sleep(self.check_interval)
        
        except KeyboardInterrupt:
            print("\n👋 Stopping Discord monitoring...")
        except Exception as e:
            print(f"\n❌ Error in monitoring: {e}")
        finally:
            self.running = False
            print("✅ Discord monitoring stopped")

def main():
    """Main function"""
    runner = DiscordMonitorRunner(check_interval=15)
    runner.start_monitoring()

if __name__ == "__main__":
    main()
