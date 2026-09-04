"""
SEO Expert Skill for OpenHands
Professional Technical SEO Specialist.
Focus: On-page SEO, technical SEO, meta optimization, structured data, Core Web Vitals for search, mobile SEO.
"""

from logger import log
from typing import Dict, Any

try:
    from openhands_skills.code_researcher import code_researcher
except Exception:
    code_researcher = None

try:
    from persistent_memory import persistent_memory
except Exception:
    persistent_memory = None


from openhands_skills.expert_base import ExpertSkill


class SEOExpert(ExpertSkill):
    """
    Senior SEO Specialist for modern websites.
    Delivers production-ready SEO strategy, tags, audits, and optimizations.
    Integrates with website-builder for final polish and mobile-first SEO.
    """

    def __init__(self):
        self.focus = "Making websites discoverable, fast, and ranking well on Google and other search engines."

    def optimize_for_search(self, task: str, context: Dict = None) -> Dict[str, Any]:
        """Main professional entry: Full SEO audit + optimization plan + ready assets."""
        log.info(f"SEOExpert: Optimizing for search: {task[:60]}")
        context = context or {}

        research = ""
        if code_researcher:
            try:
                research = code_researcher.feed_programmer_and_website(task + " SEO 2026", "technical SEO best practices")
            except Exception:
                pass

        result = {
            "task": task,
            "seo_audit_checklist": self.seo_audit_checklist(),
            "meta_tags_template": self.generate_meta_tags(task),
            "structured_data_examples": self.structured_data_examples(task),
            "technical_recommendations": self.technical_recommendations(),
            "mobile_seo_focus": "Mobile-first indexing is default. Ensure responsive, fast load (<3s on 3G), touch-friendly.",
            "core_web_vitals_targets": {
                "LCP": "< 2.5s",
                "INP": "< 200ms",
                "CLS": "< 0.1"
            },
            "research": research[:1200] if research else "2026 Google SEO guidelines + E-E-A-T focus."
        }

        if persistent_memory:
            try:
                persistent_memory.store_learning("seo:website", f"{task} | professional SEO strategy")
            except Exception:
                pass

        print("🔍 SEOExpert: Professional SEO optimization plan delivered.")
        result["expert_analysis"] = self.consult(
            task, context, extra_system="You are a senior technical SEO expert in structured data, Core Web Vitals and search optimisation.")
        self.mark_analysis(result)
        return result

    def seo_audit_checklist(self) -> list:
        return [
            "Title & meta description unique, <60/155 chars, keyword front-loaded",
            "H1-H6 proper hierarchy, one H1 per page",
            "Image alt text descriptive + keywords",
            "Internal linking (3-5 per page) + external authority links",
            "Schema markup (Article, FAQ, Product, Organization)",
            "XML sitemap + robots.txt optimized",
            "HTTPS, mobile-friendly, no duplicate content",
            "Page speed: optimize images, defer JS, use CDN",
            "E-E-A-T signals: author bios, citations, fresh content"
        ]

    def generate_meta_tags(self, page_topic: str) -> str:
        return f"""<!-- Professional SEO Meta Tags for: {page_topic} -->
<title>{page_topic} | Your Brand - Premium Modern Experience</title>
<meta name="description" content="Discover {page_topic} with stunning 3D visuals, seamless mobile experience, and expert craftsmanship. Fast, accessible, and built for 2026.">
<meta name="robots" content="index, follow, max-image-preview:large">
<link rel="canonical" href="https://yourdomain.com/..." />

<!-- Open Graph / Twitter -->
<meta property="og:title" content="{page_topic} | Your Brand">
<meta property="og:description" content="...">
<meta property="og:image" content="https://yourdomain.com/og-image.jpg">
<meta name="twitter:card" content="summary_large_image">
"""

    def structured_data_examples(self, page_type: str) -> str:
        return f"""<!-- JSON-LD Structured Data (add to <head> or via script) -->
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "WebPage",
  "name": "{page_type}",
  "description": "Professional {page_type} with modern design and 3D experiences.",
  "breadcrumb": {{ ... }},
  "mainEntity": {{
    "@type": "Article",
    "author": {{"@type": "Person", "name": "Your Expert"}},
    "datePublished": "2026-..."
  }}
}}
</script>
"""

    def technical_recommendations(self) -> list:
        return [
            "Implement hreflang for multi-language if needed",
            "Use next-sitemap or similar for dynamic sitemaps",
            "Monitor with Google Search Console + PageSpeed Insights",
            "Implement FAQ/HowTo schema for rich results",
            "Optimize for voice search & featured snippets"
        ]

# Register
seo_expert = SEOExpert()
print("🔍 SEOExpert registered. Ready for sub_type='seo'.")