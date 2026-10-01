import re
from pathlib import Path
from typing import List, Dict, Any


def get_skills_dir() -> Path:
    """
    Locates the workspace skills directory (.agents/skills).
    Walks up from backend/agent directory to repository root.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent
    skills_dir = repo_root / ".agents" / "skills"
    if skills_dir.exists():
        return skills_dir

    local_skills = Path(".agents/skills").resolve()
    return local_skills


def load_workspace_skills() -> List[Dict[str, Any]]:
    """
    Discovers and parses all workspace skills from .agents/skills/*/SKILL.md.
    Returns a list of dicts with 'name', 'description', 'body', and 'file_path'.
    """
    skills_dir = get_skills_dir()
    if not skills_dir.exists():
        return []

    skills = []
    for skill_file in sorted(skills_dir.glob("*/SKILL.md")):
        try:
            content = skill_file.read_text(encoding="utf-8")
            name = skill_file.parent.name
            desc = ""
            body = content

            # Parse frontmatter if present
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter = parts[1]
                    body = parts[2].strip()

                    # Extract name
                    name_match = re.search(r"^name:\s*(.+)$", frontmatter, re.MULTILINE)
                    if name_match:
                        name = name_match.group(1).strip()

                    # Extract description
                    desc_match = re.search(
                        r"^description:\s*(?:>-\s*|\s*)(.+?)(?=\n\w+:|\Z)",
                        frontmatter,
                        re.DOTALL | re.MULTILINE,
                    )
                    if desc_match:
                        desc = " ".join(desc_match.group(1).split())

            skills.append({
                "name": name,
                "description": desc,
                "body": body,
                "file_path": str(skill_file),
            })
        except Exception as e:
            print(f"[Warning] Failed to read skill file {skill_file}: {e}")

    return skills


def format_skills_for_prompt() -> str:
    """
    Formats all loaded workspace skills into a clear instruction block
    to be injected into the search agent's prompt/system instruction.
    """
    skills = load_workspace_skills()
    if not skills:
        return ""

    blocks = [
        "### Workspace Skills & Search Directives",
        "You MUST strictly follow and apply the following domain search skills when the user request matches their scope:",
    ]

    for s in skills:
        skill_header = f"#### Skill: {s['name']}"
        if s.get("description"):
            skill_header += f"\nDescription: {s['description']}"
        blocks.append(f"{skill_header}\nInstructions:\n{s['body']}")

    return "\n\n".join(blocks)
