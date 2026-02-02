"""
Log Viewer - Generates readable reports from game session logs.

Provides two outputs:
1. Story Markdown - A clean narrative of what happened
2. Debug HTML - Technical view for debugging LLM calls
"""

import json
import os
import html
import re
from datetime import datetime
from typing import List, Dict, Any, Optional


class StoryExtractor:
    """Extracts a readable story from LLM logs."""

    @staticmethod
    def extract_story_events(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract story-relevant events from log entries."""
        events = []

        for entry in entries:
            ts = entry.get("ts", entry.get("timestamp", ""))
            resp = entry.get("resp", entry.get("response", {}))
            req = entry.get("req", entry.get("request", {}))

            # Determine agent type from system prompt
            msgs = req.get("messages", [])
            system_msg = msgs[0]["content"] if msgs else ""
            agent = StoryExtractor._identify_agent(system_msg)

            # Extract tool calls (the actual actions)
            tool_calls = resp.get("tool_calls") or []
            for tc in tool_calls:
                event = StoryExtractor._parse_tool_call(tc, agent, ts)
                if event:
                    events.append(event)

            # Also capture DM narration from content
            content = resp.get("content", "")
            if agent == "DM" and content and not tool_calls:
                events.append(
                    {
                        "timestamp": ts,
                        "type": "narration",
                        "agent": "DM",
                        "content": content,
                    }
                )

        return events

    @staticmethod
    def _identify_agent(system_msg: str) -> str:
        """Identify the agent from system prompt."""
        if "Director" in system_msg:
            return "Director"
        elif "Dungeon Master" in system_msg or "World Engineer" in system_msg:
            return "DM"
        elif "# I am" in system_msg:
            # Extract character name
            match = re.search(r"# I am (.+)", system_msg)
            if match:
                return match.group(1).strip()
        return "Unknown"

    @staticmethod
    def _parse_tool_call(tc: Dict, agent: str, ts: str) -> Optional[Dict]:
        """Parse a tool call into a story event."""
        name = tc.get("name", "")
        args_str = tc.get("args", "{}")

        try:
            args = json.loads(args_str) if isinstance(args_str, str) else args_str
        except (json.JSONDecodeError, TypeError):
            args = {}

        # Skip director meta-actions for story view
        if name in ["select_next_actor", "update_narrative", "direct"]:
            return None

        event = {"timestamp": ts, "agent": agent, "action": name, "args": args}

        # Categorize event type
        if name == "speak":
            event["type"] = "dialogue"
            event["message"] = args.get("message", "")
            event["target"] = args.get("target", "")
        elif name == "think":
            event["type"] = "thought"
            event["goals"] = args.get("goals", "")
            event["emotions"] = args.get("emotions", "")
            event["knowledge"] = args.get("knowledge", "")
        elif name == "act":
            event["type"] = "action"
            event["description"] = args.get("description", "")
            event["skill"] = args.get("skill", "")
            event["target"] = args.get("target", "")
        elif name == "move":
            event["type"] = "movement"
            event["destination"] = args.get("location", args.get("location_id", ""))
        elif name == "narrate":
            event["type"] = "narration"
            event["content"] = args.get("content", args.get("text", args.get("narration", "")))
        elif name == "create":
            # New unified create tool
            create_type = args.get("type", "")
            if create_type == "npc":
                event["type"] = "world_change"
                event["content"] = f"A new character appears: {args.get('name', 'someone')}"
            elif create_type == "location":
                event["type"] = "world_change"
                event["content"] = f"New location revealed: {args.get('name', 'somewhere')}"
            elif create_type == "item":
                event["type"] = "world_change"
                event["content"] = f"New item: {args.get('name', 'something')}"
            else:
                event["type"] = "world_change"
                event["content"] = f"Created: {args.get('name', 'something')}"
        elif name == "modify":
            event["type"] = "world_change"
            action = args.get("action", "")
            target = args.get("target_id", "")
            event["content"] = f"{action}: {target}"
        elif name == "spawn_npc":
            event["type"] = "world_change"
            event["content"] = f"A new character appears: {args.get('name', 'someone')}"
        elif name == "create_location":
            event["type"] = "world_change"
            event["content"] = f"New location revealed: {args.get('name', 'somewhere')}"
        else:
            event["type"] = "other"
            event["content"] = str(args)

        return event


class StoryFormatter:
    """Formats story events into readable output."""

    @staticmethod
    def to_markdown(events: List[Dict], include_thoughts: bool = False) -> str:
        """Generate a clean narrative markdown."""
        lines = [
            "# 📖 Story Log",
            "",
            f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
            "",
            "---",
            "",
        ]

        for event in events:
            event_type = event.get("type", "")
            agent = event.get("agent", "")

            # Scene changes get headers
            if event_type == "scene_change":
                dest = event.get("destination", "somewhere")
                lines.append(f"\n## 🎬 Scene: {dest.replace('-', ' ').title()}\n")
                continue

            # Format based on event type
            if event_type == "dialogue":
                msg = event.get("message", "")
                target = event.get("target", "")
                target_str = f" to {target}" if target else ""
                lines.append(f'**{agent}**{target_str}: "{msg}"\n')

            elif event_type == "narration":
                content = event.get("content", "")
                if content:
                    lines.append(f"*{content}*\n")

            elif event_type == "action":
                desc = event.get("description", "")
                lines.append(f"**{agent}** {desc}\n")

            elif event_type == "movement":
                dest = event.get("destination", "")
                lines.append(
                    f"*{agent} travels to {dest.replace('-', ' ').title()}.*\n"
                )

            elif event_type == "world_change":
                content = event.get("content", "")
                lines.append(f"🌟 *{content}*\n")

            elif event_type == "thought" and include_thoughts:
                emotions = event.get("emotions", "")
                goals = event.get("goals", "")
                knowledge = event.get("knowledge", "")

                thought_parts = []
                if emotions:
                    thought_parts.append(f"*Feeling: {emotions}*")
                if goals:
                    thought_parts.append(f"*Goal: {goals}*")
                if knowledge:
                    thought_parts.append(f"*Realizes: {knowledge}*")

                if thought_parts:
                    lines.append(f"> 💭 **{agent}'s thoughts:**")
                    for part in thought_parts:
                        lines.append(f"> {part}")
                    lines.append("")

        return "\n".join(lines)

    @staticmethod
    def to_html(events: List[Dict], include_thoughts: bool = True) -> str:
        """Generate a beautiful HTML story view."""

        html_content = (
            """<!DOCTYPE html>
<html>
<head>
    <title>📖 Story Log</title>
    <meta charset="UTF-8">
    <style>
        :root {
            --bg: #1a1a2e;
            --card-bg: #16213e;
            --text: #eaeaea;
            --text-dim: #a0a0a0;
            --accent: #e94560;
            --accent2: #0f3460;
            --gold: #f4d03f;
        }
        
        body {
            font-family: 'Georgia', serif;
            background: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 40px 20px;
            line-height: 1.8;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        
        h1 {
            text-align: center;
            color: var(--gold);
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }
        
        .subtitle {
            text-align: center;
            color: var(--text-dim);
            margin-bottom: 40px;
        }
        
        .scene-header {
            background: linear-gradient(135deg, var(--accent2), var(--card-bg));
            padding: 20px 30px;
            margin: 40px -20px;
            border-left: 4px solid var(--accent);
        }
        
        .scene-header h2 {
            margin: 0;
            color: var(--gold);
            font-size: 1.5em;
        }
        
        .event {
            margin: 20px 0;
            padding: 15px 20px;
            border-radius: 8px;
        }
        
        .dialogue {
            background: var(--card-bg);
            border-left: 3px solid var(--accent);
        }
        
        .dialogue .speaker {
            color: var(--accent);
            font-weight: bold;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .dialogue .message {
            font-size: 1.1em;
            margin-top: 8px;
            font-style: italic;
        }
        
        .dialogue .message::before { content: '"'; color: var(--gold); }
        .dialogue .message::after { content: '"'; color: var(--gold); }
        
        .narration {
            background: transparent;
            color: var(--text-dim);
            font-style: italic;
            padding: 10px 30px;
            border-left: 2px solid var(--accent2);
        }
        
        .action {
            background: var(--accent2);
            border-left: 3px solid var(--gold);
        }
        
        .action .actor {
            color: var(--gold);
            font-weight: bold;
        }
        
        .thought {
            background: rgba(244, 208, 63, 0.1);
            border: 1px dashed var(--gold);
            font-size: 0.95em;
        }
        
        .thought-label {
            color: var(--gold);
            font-size: 0.8em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .thought-content {
            color: var(--text-dim);
            font-style: italic;
        }
        
        .world-change {
            text-align: center;
            color: var(--gold);
            padding: 20px;
            font-style: italic;
        }
        
        .world-change::before { content: '✨ '; }
        .world-change::after { content: ' ✨'; }
        
        .movement {
            text-align: center;
            color: var(--text-dim);
            font-style: italic;
            padding: 10px;
        }
        
        .timestamp {
            font-size: 0.7em;
            color: var(--text-dim);
            float: right;
            opacity: 0.5;
        }
        
        .controls {
            position: fixed;
            top: 20px;
            right: 20px;
            background: var(--card-bg);
            padding: 10px 15px;
            border-radius: 8px;
            font-size: 0.9em;
        }
        
        .controls label {
            cursor: pointer;
        }
        
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="controls">
        <label>
            <input type="checkbox" id="showThoughts" checked onchange="toggleThoughts()">
            Show character thoughts
        </label>
    </div>
    
    <div class="container">
        <h1>📖 Story Log</h1>
        <p class="subtitle">Generated: """
            + datetime.now().strftime("%Y-%m-%d %H:%M")
            + """</p>
        
        <div class="story">
"""
        )

        for event in events:
            ts = event.get("timestamp", "")
            if ts:
                try:
                    time_str = datetime.fromisoformat(ts).strftime("%H:%M")
                except (ValueError, TypeError):
                    time_str = ""
            else:
                time_str = ""

            event_type = event.get("type", "")
            agent = html.escape(event.get("agent", ""))

            timestamp_html = (
                f'<span class="timestamp">{time_str}</span>' if time_str else ""
            )

            if event_type == "scene_change":
                dest = event.get("destination", "somewhere").replace("-", " ").title()
                html_content += f"""
            <div class="scene-header">
                <h2>🎬 {html.escape(dest)}</h2>
            </div>
"""
            elif event_type == "dialogue":
                msg = html.escape(event.get("message", ""))
                target = event.get("target", "")
                target_str = f" → {html.escape(target)}" if target else ""
                html_content += f"""
            <div class="event dialogue">
                {timestamp_html}
                <div class="speaker">{agent}{target_str}</div>
                <div class="message">{msg}</div>
            </div>
"""
            elif event_type == "narration":
                content = html.escape(event.get("content", ""))
                if content:
                    html_content += f"""
            <div class="event narration">{timestamp_html}{content}</div>
"""
            elif event_type == "action":
                desc = html.escape(event.get("description", ""))
                html_content += f"""
            <div class="event action">
                {timestamp_html}
                <span class="actor">{agent}</span> {desc}
            </div>
"""
            elif event_type == "movement":
                dest = event.get("destination", "").replace("-", " ").title()
                html_content += f"""
            <div class="event movement">{timestamp_html}{agent} travels to {html.escape(dest)}...</div>
"""
            elif event_type == "world_change":
                content = html.escape(event.get("content", ""))
                html_content += f"""
            <div class="event world-change">{timestamp_html}{content}</div>
"""
            elif event_type == "thought":
                emotions = html.escape(event.get("emotions", ""))
                goals = html.escape(event.get("goals", ""))
                knowledge = html.escape(event.get("knowledge", ""))

                parts = []
                if emotions:
                    parts.append(f"<strong>Feeling:</strong> {emotions}")
                if goals:
                    parts.append(f"<strong>Goal:</strong> {goals}")
                if knowledge:
                    parts.append(f"<strong>Realizes:</strong> {knowledge}")

                if parts:
                    html_content += f"""
            <div class="event thought" data-thought="true">
                {timestamp_html}
                <div class="thought-label">💭 {agent}'s thoughts</div>
                <div class="thought-content">{"<br>".join(parts)}</div>
            </div>
"""

        html_content += """
        </div>
    </div>
    
    <script>
        function toggleThoughts() {
            const show = document.getElementById('showThoughts').checked;
            document.querySelectorAll('[data-thought]').forEach(el => {
                el.classList.toggle('hidden', !show);
            });
        }
    </script>
</body>
</html>
"""
        return html_content


class LogViewer:
    """Original debug log viewer for technical inspection."""

    @staticmethod
    def parse_log(filepath: str) -> List[Dict[str, Any]]:
        entries = []
        if not os.path.exists(filepath):
            return entries

        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return entries

    @staticmethod
    def generate_html(entries: List[Dict[str, Any]], output_file: str):
        """Generate debug HTML view."""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>🔧 LLM Debug Viewer</title>
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
                .agent-director { color: #9c27b0; }
                .agent-dm { color: #f57c00; }
                .agent-char { color: #2196f3; }
                .card { background: #fff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 20px; padding: 20px; }
                .role { font-weight: bold; text-transform: uppercase; font-size: 0.8em; margin-bottom: 5px; color: #555; }
                .content { white-space: pre-wrap; font-family: "Consolas", "Monaco", monospace; font-size: 13px; background: #f8f9fa; padding: 10px; border-radius: 4px; border: 1px solid #eee; overflow-x: auto; max-height: 400px; overflow-y: auto; }
                .tool-call { background: #e8f5e9; border: 1px solid #c8e6c9; padding: 10px; margin-top: 10px; border-radius: 4px; }
                .tool-name { font-weight: bold; color: #2e7d32; }
                h2 { margin-top: 0; }
                .hidden { display: none; }
                .tokens { font-size: 0.75em; color: #888; margin-top: 5px; }
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

        for i, entry in enumerate(entries):
            ts = datetime.fromisoformat(
                entry.get("ts", entry.get("timestamp", ""))
            ).strftime("%H:%M:%S")
            duration = f"{entry.get('ms', entry.get('duration_ms', 0)):.0f}ms"

            req_data = entry.get("req", entry.get("request", {}))
            msgs = req_data.get("messages", [])
            system_msg = msgs[0]["content"] if msgs else ""

            if "Director" in system_msg:
                agent = "Director"
                agent_class = "agent-director"
            elif "Dungeon Master" in system_msg or "World Engineer" in system_msg:
                agent = "DM"
                agent_class = "agent-dm"
            elif "# I am" in system_msg:
                match = re.search(r"# I am (.+)", system_msg)
                agent = match.group(1).strip() if match else "Character"
                agent_class = "agent-char"
            else:
                agent = "Unknown"
                agent_class = ""

            html_content += f"""
                    <div class="entry-item" id="item-{i}" onclick="showEntry({i})">
                        <div class="timestamp">{ts}</div>
                        <div class="duration">{duration}</div>
                        <div style="font-weight:bold" class="{agent_class}">{html.escape(agent)}</div>
                    </div>
            """

        html_content += """
                </div>
                <div class="main">
        """

        for i, entry in enumerate(entries):
            req = entry.get("req", entry.get("request", {}))
            resp = entry.get("resp", entry.get("response", {}))
            usage = resp.get("usage", {})

            html_content += f'<div id="detail-{i}" class="entry-detail {"hidden" if i > 0 else ""}">'

            # Request Messages
            html_content += "<h2>📤 Request</h2>"
            for msg in req.get("messages", []):
                role = msg["role"]
                content = html.escape(msg["content"])
                html_content += f"""
                    <div class="card">
                        <div class="role">{role}</div>
                        <div class="content">{content}</div>
                    </div>
                """

            # Response
            html_content += "<h2>📥 Response</h2>"
            html_content += '<div class="card">'

            if resp.get("reasoning"):
                reasoning = html.escape(resp["reasoning"])
                html_content += f"""
                    <div style="background: #fff3e0; border: 1px solid #ffe0b2; padding: 10px; margin-bottom: 10px; border-radius: 4px;">
                        <div style="font-weight: bold; color: #e65100; margin-bottom: 5px;">🧠 Reasoning</div>
                        <div class="content" style="background: #fff8f0;">{reasoning}</div>
                    </div>
                """

            if resp.get("tool_calls"):
                for tc in resp["tool_calls"]:
                    args = tc.get("args", {})
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                            args = html.escape(json.dumps(args, indent=2))
                        except (json.JSONDecodeError, TypeError):
                            args = html.escape(args)
                    else:
                        args = html.escape(json.dumps(args, indent=2))

                    html_content += f"""
                        <div class="tool-call">
                            <div class="tool-name">🔧 {tc.get("name", "unknown")}</div>
                            <pre style="margin: 5px 0; white-space: pre-wrap;">{args}</pre>
                        </div>
                    """

            if resp.get("content"):
                html_content += (
                    f'<div class="content">{html.escape(resp["content"])}</div>'
                )

            if usage:
                html_content += f'<div class="tokens">Tokens: {usage.get("prompt_tokens", 0)} prompt + {usage.get("completion_tokens", 0)} completion = {usage.get("total_tokens", 0)} total</div>'

            html_content += "</div></div>"

        html_content += """
                </div>
            </div>
        </body>
        </html>
        """

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)


def generate_log_report(log_file: str, output_dir: str) -> bool:
    """Generate all reports from a log file."""
    entries = LogViewer.parse_log(log_file)
    if not entries:
        return False

    # 1. Generate debug HTML
    debug_path = os.path.join(output_dir, "debug_viewer.html")
    LogViewer.generate_html(entries, debug_path)

    # 2. Extract and format story
    events = StoryExtractor.extract_story_events(entries)

    # 3. Generate story markdown
    story_md = StoryFormatter.to_markdown(events, include_thoughts=True)
    md_path = os.path.join(output_dir, "story.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(story_md)

    # 4. Generate story HTML
    story_html = StoryFormatter.to_html(events, include_thoughts=True)
    html_path = os.path.join(output_dir, "story.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(story_html)

    return True
