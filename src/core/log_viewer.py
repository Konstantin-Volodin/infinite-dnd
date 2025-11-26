import json
import os
import html
from datetime import datetime
from typing import List, Dict, Any

class LogViewer:
    @staticmethod
    def parse_log(filepath: str) -> List[Dict[str, Any]]:
        entries = []
        if not os.path.exists(filepath):
            return entries
            
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entries.append(json.loads(line))
                except:
                    pass
        return entries

    @staticmethod
    def generate_html(entries: List[Dict[str, Any]], output_file: str):
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>LLM Debug Viewer</title>
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 0; background: #f0f2f5; color: #333; }
                .container { display: flex; height: 100vh; }
                .sidebar { width: 300px; background: #fff; border-right: 1px solid #ddd; overflow-y: auto; }
                .main { flex: 1; padding: 20px; overflow-y: auto; }
                .entry-item { padding: 15px; border-bottom: 1px solid #eee; cursor: pointer; }
                .entry-item:hover { background: #f5f5f5; }
                .entry-item.active { background: #e3f2fd; border-left: 4px solid #2196f3; }
                .timestamp { font-size: 0.8em; color: #888; }
                .duration { font-size: 0.8em; color: #666; font-weight: bold; }
                .card { background: #fff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 20px; padding: 20px; }
                .role { font-weight: bold; text-transform: uppercase; font-size: 0.8em; margin-bottom: 5px; color: #555; }
                .content { white-space: pre-wrap; font-family: "Consolas", "Monaco", monospace; font-size: 14px; background: #f8f9fa; padding: 10px; border-radius: 4px; border: 1px solid #eee; overflow-x: auto; }
                .tool-call { background: #e8f5e9; border: 1px solid #c8e6c9; padding: 10px; margin-top: 10px; border-radius: 4px; }
                .tool-name { font-weight: bold; color: #2e7d32; }
                h2 { margin-top: 0; }
                .hidden { display: none; }
            </style>
            <script>
                function showEntry(index) {
                    document.querySelectorAll('.entry-detail').forEach(el => el.classList.add('hidden'));
                    document.getElementById('detail-' + index).classList.remove('hidden');
                    document.querySelectorAll('.entry-item').forEach(el => el.classList.remove('active'));
                    document.getElementById('item-' + index).classList.add('active');
                }
            </script>
        </head>
        <body>
            <div class="container">
                <div class="sidebar">
        """
        
        # Sidebar items
        for i, entry in enumerate(entries):
            ts = datetime.fromisoformat(entry.get('ts', entry.get('timestamp', ''))).strftime('%H:%M:%S')
            duration = f"{entry.get('ms', entry.get('duration_ms', 0)):.0f}ms"
            
            # Try to guess the agent/action
            req_data = entry.get('req', entry.get('request', {}))
            msgs = req_data.get('messages', [])
            system_msg = msgs[0]['content'] if msgs else ""
            agent = "Unknown"
            if "Orchestrator" in system_msg or "bard" in system_msg.lower():
                agent = "Orchestrator"
            elif "Dungeon Master" in system_msg:
                agent = "DM"
            elif "You are" in system_msg:
                # Extract name
                agent = system_msg.split(",")[0].replace("You are ", "")
                
            html_content += f"""
                    <div class="entry-item" id="item-{i}" onclick="showEntry({i})">
                        <div class="timestamp">{ts}</div>
                        <div style="font-weight:bold">{agent}</div>
                        <div class="duration">{duration}</div>
                    </div>
            """

        html_content += """
                </div>
                <div class="main">
        """

        # Main content details
        for i, entry in enumerate(entries):
            req = entry.get('req', entry.get('request', {}))
            resp = entry.get('resp', entry.get('response', {}))
            
            html_content += f'<div id="detail-{i}" class="entry-detail {"hidden" if i > 0 else ""}">'
            
            # Request Messages
            html_content += "<h2>Request</h2>"
            for msg in req['messages']:
                role = msg['role']
                content = html.escape(msg['content'])
                html_content += f"""
                    <div class="card">
                        <div class="role">{role}</div>
                        <div class="content">{content}</div>
                    </div>
                """
                
            # Response
            html_content += "<h2>Response</h2>"
            html_content += '<div class="card">'
            
            if resp.get('tool_calls'):
                for tc in resp['tool_calls']:
                    args = tc['args']
                    if isinstance(args, str):
                        args = html.escape(args)
                    else:
                        args = html.escape(json.dumps(args, indent=2))
                        
                    html_content += f"""
                        <div class="tool-call">
                            <div class="tool-name">🔧 {tc['name']}</div>
                            <pre>{args}</pre>
                        </div>
                    """
            
            if resp.get('content'):
                 html_content += f'<div class="content">{html.escape(resp["content"])}</div>'
                 
            html_content += "</div></div>"

        html_content += """
                </div>
            </div>
        </body>
        </html>
        """
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

def generate_log_report(log_file: str, output_file: str):
    """Convenience function to generate report from a log file"""
    entries = LogViewer.parse_log(log_file)
    if entries:
        LogViewer.generate_html(entries, output_file)
        return True
    return False
