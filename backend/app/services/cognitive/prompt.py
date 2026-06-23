from typing import Dict, Any, List
from app.core.config import settings
from app.core.logger import system_logger

class PromptBuilder:
    """Formats aggregated context blocks into standardized system/user prompt packages."""

    def __init__(self, version: str = None):
        self.version = version or settings.PROMPT_VERSION

    def build_prompt_package(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        # 1. System Prompt Assembly
        # Include Socratic Identity
        system_sections = [
            "=== CORE IDENTITY ===",
            context["identity"],
            ""
        ]

        # Include Selected Skills Prompt Overlays
        if context["skills"]:
            system_sections.append("=== ACTIVE SKILLS INSTRUCTIONS ===")
            for s in context["skills"]:
                skills_block = (
                    f"Skill: {s['name']}\n"
                    f"Assumed Role: {s['role']}\n"
                    f"Pedagogical Instruction: {s['pedagogical_instructions']}\n"
                    f"Technical Constraints:\n{s['technical_constraints']}"
                )
                system_sections.append(skills_block)
                system_sections.append("")
        else:
            system_sections.append("=== ACTIVE SKILLS INSTRUCTIONS ===")
            system_sections.append("Default Persona Active: Research Assistant.")
            system_sections.append("")

        system_prompt = "\n".join(system_sections).strip()

        # 2. User Prompt Assembly
        user_sections = []

        # Include Memory Context (goals, workspace telemetry, lessons, projects)
        user_sections.append("=== WORKSPACE & MEMORY CONTEXT ===")
        wm = context["working_memory"]
        goals_str = ", ".join([g["description"] for g in wm["active_goals"]]) if wm["active_goals"] else "None"
        user_sections.append(f"Active Goals: {goals_str}")
        
        active_ctx = wm["active_context"]
        if active_ctx:
            user_sections.append(
                f"Active Workspace File: {active_ctx.get('active_file')}\n"
                f"Cursor Line: {active_ctx.get('cursor_line')}"
            )
            if active_ctx.get("selected_code"):
                user_sections.append(f"Selected Code Context:\n{active_ctx.get('selected_code')}")
        
        # Long-term memory
        lt = context["longterm_memory"]
        if lt["lessons"]:
            lessons_str = "\n".join([f"- {l['concept_name']} (Mastery: {l['mastery_score']})" for l in lt["lessons"]])
            user_sections.append(f"Known Concepts:\n{lessons_str}")
        if lt["projects"]:
            projects_str = "\n".join([f"- {p['project_name']} (Tech: {', '.join(p['tech_stack']) if p['tech_stack'] else 'N/A'})" for p in lt["projects"]])
            user_sections.append(f"Associated Projects:\n{projects_str}")
            
        # Conversation History (Milestone-17)
        turns = context.get("conversation_turns")
        if turns:
            user_sections.append("\n=== CONVERSATION HISTORY ===")
            for turn in turns:
                user_sections.append(f"User: {turn['user_text']}")
                user_sections.append(f"Assistant: {turn['assistant_text']}")
        else:
            # Sensory Memory Events fallback
            sensory = context["sensory_memory"]
            if sensory:
                user_sections.append("\n=== RECENT DIALOGUE HISTORY ===")
                for event in sensory:
                    mod = event.get("primary_modality", "text")
                    summary = event.get("summary") or ""
                    text_payload = event.get("text_payload") or {}
                    transcript = text_payload.get("transcript") or ""
                    user_sections.append(f"[{mod.upper()}] {summary or transcript}")
        
        user_sections.append("")

        # Include Retrieved Episodic Memories (Milestone-18)
        episodic_memories = context.get("episodic_memories")
        if episodic_memories:
            user_sections.append("=== RECALLED PRIOR CONVERSATIONS (EPISODIC MEMORY) ===")
            for mem in episodic_memories:
                mem_block = (
                    f"Topic: {mem['title']}\n"
                    f"Summary: {mem['summary']}"
                )
                if mem.get("key_decisions"):
                    mem_block += f"\nDecisions Made: {', '.join(mem['key_decisions'])}"
                if mem.get("important_facts"):
                    mem_block += f"\nFacts Recalled: {', '.join(mem['important_facts'])}"
                if mem.get("open_tasks"):
                    mem_block += f"\nOpen Tasks from Session: {', '.join(mem['open_tasks'])}"
                user_sections.append(mem_block)
                user_sections.append("")

        # Workspace Environment Status
        ws = context.get("workspace")
        if ws:
            ws_sections = ["=== WORKSPACE ENVIRONMENT STATUS ==="]
            ws_sections.append(f"Repository: {ws['repo_name']} at {ws['repo_path']}")
            if ws.get("git_branch"):
                ws_sections.append(f"Git Branch: {ws['git_branch']}")
            
            git_status = ws.get("git_status") or {}
            mod = git_status.get("modified", [])
            stg = git_status.get("staged", [])
            utr = git_status.get("untracked", [])
            if mod or stg or utr:
                ws_sections.append("Git Status:")
                if stg:
                    ws_sections.append(f"  Staged: {', '.join(stg)}")
                if mod:
                    ws_sections.append(f"  Modified: {', '.join(mod)}")
                if utr:
                    ws_sections.append(f"  Untracked: {', '.join(utr)}")
            
            commits = ws.get("git_recent_commits")
            if commits:
                ws_sections.append("Recent Commits:")
                for c in commits[:settings.MAX_RECENT_COMMITS]:
                    ws_sections.append(f"  - {c['sha'][:7]} {c['author']}: {c['message']}")
            
            langs = ws.get("detected_languages")
            if langs:
                langs_str = ", ".join([f"{l['language']} ({l['file_count']})" for l in langs])
                ws_sections.append(f"Detected Languages: {langs_str}")
            
            frameworks = ws.get("detected_frameworks")
            if frameworks:
                ws_sections.append(f"Detected Frameworks: {', '.join(frameworks)}")
            
            if ws.get("scan_limit_reached"):
                ws_sections.append("Warning: Workspace scan limit reached during collection.")

            active_file = ws.get("active_file_path")
            if active_file:
                ws_sections.append(f"Active File: {active_file} ({ws.get('active_file_language') or 'Unknown'})")
                if ws.get("cursor_line"):
                    ws_sections.append(f"Cursor: line {ws['cursor_line']}, column {ws.get('cursor_column') or 0}")
                if ws.get("selection_content"):
                    trunc_str = " (truncated)" if ws.get("selection_truncated") else ""
                    ws_sections.append(f"Selected Code Segment{trunc_str}:\n{ws['selection_content']}")
            
            errors = ws.get("errors")
            if errors:
                ws_sections.append("Active Environment Errors / Failures:")
                for err in errors[:settings.MAX_WORKSPACE_ERRORS]:
                    ws_sections.append(f"  - [{err['source']} {err['severity'].upper()}] {err['message']}")
            
            user_sections.append("\n".join(ws_sections))
            user_sections.append("")

        # Include Retrieved Knowledge Context
        user_sections.append("=== RETRIEVED KNOWLEDGE CHUNKS ===")
        if context["knowledge"]:
            for idx, chunk in enumerate(context["knowledge"]):
                hierarchy = " > ".join(chunk["heading_hierarchy"]) if chunk.get("heading_hierarchy") else "General"
                user_sections.append(
                    f"Chunk {idx+1} [{chunk['filepath']} - {hierarchy}]:\n"
                    f"{chunk['content']}\n"
                )
        else:
            user_sections.append("No relevant documentation found.\n")

        # Include User Query
        user_sections.append("=== USER QUERY ===")
        user_sections.append(query)

        user_prompt = "\n".join(user_sections).strip()

        # Performance budget enforcement (MS-19)
        user_prompt_truncated = False
        if len(user_prompt) > settings.MAX_PROMPT_CHARS:
            user_prompt = user_prompt[:settings.MAX_PROMPT_CHARS] + "\n[TRUNCATED]"
            user_prompt_truncated = True
            system_logger.warning(
                f"User prompt truncated at {settings.MAX_PROMPT_CHARS} chars "
                f"(original length exceeded budget)"
            )

        # 3. Preview Generation
        # A short summary of counts and highlights
        skills_summary = ", ".join([s["name"] for s in context["skills"]]) if context["skills"] else "None"
        chunks_count = len(context["knowledge"])
        events_count = len(context["sensory_memory"])
        preview = (
            f"Prompt Version: {self.version}\n"
            f"Active Skills: {skills_summary}\n"
            f"Knowledge Chunks: {chunks_count} included\n"
            f"Sensory History Events: {events_count} included\n"
            f"Prompt Truncated: {user_prompt_truncated}\n"
            f"Raw Query: '{query[:60]}...'"
        )

        return {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "preview": preview,
            "prompt_version": self.version,
            "prompt_truncated": user_prompt_truncated,
        }
