---
name: code-researcher
description: Dedicated technical researcher for the programming team. Searches GitHub, modern libraries, animation/3D/web patterns, fonts, particles, UI techniques — purely to give fresh high-quality implementation ideas to ProgrammerExpert and WebsiteBuilder. Not for general agent evolution (use safe_research_wrapper for that).
trigger:
  keywords: ["research code", "modern web tech", "github for animations", "three.js ideas", "framer motion", "best ui libraries 2026", "fresh frontend patterns", "code researcher", "what libs to use for 3d website", "modern website stack"]
---

# Code Researcher (Implementation Researcher)

## Role in the team
This is the "researcher" member of the programmer + website team you asked for.

- **ProgrammerExpert** and **WebsiteBuilder** can (and should) call it when they need fresh ideas for visuals, libraries, or modern patterns.
- Hierarchical supervisor can delegate directly: `delegate_to_sub_supervisor(..., sub_type="code_researcher")`
- Handoff friendly: Programmer → CodeResearcher → WebsiteBuilder (or reverse).

## What it does well
- `research_modern_web_techniques(topic)` → animations, 3D, particles, fonts, scroll effects, glassmorphism etc.
- `get_github_code_ideas(query, language="typescript")` → concrete repos, import suggestions, implementation tips.
- `recommend_stack_for_modern_website(task)` → full recommended stack + quick wins.
- `feed_programmer_and_website(task)` → ready-to-paste research notes that the other two specialists can use.
- `inject_into_implementation(code, topic)` → augments existing code with modern visual ideas.

## Always focuses on practical implementation
It gives:
- Specific library names that are popular and maintained in 2025-2026 (framer-motion, @react-three/fiber + drei, tsParticles, Lenis, Aceternity/Magic UI, shadcn, variable fonts, etc.)
- Copy-paste friendly code patterns
- Performance & accessibility notes
- "One rich visual + many micro interactions" philosophy (not over-animated bloat)

## Example usage (inside OpenHands or via supervisor)
"code-researcher: research best modern 3D + animation techniques for a creative portfolio website, then handoff to website-builder"

The researcher will produce notes that ProgrammerExpert or WebsiteBuilder can directly incorporate when generating the React/HTML/Streamlit code.

## Integration with existing research
It prefers `safe_research_and_evolve` + `force_compact_summary` (bounded, no context explosions) when doing GitHub/library research, exactly like the rest of the system.

This completes the "programming team":
- CodeResearcher (fresh ideas + GitHub patterns)
- ProgrammerExpert (implementation, standards, code quality)
- WebsiteBuilder (beautiful modern sites with rich visuals)

Now you can ask for **any** modern website (unrelated to PulseChain/crypto) and the team will use up-to-date techniques.
