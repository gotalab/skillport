import json
from typing import List, Optional, Any, Dict
import lancedb
from lancedb.pydantic import LanceModel
from .config import settings
from .utils import parse_frontmatter
import openai
from google import genai

import sys

# --- Embedding Handling ---

def get_embedding(text: str) -> Optional[List[float]]:
    """
    Provider-agnostic embedding fetcher.
    """
    if settings.embedding_provider == "none":
        return None

    provider = settings.embedding_provider
    text = text.replace("\n", " ")

    try:
        if provider == "openai":
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required when embedding_provider='openai'")
            client = openai.Client(api_key=settings.openai_api_key)
            response = client.embeddings.create(input=[text], model=settings.embedding_model)
            return response.data[0].embedding

        if provider == "gemini":
            if not settings.gemini_api_key:
                raise ValueError("GEMINI_API_KEY is required when embedding_provider='gemini'")
            client = genai.Client(api_key=settings.gemini_api_key)
            result = client.models.embed_content(
                model=settings.gemini_embedding_model,
                contents=text,
            )
            # google-genai returns embeddings list with .values
            if result.embeddings:
                return list(result.embeddings[0].values)
            raise ValueError("Gemini embedding response missing embeddings")

        raise ValueError(f"Unsupported embedding_provider: {provider}")

    except Exception as e:
        print(f"Embedding error ({provider}): {e}", file=sys.stderr)
        raise

# --- Schema ---

class SkillRecord(LanceModel):
    name: str
    description: str
    category: str = "" 
    tags: List[str] = []
    always_apply: bool = False 
    instructions: str
    path: str
    metadata: str # JSON string
    # Using List[float] allows flexibility for different embedding models (OpenAI: 1536, Gemini: 768, etc.)
    # without strict schema validation failures on dimension mismatch during development/model switching.
    vector: Optional[List[float]] = None

    # For FTS we need to specify which fields. LanceDB 0.1+ supports FTS.
    
# --- DB Manager ---

class SkillDB:
    def __init__(self):
        self.db_path = settings.get_effective_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = lancedb.connect(self.db_path)
        self.table_name = "skills"
        # lightweight query normalization
        self._normalize = lambda q: " ".join(q.strip().split())

    def _norm_token(self, value: str) -> str:
        """
        Lowercase + trim for category/tags normalization.
        Keeps original spelling for display elsewhere.
        """
        return " ".join(str(value).strip().split()).lower()

    def _get_table(self):
        if self.table_name in self.db.table_names():
            return self.db.open_table(self.table_name)
        return None

    def initialize_index(self):
        """
        Scans SKILLS_DIR and re-creates the index.
        """
        # Fail fast if embeddings are requested but credentials are missing to avoid
        # creating a broken table schema.
        if settings.embedding_provider == "openai" and not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when embedding_provider='openai'")
        if settings.embedding_provider == "gemini" and not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY is required when embedding_provider='gemini'")

        skills_dir = settings.get_effective_skills_dir()
        if not skills_dir.exists():
            print(f"Skills dir not found: {skills_dir}", file=sys.stderr)
            return

        records = []
        vectors_present = False
        
        # Walk through subdirectories
        for skill_path in skills_dir.iterdir():
            if skill_path.is_dir():
                skill_md = skill_path / "SKILL.md"
                if skill_md.exists():
                    meta, body = parse_frontmatter(skill_md)
                    
                    name = meta.get("name", skill_path.name)
                    description = meta.get("description", "")
                    category = meta.get("category", "")
                    tags = meta.get("tags", [])
                    always_apply = meta.get("alwaysApply", False)
                    if not isinstance(always_apply, bool):
                        always_apply = False

                    # Normalize category/tags for consistent search & filtering
                    category_norm = self._norm_token(category) if category else ""
                    tags_norm = []
                    if isinstance(tags, list):
                        tags_norm = [self._norm_token(t) for t in tags]
                    elif isinstance(tags, str):
                        tags_norm = [self._norm_token(tags)]
                    
                    # Combine for embedding
                    text_to_embed = f"{name} {description} {category_norm} {' '.join(tags_norm)}"
                    
                    vec = get_embedding(text_to_embed)
                    if vec:
                        vectors_present = True
                    
                    record = SkillRecord(
                        name=name,
                        description=description,
                        category=category_norm,
                        tags=tags_norm,
                        always_apply=always_apply,
                        instructions=body,
                        path=str(skill_path.absolute()),
                        metadata=json.dumps(meta),
                        vector=vec
                    )
                    records.append(record)

        if not records:
            return

        # Create or Overwrite table
        # We drop and recreate to handle schema changes or clean state easily for v0
        if self.table_name in self.db.table_names():
            self.db.drop_table(self.table_name)
            
        # Convert records to list of dicts to allow flexible schema inference
        # If provider is none, we want to ensure vector column is handled correctly (or omitted)
        data = []
        for r in records:
            d = r.model_dump()
            # FTS用にtagsを文字列化（LanceDB FTSはList[str]を受けない）
            if isinstance(d.get("tags"), list):
                d["tags_text"] = " ".join(d["tags"])
            else:
                d["tags_text"] = str(d.get("tags", ""))
            # If we have no vectors at all, drop the column to avoid schema inference issues.
            if not vectors_present:
                d.pop("vector", None)
            data.append(d)

        if not data:
            return

        self.db.create_table(self.table_name, data=data, mode="overwrite")
        
        # Create FTS index
        tbl = self.db.open_table(self.table_name)
        try:
            # Light, multilingual-friendly index (equal weights)
            tbl.create_fts_index(
                ["name", "description", "tags_text", "category"],
                replace=True,
                use_tantivy=True,
            )
        except Exception as e:
            print(f"FTS index creation failed (maybe already exists or not supported): {e}", file=sys.stderr)

        # Scalar indexes for filters
        try:
            tbl.create_scalar_index("category", index_type="BITMAP", replace=True)
        except Exception as e:
            print(f"Category scalar index creation failed: {e}", file=sys.stderr)
        try:
            tbl.create_scalar_index("tags", index_type="LABEL_LIST", replace=True)
        except Exception as e:
            print(f"Tags scalar index creation failed: {e}", file=sys.stderr)

    def _escape_sql_string(self, value: str) -> str:
        """
        Basic SQL escaping for string literals.
        """
        return value.replace("'", "''")

    def _build_prefilter(self) -> str:
        """
        Constructs a SQL WHERE clause based on enabled skills/categories settings.
        Returns empty string if no filters are active.
        """
        conditions = []
        
        if settings.skillhub_enabled_skills:
            safe_skills = [f"'{self._escape_sql_string(s)}'" for s in settings.skillhub_enabled_skills]
            conditions.append(f"name IN ({', '.join(safe_skills)})")
            
        if settings.skillhub_enabled_categories:
            safe_cats = [f"'{self._escape_sql_string(self._norm_token(c))}'" for c in settings.skillhub_enabled_categories]
            conditions.append(f"category IN ({', '.join(safe_cats)})")
            
        if not conditions:
            return ""
            
        # Union logic: Allow if match specific skill name OR specific category
        return " OR ".join(conditions)

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        tbl = self._get_table()
        if not tbl:
            return []

        # Use settings if defaults used (though limit comes as arg, usually from tool)
        # The tool definition might pass a limit. 
        # If the user didn't specify a limit in the tool call, it might be the default 5.
        # We'll stick to the passed limit but use config for threshold.
        threshold = settings.search_threshold
        
        query = self._normalize(query)
        prefilter = self._build_prefilter()
        
        # Fetch more candidates to allow for post-filtering
        fetch_limit = limit * 4 
        
        try:
            vec = get_embedding(query)
        except Exception as e:
            print(f"Embedding fetch failed, falling back to FTS: {e}", file=sys.stderr)
            vec = None
        
        results = []
        
        try:
            if vec:
                # Vector Search
                search_op = tbl.search(vec)
                if prefilter:
                    search_op = search_op.where(prefilter)
                results = search_op.limit(fetch_limit).to_list()
            else:
                # FTS Search
                try:
                    search_op = tbl.search(query, query_type="fts")
                    if prefilter:
                        search_op = search_op.where(prefilter)
                    results = search_op.limit(fetch_limit).to_list()
                except Exception as e:
                    # Fallback: simple substring match on name/description
                    print(f"FTS search failed, using substring fallback: {e}", file=sys.stderr)
                    search_op = tbl.search()
                    if prefilter:
                        search_op = search_op.where(prefilter)
                    rows = search_op.limit(fetch_limit * 3).to_list()
                    
                    qlow = query.lower()
                    results = []
                    for row in rows:
                        if qlow in str(row.get("name", "")).lower() or qlow in str(row.get("description", "")).lower():
                            row["_score"] = 0.1 # Fixed low score
                            results.append(row)
                            if len(results) >= fetch_limit:
                                break
        except Exception as e:
            print(f"Search error: {e}", file=sys.stderr)
            return []

        if not results:
            return []

        # Dynamic Filtering (Max-Ratio Normalization)
        # 1. Sort by score (descending) just in case
        results.sort(key=lambda x: x.get("_score", 0), reverse=True)
        
        # 2. Check heuristic: if hits <= 5, return all (up to limit)
        if len(results) <= 5:
            return results[:limit]
            
        # 3. Calculate ratios and filter
        top_score = results[0].get("_score", 0)
        if top_score <= 0:
             return results[:limit]

        filtered_results = []
        for res in results:
            score = res.get("_score", 0)
            ratio = score / top_score
            if ratio >= threshold:
                filtered_results.append(res)
            else:
                # Since sorted, we can break early if strictly monotonic, 
                # but FTS scores might be close. Safe to continue or break?
                # Sorted descending, so subsequent ratios will be lower.
                break
                
        return filtered_results[:limit]

    def get_skill(self, skill_name: str) -> Optional[Dict[str, Any]]:
        tbl = self._get_table()
        if not tbl:
            return None
        
        safe_name = self._escape_sql_string(skill_name)
        res = tbl.search().where(f"name = '{safe_name}'").limit(1).to_list()
        if res:
            return res[0]
        return None

    def get_core_skills(self) -> List[Dict[str, Any]]:
        tbl = self._get_table()
        if not tbl:
            return []
        # LanceDB doesn't support boolean literals easily in SQL sometimes, but True/False usually works.
        # Or we can use where string "always_apply = true"
        try:
            return tbl.search().where("always_apply = true").limit(100).to_list()
        except Exception as e:
            print(f"Error fetching core skills: {e}", file=sys.stderr)
            return []

db = SkillDB()
