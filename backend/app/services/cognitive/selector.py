import os
import re
from typing import List, Dict, Any, Tuple, Optional
from app.core.logger import skills_logger
from app.services.skills.registry import SkillsRegistry
from app.schemas.skills import SkillManifest

class SkillSelector:
    """Deterministic, offline rule-based selection engine for engineering skills."""
    
    def __init__(self, registry: Optional[SkillsRegistry] = None):
        self.registry = registry or SkillsRegistry()
        self.registry.load_manifests()

    def select_skills(self, query: str, active_file: Optional[str] = None) -> List[Dict[str, Any]]:
        """Evaluates registry manifests and returns up to 3 highest scoring skills (score > 0) ordered descending."""
        skills_logger.info(f"Evaluating skill triggers for query='{query}', active_file='{active_file}'")
        
        scores = []
        query_lower = query.lower()

        # Iterate all registered skills
        for name, skill in self.registry.skills.items():
            score = 0.0
            reasons = []

            # 1. Query-based triggers (Keywords matching)
            kw_matches = 0
            for kw in skill.activation_rules.keywords:
                # Use regex or simple word boundary to check if keyword is in query
                if re.search(r'\b' + re.escape(kw.lower()) + r'\b', query_lower):
                    kw_matches += 1
            if kw_matches > 0:
                score += kw_matches * 2.0
                reasons.append(f"Matched {kw_matches} query keywords")

            # 2. Domain-based triggers (File patterns matching)
            if active_file:
                basename = os.path.basename(active_file)
                pattern_matches = 0
                exact_match = False
                suffix_match = False

                for pattern in skill.activation_rules.file_patterns:
                    # check exact match or wildcard match
                    clean_pattern = pattern.replace("*", "")
                    if pattern == active_file or pattern == basename:
                        exact_match = True
                    elif clean_pattern and (active_file.endswith(clean_pattern) or basename.endswith(clean_pattern)):
                        suffix_match = True
                
                if exact_match:
                    score += 10.0
                    reasons.append(f"Exact workspace filename match for active file '{active_file}'")
                elif suffix_match:
                    score += 5.0
                    reasons.append(f"Suffix/Extension match for active file '{active_file}'")

            if score > 0:
                scores.append({
                    "skill": name,
                    "score": int(score),
                    "reason": "; ".join(reasons),
                    "manifest": skill
                })

        # Sort by score descending, then by name alphabetically to resolve ties predictably
        sorted_skills = sorted(scores, key=lambda x: (-x["score"], x["skill"]))
        
        # Take top 3
        top_skills = sorted_skills[:3]
        skills_logger.info(f"Selected skills: {[s['skill'] for s in top_skills]}")
        return top_skills
