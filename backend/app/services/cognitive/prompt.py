from typing import Dict, Any, List
from app.core.config import settings

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
            
        # Sensory Memory Events
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
            f"Raw Query: '{query[:60]}...'"
        )

        return {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "preview": preview,
            "prompt_version": self.version
        }
