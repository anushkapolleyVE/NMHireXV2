"""Skill taxonomy for NM-HireX structured search.

Structure:
  SKILL_TREE         -- parent -> [children/sub-skills]
  SKILL_CATEGORIES   -- top-level domain -> [SKILL_TREE keys that belong to it]
  SKILL_ALIASES      -- canonical skill -> [known spelling/abbreviation variants]
  CANONICAL_PARENT   -- explicit single parent for multi-parent children

Derived at module load (do NOT mutate after import):
  ALIAS_TO_CANONICAL -- any alias/variant -> canonical SKILL_TREE key (lowercase)
  IMPLICATIONS       -- child canonical -> set of parent canonicals
  SKILL_TO_CATEGORY  -- SKILL_TREE key canonical -> display category string

Public API
----------
canonical(skill)                -> punctuation-stripped lowercase key
resolve_canonical(skill)        -> follows alias redirects to canonical key
implied_parents(skill)          -> set[str] of parent canonical keys
normalize_skill_from_tree(name) -> (display_name, parent_display|None, category|None)
get_fts_expansion_terms(skill)  -> list[str] of all variant spellings for FTS
"""

import re

# ============================================================
# SKILL TREE
# Keys are parents; values are their children.
# ============================================================

SKILL_TREE: dict[str, list[str]] = {
    # ---- languages ------------------------------------------------
    "python": [
        "django", "flask", "fastapi", "pandas", "numpy", "scipy", "pytest",
        "celery", "sqlalchemy", "pyspark", "matplotlib", "scikit-learn",
        "beautifulsoup", "scrapy", "streamlit", "gradio",
    ],
    "php": [
        "laravel", "codeigniter", "symfony", "cakephp", "yii", "zend",
        "wordpress", "magento", "drupal", "joomla", "woocommerce", "phpunit",
    ],
    "javascript": [
        "typescript", "react", "angular", "vue", "node.js",
        "express", "jquery", "svelte", "ember",
        "backbone", "d3.js", "three.js",
    ],
    "java": [
        "spring", "spring boot", "hibernate", "struts", "maven", "gradle",
        "junit", "jsp", "servlets", "jakarta ee", "j2ee", "kafka streams",
    ],
    "c#": ["asp.net", ".net", ".net core", "entity framework", "blazor", "xamarin", "linq", "wpf"],
    ".net": ["asp.net", ".net core", "entity framework", "blazor", "wpf", "wcf"],
    "c++": ["qt", "boost", "unreal engine", "opencv"],
    "ruby": ["ruby on rails", "rails", "sinatra"],
    "go": ["gin", "echo framework"],
    "rust": ["actix", "tokio"],
    "kotlin": ["ktor", "jetpack compose"],
    "swift": ["swiftui", "uikit"],
    "scala": ["akka", "play framework"],

    # ---- frontend -------------------------------------------------
    "react": ["next.js", "redux", "react native", "react hooks", "gatsby"],
    "angular": ["rxjs", "ngrx"],
    "vue": ["nuxt.js", "vuex", "pinia"],
    "css": ["sass", "scss", "less", "tailwind css", "bootstrap", "material ui", "styled components"],
    "html": ["html5", "jsx", "handlebars"],

    # ---- mobile ---------------------------------------------------
    "mobile development": ["android", "ios", "flutter", "react native", "xamarin", "ionic", "cordova"],
    "android": ["android studio", "jetpack compose", "kotlin android"],
    "ios": ["swiftui", "uikit", "xcode", "objective-c"],
    "flutter": ["dart"],

    # ---- data / databases -----------------------------------------
    "sql": [
        "mysql", "postgresql", "sql server", "mssql", "oracle sql",
        "pl/sql", "t-sql", "sqlite", "mariadb",
    ],
    "nosql": ["mongodb", "cassandra", "dynamodb", "couchdb", "redis", "neo4j", "firebase"],
    "data engineering": ["etl", "airflow", "spark", "hadoop", "kafka", "databricks", "snowflake", "dbt"],
    "business intelligence": ["power bi", "tableau", "looker", "qlik", "apache superset"],

    # ---- cloud / devops -------------------------------------------
    "aws": [
        "ec2", "s3", "lambda", "cloudformation", "rds", "eks", "ecs",
        "cloudfront", "sqs", "sns", "dynamodb",
    ],
    "azure": ["azure devops", "azure functions", "azure ad", "aks", "azure synapse", "logic apps"],
    "gcp": ["bigquery", "cloud functions", "gke", "cloud run"],
    "devops": [
        "docker", "kubernetes", "jenkins", "terraform", "ansible", "gitlab ci",
        "github actions", "circleci", "helm", "prometheus", "grafana", "ci/cd",
    ],
    "linux": ["ubuntu", "centos", "rhel", "bash", "shell scripting", "debian"],
    "version control": ["git", "github", "gitlab", "bitbucket", "svn"],

    # ---- ai / ml --------------------------------------------------
    "machine learning": [
        "scikit-learn", "xgboost", "random forest", "regression models",
        "classification models", "clustering", "feature engineering",
    ],
    "deep learning": ["pytorch", "tensorflow", "keras", "cnn", "rnn", "transformers", "neural networks"],
    "llms": [
        "large language models", "gpt", "chatgpt", "claude", "gemini", "llama",
        "mistral", "langchain", "llamaindex", "prompt engineering", "rag",
        "retrieval-augmented generation", "fine-tuning", "lora", "qlora",
        "hugging face", "openai api", "anthropic api", "mcp",
    ],
    "vector databases": ["pinecone", "faiss", "chromadb", "weaviate", "qdrant", "milvus", "pgvector"],
    "nlp": ["spacy", "nltk", "bert", "named entity recognition", "sentiment analysis", "text classification"],
    "computer vision": ["opencv", "yolo", "image segmentation", "object detection"],

    # ---- cms / ecommerce ------------------------------------------
    "wordpress": ["elementor", "woocommerce", "divi", "acf", "gutenberg"],
    "magento": ["adobe commerce", "magento 2"],
    "ecommerce": ["shopify", "woocommerce", "magento", "bigcommerce", "prestashop", "opencart"],

    # ---- digital marketing / seo ----------------------------------
    "seo": [
        "on-page seo", "off-page seo", "technical seo", "local seo",
        "keyword research", "link building", "backlink acquisition",
        "serp analysis", "schema markup", "google search console",
        "semrush", "ahrefs", "moz", "screaming frog",
        "answer engine optimization",
    ],
    "digital marketing": [
        "seo", "sem", "ppc", "google ads", "meta ads",
        "facebook ads", "social media marketing", "email marketing",
        "content marketing", "affiliate marketing", "google analytics",
        "google tag manager", "mailchimp", "hubspot",
    ],
    "content writing": ["copywriting", "blog writing", "technical writing", "content strategy"],
    "graphic design": ["photoshop", "illustrator", "canva", "figma", "adobe xd", "coreldraw", "indesign"],

    # ---- finance / accounts ---------------------------------------
    "accounting": [
        "tally", "tally erp", "quickbooks", "zoho books", "sap fico",
        "bookkeeping", "accounts payable", "accounts receivable",
        "bank reconciliation", "journal entries", "general ledger",
        "financial reporting", "balance sheet", "trial balance",
    ],
    "taxation": ["gst", "tds", "income tax", "vat", "gst filing", "tax returns", "tax compliance"],
    "auditing": ["internal audit", "statutory audit", "audit compliance"],
    "payroll": ["salary processing", "pf", "esi", "payroll management"],

    # ---- hr -------------------------------------------------------
    "human resources": [
        "recruitment", "talent acquisition", "onboarding",
        "employee relations", "performance management", "hrms", "hris",
        "payroll", "employee engagement", "exit formalities", "hr operations",
        "workforce planning", "compensation and benefits",
    ],
    "recruitment": [
        "sourcing", "screening", "technical recruitment", "it recruitment",
        "naukri", "linkedin recruiter", "applicant tracking system",
        "campus hiring", "lateral hiring",
    ],

    # ---- testing / qa ---------------------------------------------
    "testing": [
        "manual testing", "automation testing", "selenium", "cypress",
        "playwright", "appium", "jmeter", "postman", "test cases",
        "regression testing", "unit testing",
    ],

    # ---- project / process ----------------------------------------
    "project management": ["jira", "agile", "scrum", "kanban", "confluence", "asana", "trello", "sprint planning"],
    "erp": ["sap", "dynamics 365", "oracle erp", "netsuite", "odoo"],
}


# ============================================================
# SKILL CATEGORIES
# Groups SKILL_TREE top-level keys into high-level domains.
# ============================================================

SKILL_CATEGORIES: dict[str, list[str]] = {
    "Backend":            ["python", "java", "php", "ruby", "go", "rust", "scala", "c#", ".net", "c++"],
    "Frontend":           ["javascript", "react", "angular", "vue", "css", "html"],
    "Mobile":             ["mobile development", "android", "ios", "flutter"],
    "Data & Databases":   ["sql", "nosql", "data engineering", "business intelligence"],
    "Cloud & DevOps":     ["aws", "azure", "gcp", "devops", "linux", "version control"],
    "AI & ML":            ["machine learning", "deep learning", "llms", "vector databases", "nlp", "computer vision"],
    "CMS & Ecommerce":    ["wordpress", "magento", "ecommerce"],
    "Digital Marketing":  ["seo", "digital marketing", "content writing", "graphic design"],
    "Finance":            ["accounting", "taxation", "auditing", "payroll"],
    "HR":                 ["human resources", "recruitment"],
    "Testing & QA":       ["testing"],
    "Project Management": ["project management", "erp"],
}


# ============================================================
# SKILL ALIASES
# canonical skill -> [variant spellings / abbreviations]
# ============================================================

SKILL_ALIASES: dict[str, list[str]] = {
    # Languages
    "javascript":                ["js", "ecmascript", "es6", "es2015"],
    "typescript":                ["ts"],
    "python":                    ["py"],
    "c#":                        ["csharp", "c sharp"],
    "c++":                       ["cpp", "cplusplus"],
    "go":                        ["golang"],
    "kotlin":                    ["kt"],
    # Frontend frameworks
    "react":                     ["react.js", "reactjs", "react js"],
    "vue":                       ["vue.js", "vuejs", "vue js"],
    "angular":                   ["angularjs", "angular 2+", "angular2"],
    "node.js":                   ["nodejs", "node js", "node"],
    "next.js":                   ["nextjs", "next js"],
    "nuxt.js":                   ["nuxtjs", "nuxt js"],
    "svelte":                    ["sveltejs", "svelte.js"],
    "tailwind css":              ["tailwind", "tailwindcss"],
    "material ui":               ["mui", "material-ui"],
    # Databases
    "postgresql":                ["postgres", "psql", "pg"],
    "mongodb":                   ["mongo"],
    "sql server":                ["mssql", "ms sql", "microsoft sql server"],
    "pl/sql":                    ["plsql"],
    "elasticsearch":             ["elastic search", "es"],
    "redis":                     ["redis cache"],
    "dynamodb":                  ["amazon dynamodb"],
    # Cloud
    "aws":                       ["amazon web services", "amazon aws"],
    "gcp":                       ["google cloud", "google cloud platform"],
    "azure":                     ["microsoft azure"],
    "kubernetes":                ["k8s"],
    "docker":                    ["docker container"],
    "github actions":            ["gh actions"],
    "gitlab ci":                 ["gitlab ci/cd", "gitlab cicd"],
    "ci/cd":                     ["cicd", "ci cd", "continuous integration", "continuous delivery"],
    # ML / AI
    "scikit-learn":              ["sklearn", "scikit learn"],
    "tensorflow":                ["tf"],
    "pytorch":                   ["torch"],
    "hugging face":              ["huggingface"],
    "llms":                      ["large language models", "llm"],
    "rag":                       ["retrieval-augmented generation", "retrieval augmented generation"],
    # Mobile
    "react native":              ["rn"],
    "flutter":                   ["flutter sdk"],
    "swift":                     ["swift language"],
    "android":                   ["android development"],
    "ios":                       ["ios development"],
    # Tools / Frameworks
    "ruby on rails":             ["rails", "ror"],
    "spring boot":               ["springboot"],
    "spring":                    ["spring framework"],
    "django":                    ["django framework"],
    "fastapi":                   ["fast api"],
    "wordpress":                 ["wp"],
    "figma":                     ["figma design"],
    "photoshop":                 ["adobe photoshop"],
    "illustrator":               ["adobe illustrator"],
    # Finance
    "tally":                     ["tally erp", "tally erp 9", "tally prime"],
    "quickbooks":                ["quick books"],
    "sap fico":                  ["sap fi", "sap co"],
    # Marketing
    "google ads":                ["google adwords", "adwords"],
    "meta ads":                  ["facebook ads", "instagram ads"],
    "semrush":                   ["sem rush"],
    # HR / Recruitment
    "applicant tracking system": ["ats"],
    "human resources":           ["hr"],
    "hrms":                      ["hris"],
    # ERP
    "dynamics 365":              ["d365", "ms dynamics", "microsoft dynamics"],
    "sap":                       ["sap erp"],
    # Misc
    "power bi":                  ["powerbi", "power-bi"],
    "agile":                     ["agile methodology"],
    "scrum":                     ["scrum methodology"],
    "selenium":                  ["selenium webdriver"],
    "yolo":                      ["yolov5", "yolov8"],
}


# ============================================================
# CANONICAL PARENT
# Resolves ambiguity when a child appears under multiple parents.
# child_canonical -> preferred parent_canonical
# ============================================================

CANONICAL_PARENT: dict[str, str] = {
    # react children
    "next.js":          "react",
    "redux":            "react",
    "react native":     "react",
    "react hooks":      "react",
    "gatsby":           "react",
    # vue children
    "nuxt.js":          "vue",
    "vuex":             "vue",
    "pinia":            "vue",
    # angular children
    "rxjs":             "angular",
    "ngrx":             "angular",
    # javascript ecosystem
    "typescript":       "javascript",
    "svelte":           "javascript",
    "node.js":          "javascript",
    "express":          "node.js",
    # python children
    "django":           "python",
    "flask":            "python",
    "fastapi":          "python",
    "scikit-learn":     "python",
    "celery":           "python",
    # java children
    "spring boot":      "java",
    "spring":           "java",
    "hibernate":        "java",
    "maven":            "java",
    "gradle":           "java",
    # php children
    "laravel":          "php",
    "symfony":          "php",
    "wordpress":        "php",
    # mobile
    "jetpack compose":  "android",
    "swiftui":          "ios",
    "uikit":            "ios",
    "dart":             "flutter",
    # devops
    "docker":           "devops",
    "kubernetes":       "devops",
    "terraform":        "devops",
    "jenkins":          "devops",
    "helm":             "devops",
    "github actions":   "devops",
    "gitlab ci":        "devops",
    "ansible":          "devops",
    "ci/cd":            "devops",
    # cloud
    "dynamodb":         "aws",
    # ecommerce
    "woocommerce":      "wordpress",
    "magento":          "ecommerce",
    # ml / ai
    "xgboost":          "machine learning",
    "pytorch":          "deep learning",
    "tensorflow":       "deep learning",
    "keras":            "deep learning",
    "transformers":     "deep learning",
    "scikit-learn":     "machine learning",
    "opencv":           "computer vision",
    "yolo":             "computer vision",
    # marketing
    "seo":              "digital marketing",
    "google ads":       "digital marketing",
    "meta ads":         "digital marketing",
    # hr
    "payroll":          "human resources",
    "recruitment":      "human resources",
    # version control
    "github":           "version control",
    "gitlab":           "version control",
    "git":              "version control",
    # accounting
    "tally":            "accounting",
    "tally erp":        "accounting",
}


# ============================================================
# DISPLAY NAMES
# canonical key -> preferred title-case display name
# ============================================================

_DISPLAY_NAMES: dict[str, str] = {
    "javascript":            "JavaScript",
    "typescript":            "TypeScript",
    "python":                "Python",
    "php":                   "PHP",
    "java":                  "Java",
    "c#":                    "C#",
    ".net":                  ".NET",
    ".net core":             ".NET Core",
    "asp.net":               "ASP.NET",
    "c++":                   "C++",
    "ruby":                  "Ruby",
    "go":                    "Go",
    "rust":                  "Rust",
    "kotlin":                "Kotlin",
    "swift":                 "Swift",
    "scala":                 "Scala",
    "react":                 "React",
    "angular":               "Angular",
    "vue":                   "Vue",
    "css":                   "CSS",
    "html":                  "HTML",
    "html5":                 "HTML5",
    "node.js":               "Node.js",
    "next.js":               "Next.js",
    "nuxt.js":               "Nuxt.js",
    "d3.js":                 "D3.js",
    "three.js":              "Three.js",
    "tailwind css":          "Tailwind CSS",
    "material ui":           "Material UI",
    "sql":                   "SQL",
    "nosql":                 "NoSQL",
    "postgresql":            "PostgreSQL",
    "mongodb":               "MongoDB",
    "mysql":                 "MySQL",
    "redis":                 "Redis",
    "dynamodb":              "DynamoDB",
    "cassandra":             "Cassandra",
    "sqlite":                "SQLite",
    "mariadb":               "MariaDB",
    "firebase":              "Firebase",
    "neo4j":                 "Neo4j",
    "sql server":            "SQL Server",
    "pl/sql":                "PL/SQL",
    "t-sql":                 "T-SQL",
    "aws":                   "AWS",
    "azure":                 "Azure",
    "gcp":                   "GCP",
    "devops":                "DevOps",
    "linux":                 "Linux",
    "docker":                "Docker",
    "kubernetes":            "Kubernetes",
    "jenkins":               "Jenkins",
    "terraform":             "Terraform",
    "ansible":               "Ansible",
    "ci/cd":                 "CI/CD",
    "github actions":        "GitHub Actions",
    "gitlab ci":             "GitLab CI",
    "git":                   "Git",
    "github":                "GitHub",
    "gitlab":                "GitLab",
    "bitbucket":             "Bitbucket",
    "machine learning":      "Machine Learning",
    "deep learning":         "Deep Learning",
    "llms":                  "LLMs",
    "nlp":                   "NLP",
    "pytorch":               "PyTorch",
    "tensorflow":            "TensorFlow",
    "scikit-learn":          "Scikit-learn",
    "hugging face":          "Hugging Face",
    "rag":                   "RAG",
    "langchain":             "LangChain",
    "openai api":            "OpenAI API",
    "vector databases":      "Vector Databases",
    "chromadb":              "ChromaDB",
    "pinecone":              "Pinecone",
    "computer vision":       "Computer Vision",
    "opencv":                "OpenCV",
    "yolo":                  "YOLO",
    "wordpress":             "WordPress",
    "woocommerce":           "WooCommerce",
    "magento":               "Magento",
    "ecommerce":             "E-Commerce",
    "seo":                   "SEO",
    "digital marketing":     "Digital Marketing",
    "graphic design":        "Graphic Design",
    "power bi":              "Power BI",
    "tableau":               "Tableau",
    "bigquery":              "BigQuery",
    "snowflake":             "Snowflake",
    "databricks":            "Databricks",
    "kafka":                 "Kafka",
    "airflow":               "Airflow",
    "spark":                 "Spark",
    "dbt":                   "dbt",
    "sap":                   "SAP",
    "sap fico":              "SAP FICO",
    "dynamics 365":          "Dynamics 365",
    "quickbooks":            "QuickBooks",
    "tally":                 "Tally",
    "tally erp":             "Tally ERP",
    "accounting":            "Accounting",
    "taxation":              "Taxation",
    "auditing":              "Auditing",
    "payroll":               "Payroll",
    "human resources":       "Human Resources",
    "recruitment":           "Recruitment",
    "testing":               "Testing",
    "project management":    "Project Management",
    "erp":                   "ERP",
    "agile":                 "Agile",
    "scrum":                 "Scrum",
    "jira":                  "Jira",
    "selenium":              "Selenium",
    "postman":               "Postman",
    "spring boot":           "Spring Boot",
    "spring":                "Spring",
    "django":                "Django",
    "flask":                 "Flask",
    "fastapi":               "FastAPI",
    "laravel":               "Laravel",
    "figma":                 "Figma",
    "photoshop":             "Photoshop",
    "illustrator":           "Illustrator",
    "canva":                 "Canva",
    "google ads":            "Google Ads",
    "meta ads":              "Meta Ads",
    "google analytics":      "Google Analytics",
    "hubspot":               "HubSpot",
    "mailchimp":             "Mailchimp",
    "semrush":               "SEMrush",
    "ahrefs":                "Ahrefs",
    "android studio":        "Android Studio",
    "xcode":                 "Xcode",
    "flutter":               "Flutter",
    "dart":                  "Dart",
    "react native":          "React Native",
    "ruby on rails":         "Ruby on Rails",
    "mobile development":    "Mobile Development",
    "version control":       "Version Control",
    "data engineering":      "Data Engineering",
    "business intelligence": "Business Intelligence",
    "applicant tracking system": "Applicant Tracking System",
    "hrms":                  "HRMS",
    "hris":                  "HRIS",
}


# ============================================================
# DERIVED LOOKUP TABLES  (built once at import time)
# ============================================================

def _canonicalize(skill: str) -> str:
    """Punctuation-insensitive key. '+' and '#' preserved for C++ / C#."""
    return re.sub(r"[^a-z0-9+#]", "", skill.lower())


def _build_alias_to_canonical() -> dict[str, str]:
    """Map every alias/variant -> its canonical key (canonicalized)."""
    mapping: dict[str, str] = {}
    for base_key, aliases in SKILL_ALIASES.items():
        ck = _canonicalize(base_key)
        mapping[ck] = ck          # canonical maps to itself
        for alias in aliases:
            mapping[_canonicalize(alias)] = ck
    return mapping


def _build_implications() -> dict[str, set[str]]:
    """Invert SKILL_TREE: child canonical -> set of parent canonicals."""
    implications: dict[str, set[str]] = {}
    for parent, children in SKILL_TREE.items():
        pk = _canonicalize(parent)
        for child in children:
            implications.setdefault(_canonicalize(child), set()).add(pk)
    return implications


def _build_skill_to_category() -> dict[str, str]:
    """Map every SKILL_TREE key canonical -> its category display string."""
    mapping: dict[str, str] = {}
    for category, keys in SKILL_CATEGORIES.items():
        for key in keys:
            mapping[_canonicalize(key)] = category
    return mapping


def _build_aliases_of() -> dict[str, list[str]]:
    """Map canonical key -> all known display variants (for FTS expansion)."""
    result: dict[str, list[str]] = {}
    for base_key, aliases in SKILL_ALIASES.items():
        ck = _canonicalize(base_key)
        result[ck] = [base_key] + aliases
    return result


# Build once
ALIAS_TO_CANONICAL: dict[str, str] = _build_alias_to_canonical()
IMPLICATIONS: dict[str, set[str]] = _build_implications()
SKILL_TO_CATEGORY: dict[str, str] = _build_skill_to_category()
ALIASES_OF: dict[str, list[str]] = _build_aliases_of()

# Canonical set of all SKILL_TREE parent keys
_TREE_PARENTS: set[str] = {_canonicalize(k) for k in SKILL_TREE}

# Canonical map of CANONICAL_PARENT (built once for fast lookup)
_CANONICAL_PARENT_CK: dict[str, str] = {
    _canonicalize(k): _canonicalize(v) for k, v in CANONICAL_PARENT.items()
}

# Re-key _DISPLAY_NAMES by their canonicalized form so lookups work for names
# containing dots/hyphens that get stripped during canonicalization.
# e.g. "node.js" -> "nodejs", "scikit-learn" -> "scikitlearn"
_DISPLAY_NAMES_CK: dict[str, str] = {
    _canonicalize(k): v for k, v in _DISPLAY_NAMES.items()
}


# ============================================================
# PUBLIC HELPERS
# ============================================================

def canonical(skill: str) -> str:
    """Punctuation-insensitive key: 'React.js' and 'ReactJS' both -> 'reactjs'.

    '+' and '#' survive so C++ and C# stay distinct from C.
    """
    return _canonicalize(skill)


def resolve_canonical(skill: str) -> str:
    """Return the canonical key for a skill, following alias redirects.

    Example:
        "NodeJS"  -> "nodejs"  (which is the canonical for "node.js")
        "sklearn" -> "scikitlearn"
    """
    ck = _canonicalize(skill)
    return ALIAS_TO_CANONICAL.get(ck, ck)


def implied_parents(skill: str) -> set[str]:
    """Canonical parent skill keys this skill demonstrates. Empty when unmapped."""
    return IMPLICATIONS.get(resolve_canonical(skill), set())


def normalize_skill_from_tree(name: str) -> tuple[str, str | None, str | None]:
    """Normalize a raw skill name using the full skill taxonomy.

    Resolution order:
      1. Resolve alias -> canonical key
      2. Look up explicit CANONICAL_PARENT override
      3. If not found, pick the alphabetically-first implied parent (deterministic)
      4. Walk up to grandparent if category is still missing
      5. Resolve display names and category from lookup tables

    Input:
        name  -> raw skill string from CV or JD

    Output:
        (display_name, parent_display_name | None, category | None)

    Examples:
        "ReactJS"      -> ("React",        "JavaScript",   "Frontend")
        "NodeJS"       -> ("Node.js",       "JavaScript",   "Frontend")
        "Spring Boot"  -> ("Spring Boot",   "Java",         "Backend")
        "K8s"          -> ("Kubernetes",    "DevOps",       "Cloud & DevOps")
        "sklearn"      -> ("Scikit-learn",  "Machine Learning", "AI & ML")
        "Postgres"     -> ("PostgreSQL",    "SQL",          "Data & Databases")
        "Unknown Tool" -> ("Unknown Tool",  None,           None)
    """
    if not name or not name.strip():
        return ("", None, None)

    raw = name.strip()
    ck = resolve_canonical(raw)

    # --- Determine parent canonical ---
    parent_ck: str | None = _CANONICAL_PARENT_CK.get(ck)

    if parent_ck is None:
        parents = IMPLICATIONS.get(ck, set())
        if parents:
            parent_ck = min(parents)  # deterministic fallback

    # --- Display name for the skill itself ---
    # _DISPLAY_NAMES_CK is pre-keyed by canonical form, so "nodejs" and
    # "scikitlearn" resolve correctly even though the raw keys use dots/hyphens.
    display = _DISPLAY_NAMES_CK.get(ck) or raw

    # --- Display name for parent ---
    parent_display: str | None = None
    if parent_ck:
        parent_display = _DISPLAY_NAMES_CK.get(parent_ck)
        if parent_display is None:
            # Fallback: find the original SKILL_TREE key spelling
            for tree_key in SKILL_TREE:
                if _canonicalize(tree_key) == parent_ck:
                    parent_display = tree_key.title()
                    break
            if parent_display is None:
                parent_display = parent_ck  # last resort

    # --- Category ---
    category: str | None = SKILL_TO_CATEGORY.get(ck)

    if category is None and parent_ck:
        category = SKILL_TO_CATEGORY.get(parent_ck)

    if category is None and parent_ck:
        # Walk up one more level (e.g. react -> javascript -> Frontend)
        for gp in IMPLICATIONS.get(parent_ck, set()):
            cat = SKILL_TO_CATEGORY.get(gp)
            if cat:
                category = cat
                break

    return (display, parent_display, category)



def get_fts_expansion_terms(skill: str) -> list[str]:
    """Return all variant spellings for a skill for FTS OR-query expansion.

    Input:
        skill -> raw or canonical skill name

    Output:
        Deduplicated list of known variants (including the input itself).
        Returns [skill] if the skill is not found in the alias table.

    Example:
        "React"   -> ["React", "react.js", "reactjs", "react js"]
        "Postgres" -> ["Postgres", "postgresql", "postgres", "psql", "pg"]
        "Unknown" -> ["Unknown"]
    """
    ck = resolve_canonical(skill)
    variants = ALIASES_OF.get(ck)
    if variants:
        # Prepend the raw input; deduplicate while preserving order
        seen: set[str] = set()
        result: list[str] = []
        for term in [skill] + variants:
            if term.lower() not in seen:
                seen.add(term.lower())
                result.append(term)
        return result
    return [skill]
