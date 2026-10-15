from __future__ import annotations
import re
from typing import Any
from rapidfuzz import fuzz

from app.services.enhanced.ai_adjudicator import adjudicate_candidate, should_adjudicate

BASE_WEIGHTS = {
    "required_skills": 30.0,
    "experience_relevance": 25.0,
    "role_responsibilities": 20.0,
    "keywords_ats": 10.0,
    "education_certifications": 10.0,
    "work_preferences": 5.0,
}

RECOMMENDED_MIN_SCORE = 75.0
REVIEW_MIN_SCORE = 55.0
RECOMMENDED_MIN_SKILL_RATIO = 0.60
RECOMMENDED_MIN_ROLE_RELEVANCE = 0.60
REVIEW_MIN_SKILL_RATIO = 0.30
REVIEW_MIN_ROLE_RELEVANCE = 0.40
MINIMUM_ROLE_RELEVANCE_FOR_REVIEW = 0.35
EXPERIENCE_REVIEW_TOLERANCE_YEARS = 1.0

SKILL_FUZZY_THRESHOLD = 88
ATS_FUZZY_THRESHOLD = 88
RESPONSIBILITY_FUZZY_THRESHOLD = 78
EDUCATION_FUZZY_THRESHOLD = 88
CERTIFICATION_FUZZY_THRESHOLD = 90

ALIASES = {
    "scikitlearn": {"scikit learn", "scikit-learn", "sklearn"},
    "reactjs": {"react", "react.js"},
    "nodejs": {"node", "node.js"},
    "postgresql": {"postgres", "postgre sql"},
    "javascript": {"js", "java script"},
    "typescript": {"ts", "type script"},
    "dotnet": {".net", "net core", ".net core"},
    "powerbi": {"power bi"},
    "aws": {"amazon web services"},
    "azure": {"microsoft azure"},
    "gcp": {"google cloud", "google cloud platform"},
}

def normalize_text(value: Any) -> str:
    if value is None: return ""
    text = str(value).strip()
    if not text: return ""
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text).lower().replace("&", " and ")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9+#.\s]", " ", re.sub(r"[-_/]", " ", text))).strip()

def compact_text(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", normalize_text(value))

def safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []

def unique_preserve_order(values: list[Any]) -> list[str]:
    seen, output = set(), []
    for value in values or []:
        text = str(value or "").strip()
        key = normalize_text(text)
        if text and key not in seen:
            seen.add(key)
            output.append(text)
    return output

def safe_float(value: Any) -> float | None:
    try:
        if value is None: return None
        if isinstance(value, str) and value.strip().lower() in {"", "none", "null", "na", "n/a", "not specified"}: return None
        return float(value)
    except (TypeError, ValueError): return None

def extract_titles(values: Any) -> list[str]:
    titles = []
    for item in safe_list(values):
        title = item.get("title") or item.get("job_title") or item.get("designation") or item.get("degree") or "" if isinstance(item, dict) else str(item)
        if str(title).strip(): titles.append(str(title).strip())
    return unique_preserve_order(titles)

def extract_candidate_skills(cv: dict[str, Any]) -> list[str]:
    output = []
    for s in safe_list(cv.get("skills")):
        output.append(s.get("name") or s.get("skill_name") or "" if isinstance(s, dict) else str(s))
    return unique_preserve_order(output)

def extract_experience_titles(cv: dict[str, Any]) -> list[str]:
    return extract_titles(cv.get("experiences", []))

def total_experience_years(cv: dict[str, Any]) -> float:
    parsed = safe_float(cv.get("total_experience"))
    if parsed is not None and parsed >= 0: return round(parsed, 2)
    total = 0.0
    for item in safe_list(cv.get("experiences")):
        if isinstance(item, dict):
            val = safe_float(item.get("experience_in_years") or item.get("years") or item.get("experienceinyears"))
            if val and val > 0: total += val
    return round(total, 2)

def alias_set(value: str) -> set[str]:
    normalized, compact = normalize_text(value), compact_text(value)
    aliases = {normalized, compact}
    for key, values in ALIASES.items():
        if normalized == normalize_text(key) or compact == compact_text(key) or normalized in {normalize_text(v) for v in values} or compact in {compact_text(v) for v in values}:
            aliases.update([normalize_text(key), compact_text(key)] + [normalize_text(v) for v in values] + [compact_text(v) for v in values])
    return {item for item in aliases if item}

def deterministic_text_match(requirement: str, candidate_value: str, fuzzy_threshold: int) -> tuple[bool, float, str]:
    if alias_set(requirement) & alias_set(candidate_value): return True, 1.0, "exact_or_alias"
    req_norm, candidate_norm = normalize_text(requirement), normalize_text(candidate_value)
    if not req_norm or not candidate_norm: return False, 0.0, "none"
    req_comp, cand_comp = compact_text(requirement), compact_text(candidate_value)
    if len(req_comp) >= 3 and len(cand_comp) >= 3 and (cand_comp.startswith(req_comp) or cand_comp.endswith(req_comp)): return True, 1.0, "contains"
    ratio = max(fuzz.ratio(req_norm, candidate_norm), fuzz.token_sort_ratio(req_norm, candidate_norm), fuzz.token_set_ratio(req_norm, candidate_norm))
    return ratio >= fuzzy_threshold, ratio / 100.0, "fuzzy"

def _clean_bullet_line(value: Any) -> str:
    return re.sub(r"^[\-•*▪◦–—]+\s*", "", str(value or "").strip()).strip()

def _split_or_skill(value: Any) -> list[str]:
    text = _clean_bullet_line(value)
    if not text: return []
    return unique_preserve_order([part.strip(" ,.;") for part in re.split(r"\s+or\s+|\s+/\s+", text, flags=re.IGNORECASE)])

def extract_skill_groups(jd: dict[str, Any]) -> list[dict[str, Any]]:
    groups, covered = [], set()
    def add_group(raw_value: Any, required: bool) -> None:
        alternatives = _split_or_skill(raw_value)
        alt_keys = {compact_text(i) for i in alternatives if compact_text(i)}
        if not alt_keys or any(tuple(sorted(i["alternative_keys"])) == tuple(sorted(alt_keys)) for i in groups): return
        groups.append({"label": " or ".join(alternatives), "alternatives": alternatives, "alternative_keys": alt_keys, "required": required, "mandatory": required, "weight": 1.0})
        covered.update(alt_keys)
    for s in safe_list(jd.get("mandatory_skills")): add_group(s, True)
    for s in safe_list(jd.get("preferred_skills")): add_group(s, False)
    return groups

def required_skill_score(jd: dict[str, Any], candidate_skills: list[str]) -> dict[str, Any]:
    groups = extract_skill_groups(jd)
    if not groups: return {"active": False, "ratio": None, "matched": [], "missing": [], "matched_preferred": [], "missing_preferred": [], "core_skill_match": True, "matched_core_skills": [], "missing_core_skills": [], "required_groups": [], "preferred_groups": []}
    matched, missing, matched_pref, missing_pref, matched_core, missing_core = [], [], [], [], [], []
    req_tot, req_earn, pref_tot, pref_earn = 0.0, 0.0, 0.0, 0.0
    for g in groups:
        w = g["weight"]
        best = None
        for alt in g["alternatives"]:
            for cs in candidate_skills:
                is_match, score, method = deterministic_text_match(alt, cs, SKILL_FUZZY_THRESHOLD)
                if is_match and (not best or score > best["score"]): best = {"required": g["label"], "matched_alternative": alt, "candidate": cs, "score": score, "method": method}
        if g["required"]:
            req_tot += w
            if best: req_earn += w * best["score"]; matched.append(best); matched_core.append(g["label"])
            else: missing.append(g["label"]); missing_core.append(g["label"])
        else:
            pref_tot += w
            if best: pref_earn += w * best["score"]; matched_pref.append(best)
            else: missing_pref.append(g["label"])
    req_ratio = req_earn / req_tot if req_tot else None
    pref_ratio = pref_earn / pref_tot if pref_tot else None
    ratio = (req_ratio * 0.90) + (pref_ratio * 0.10) if req_ratio is not None and pref_ratio is not None else req_ratio if req_ratio is not None else pref_ratio if pref_ratio is not None else 0.0
    return {"active": True, "ratio": round(ratio, 4), "required_ratio": req_ratio, "preferred_ratio": pref_ratio, "matched": matched, "missing": missing, "matched_preferred": matched_pref, "missing_preferred": missing_pref, "core_skill_match": len(missing_core) == 0, "matched_core_skills": matched_core, "missing_core_skills": missing_core, "required_groups": [g["label"] for g in groups if g["required"]], "preferred_groups": [g["label"] for g in groups if not g["required"]]}

def experience_fit(candidate_years: float, minimum: Any, maximum: Any) -> dict[str, Any]:
    min_exp, max_exp = safe_float(minimum), safe_float(maximum)
    if min_exp is None and max_exp is None: return {"fit": "not_specified", "score": 1.0, "gap_years": 0.0, "within_range": True, "active": False}
    if min_exp is not None and candidate_years < min_exp:
        gap = round(min_exp - candidate_years, 2)
        return {"fit": "near_range" if gap <= EXPERIENCE_REVIEW_TOLERANCE_YEARS else "far_outside", "score": 0.55 if gap <= EXPERIENCE_REVIEW_TOLERANCE_YEARS else 0.0, "gap_years": gap, "within_range": False, "active": True}
    if max_exp is not None and candidate_years > max_exp:
        gap = round(candidate_years - max_exp, 2)
        return {"fit": "near_range" if gap <= EXPERIENCE_REVIEW_TOLERANCE_YEARS else "far_outside", "score": 0.55 if gap <= EXPERIENCE_REVIEW_TOLERANCE_YEARS else 0.0, "gap_years": gap, "within_range": False, "active": True}
    return {"fit": "in_range", "score": 1.0, "gap_years": 0.0, "within_range": True, "active": True}

def best_role_similarity(jd_title: str, candidate_titles: list[str]) -> tuple[float, str | None]:
    jd_norm = normalize_text(jd_title)
    if not jd_norm or not candidate_titles: return 0.0, None
    best_score, best_candidate = 0.0, None
    for ct in candidate_titles:
        cn = normalize_text(ct)
        if not cn: continue
        ratio = max(fuzz.ratio(jd_norm, cn), fuzz.token_sort_ratio(jd_norm, cn), fuzz.token_set_ratio(jd_norm, cn)) / 100.0
        if ratio > best_score: best_score, best_candidate = ratio, ct
    return round(best_score, 4), best_candidate

def experience_relevance_score(jd: dict[str, Any], cv: dict[str, Any]) -> dict[str, Any]:
    years = total_experience_years(cv)
    fit = experience_fit(years, jd.get("minimum_experience"), jd.get("maximum_experience"))
    jd_title = str(jd.get("job_title") or "").strip()
    titles = unique_preserve_order([str(cv.get("designation") or "")] + extract_experience_titles(cv))
    title_active = bool(normalize_text(jd_title))
    title_score, matched_title = best_role_similarity(jd_title, titles)
    components = []
    if fit["active"]: components.append((float(fit["score"]), 0.45))
    if title_active: components.append((title_score, 0.40))
    if not components: return {"active": False, "ratio": None, "candidate_years": years, "experience_fit": fit["fit"], "experience_gap_years": fit["gap_years"], "within_experience_range": fit["within_range"], "title_active": False, "title_score": None}
    tot_w = sum(w for _, w in components)
    return {"active": True, "ratio": round(sum(s * w for s, w in components) / tot_w, 4), "candidate_years": years, "years_score": fit["score"] if fit["active"] else None, "experience_fit": fit["fit"], "experience_gap_years": fit["gap_years"], "within_experience_range": fit["within_range"], "title_active": title_active, "title_score": round(title_score, 4) if title_active else None, "matched_candidate_title": matched_title}

def extract_responsibilities(jd: dict[str, Any]) -> list[dict[str, Any]]:
    output = []
    for r in safe_list(jd.get("responsibilities")): output.append({"text": str(r), "importance": "normal", "weight": 2.0})
    text = str(jd.get("jd_text_description") or "")
    if text:
        active = False
        for line in text.splitlines():
            h = normalize_text(line.rstrip(":"))
            if h in {"responsibilities", "key responsibilities", "duties"}: active = True; continue
            if h in {"required skills", "preferred skills", "education", "location"} or (line.endswith(":") and active): active = False; continue
            if active and normalize_text(_clean_bullet_line(line)): output.append({"text": _clean_bullet_line(line), "importance": "normal", "weight": 2.0})
    dedup = {}
    for i in output:
        key = normalize_text(i["text"])
        if key not in dedup or i["weight"] > dedup[key]["weight"]: dedup[key] = i
    return list(dedup.values())

def _flatten_evidence_strings(value: Any, depth: int = 0) -> list[str]:
    if depth > 3: return []
    if isinstance(value, str): return [p.strip() for p in re.split(r"[\n\r]+|(?<=[.!?])\s+", value) if p.strip()]
    if isinstance(value, list): return [i for sub in value for i in _flatten_evidence_strings(sub, depth + 1)]
    if isinstance(value, dict): return [i for k, v in value.items() if normalize_text(k) not in {"email", "phone", "linkedin"} for i in _flatten_evidence_strings(v, depth + 1)]
    return []

def extract_candidate_evidence_chunks(cv: dict[str, Any]) -> list[str]:
    chunks = [str(cv.get("about_me") or ""), str(cv.get("designation") or "")] + extract_candidate_skills(cv) + extract_experience_titles(cv) + _flatten_evidence_strings(cv.get("experiences", [])) + _flatten_evidence_strings(cv.get("cv_text_description") or "")
    return unique_preserve_order([c[:1200] for c in chunks if normalize_text(c)])

RESPONSIBILITY_STOPWORDS = {"a", "an", "and", "the", "to", "of", "for", "with", "using", "use", "in", "on"}
def _responsibility_evidence_match(req: str, chunks: list[str]) -> tuple[bool, float, str, str | None]:
    if not chunks: return False, 0.0, "none", None
    req_tok = {t for t in normalize_text(req).split() if t not in RESPONSIBILITY_STOPWORDS and len(t) >= 3}
    all_tok, best_f, best_c = set(), 0.0, None
    for c in chunks:
        cn = normalize_text(c)
        if not cn: continue
        all_tok.update({t for t in cn.split() if t not in RESPONSIBILITY_STOPWORDS and len(t) >= 3})
        score = max(fuzz.token_set_ratio(normalize_text(req), cn), fuzz.token_sort_ratio(normalize_text(req), cn)) / 100.0
        if score > best_f: best_f, best_c = score, c
    cov = len(req_tok & all_tok) / len(req_tok) if req_tok else 0.0
    comb = max(best_f, (cov * 0.8) + (best_f * 0.2))
    return comb >= 0.60, round(comb, 4), "evidence_coverage" if cov > best_f else "fuzzy_evidence", best_c

def responsibility_score(jd: dict[str, Any], cv: dict[str, Any]) -> dict[str, Any]:
    resps = extract_responsibilities(jd)
    if not resps: return {"active": False, "ratio": None, "matched": [], "missing": []}
    chunks = extract_candidate_evidence_chunks(cv)
    matched, missing, tot, earn = [], [], 0.0, 0.0
    for r in resps:
        tot += r["weight"]
        is_m, s, m, ev = _responsibility_evidence_match(r["text"], chunks)
        if is_m: earn += r["weight"] * s; matched.append({"responsibility": r["text"], "score": s, "method": m, "evidence": (ev or "")[:500]})
        else: missing.append({"responsibility": r["text"]})
    return {"active": True, "ratio": round(earn / tot if tot else 0.0, 4), "matched": matched, "missing": missing, "responsibility_count": len(resps)}

def extract_ats_keywords(jd: dict[str, Any]) -> list[dict[str, Any]]:
    kws = []
    def add(alts: list[str], w: float, src: str, disp: str | None = None):
        a = unique_preserve_order(alts)
        if a: kws.append({"text": disp or " or ".join(a), "alternatives": a, "weight": w, "source": src})
    for g in extract_skill_groups(jd): add(g["alternatives"], 3.0 if g["required"] else 1.0, "required_skill" if g["required"] else "preferred_skill", g["label"])
    if normalize_text(jd.get("job_title")): add([str(jd.get("job_title"))], 3.0, "job_title")
    if safe_list(jd.get("education")): add(safe_list(jd.get("education")), 1.5, "education")
    for c in safe_list(jd.get("certifications")): add([str(c)], 2.0, "certification")
    if normalize_text(jd.get("location")): add([str(jd.get("location"))], 1.0, "location")
    dedup = {}
    for k in kws:
        key = tuple(sorted(compact_text(v) for v in k["alternatives"] if compact_text(v)))
        if key and (key not in dedup or k["weight"] > dedup[key]["weight"]): dedup[key] = k
    return list(dedup.values())

def ats_score(jd: dict[str, Any], cv: dict[str, Any], candidate_skills: list[str]) -> dict[str, Any]:
    kws = extract_ats_keywords(jd)
    if not kws: return {"active": False, "ratio": None, "matched": [], "missing": []}
    blob_norm = normalize_text(" ".join(str(p) for p in [cv.get("about_me"), cv.get("fullname"), cv.get("designation"), cv.get("cv_text_description")] + candidate_skills + extract_experience_titles(cv) if p))
    chunks = extract_candidate_evidence_chunks(cv)
    matched, missing, tot, earn = [], [], 0.0, 0.0
    for k in kws:
        tot += k["weight"]; bs, bm, ba = 0.0, "none", None
        for a in k["alternatives"]:
            if any(an in blob_norm for an in alias_set(a) if an): bs, bm, ba = 1.0, "exact_or_alias", a; break
            for c in chunks:
                im, s, m = deterministic_text_match(a, c, ATS_FUZZY_THRESHOLD)
                if im and s > bs: bs, bm, ba = s, m, a
        if bs > 0: earn += k["weight"] * bs; matched.append({"keyword": k["text"], "matched_alternative": ba, "weight": k["weight"], "score": round(bs, 4)})
        else: missing.append({"keyword": k["text"]})
    return {"active": True, "ratio": round(earn / tot if tot else 0.0, 4), "matched": matched, "missing": missing}

def education_certification_score(jd: dict[str, Any], cv: dict[str, Any]) -> dict[str, Any]:
    jde, jdc = unique_preserve_order(safe_list(jd.get("education"))), unique_preserve_order(safe_list(jd.get("certifications")))
    if not jde and not jdc: return {"active": False, "ratio": None, "education": {"active": False}, "certifications": {"active": False}}
    ce, cc = extract_titles(cv.get("education", [])), extract_titles(cv.get("certifications", []))
    er = {"active": True, "ratio": 1.0 if not jde else max([max([fuzz.token_set_ratio(normalize_text(r), normalize_text(c)) for c in ce] + [0]) for r in jde]) / 100.0} if jde else {"active": False}
    cr = {"active": True, "ratio": 1.0 if not jdc else sum([max([fuzz.token_set_ratio(normalize_text(r), normalize_text(c)) for c in cc] + [0]) for r in jdc]) / (len(jdc) * 100.0)} if jdc else {"active": False}
    comps = []
    if er.get("active"): comps.append((er["ratio"], 0.6))
    if cr.get("active"): comps.append((cr["ratio"], 0.4))
    tot = sum(w for _, w in comps)
    return {"active": True, "ratio": round(sum(s * w for s, w in comps) / tot if tot else 0.0, 4), "education": er, "certifications": cr}

def work_preferences_score(jd: dict[str, Any], cv: dict[str, Any]) -> dict[str, Any]:
    comps, dets = [], {}
    jdl = normalize_text(jd.get("location"))
    if jdl:
        cl = normalize_text(cv.get("location"))
        ls = 1.0 if "remote" in jdl or jdl == cl else 0.75 if set(jdl.split()) & set(cl.split()) else 0.25 if cl else 0.5
        comps.append((ls, 0.6)); dets["location_score"] = ls
    jdw = normalize_text(jd.get("work_mode") or jd.get("work_arrangement"))
    if jdw:
        cw = normalize_text(cv.get("work_mode") or cv.get("work_arrangement"))
        ws = 1.0 if jdw == cw else 0.5
        comps.append((ws, 0.4)); dets["work_mode_score"] = ws
    if not comps: return {"active": False, "ratio": None, **dets}
    tot = sum(w for _, w in comps)
    return {"active": True, "ratio": round(sum(s * w for s, w in comps) / tot, 4), **dets}

def calculate_score(jd: dict[str, Any], cv: dict[str, Any]) -> dict[str, Any]:
    cs = extract_candidate_skills(cv)
    cats = {
        "required_skills": required_skill_score(jd, cs),
        "experience_relevance": experience_relevance_score(jd, cv),
        "role_responsibilities": responsibility_score(jd, cv),
        "keywords_ats": ats_score(jd, cv, cs),
        "education_certifications": education_certification_score(jd, cv),
        "work_preferences": work_preferences_score(jd, cv),
    }
    aw, wp = 0.0, 0.0
    for n, r in cats.items():
        if r.get("active"):
            bw = BASE_WEIGHTS[n]
            aw += bw
            wp += float(r.get("ratio") or 0.0) * bw
    fs = round((wp / aw) * 100.0 if aw > 0 else 0.0, 2)
    bd = {n: {"score": round((float(r.get("ratio") or 0.0) * (BASE_WEIGHTS[n] / aw) * 100.0), 2) if r.get("active") and aw > 0 else 0.0, "out_of": round((BASE_WEIGHTS[n] / aw) * 100.0, 2) if aw > 0 else 0.0, "active": bool(r.get("active"))} for n, r in cats.items()}
    
    req, exp = cats["required_skills"], cats["experience_relevance"]
    csm = bool(req.get("core_skill_match", True))
    efit = str(exp.get("experience_fit") or "not_specified")
    sa, sr = bool(req.get("active")), float(req.get("ratio") or 0.0)
    ta, tr = bool(exp.get("title_active")), float(exp.get("title_score") or 0.0)

    st = "review"
    rsn = []

    if not csm:
        missing = req.get("missing_core_skills", [])[:5]
        rsn.append(f"Missing mandatory skills: {', '.join(missing)}")
        st = "not recommended"

    if efit in {"far_outside", "near_range"}:
        min_e, max_e = safe_float(jd.get("minimum_experience")), safe_float(jd.get("maximum_experience"))
        c_years = exp.get("candidate_years")
        if min_e is not None and max_e is not None:
            rsn.append(f"Experience ({c_years} yrs) is outside the requested range ({min_e}-{max_e} yrs)")
        elif min_e is not None:
            rsn.append(f"Experience ({c_years} yrs) is below the required minimum ({min_e} yrs)")
        elif max_e is not None:
            rsn.append(f"Experience ({c_years} yrs) exceeds the required maximum ({max_e} yrs)")
        if efit == "far_outside":
            st = "not recommended"

    if ta and tr is not None and tr < MINIMUM_ROLE_RELEVANCE_FOR_REVIEW:
        rsn.append("Role titles do not align closely with the requested job")
        st = "not recommended"

    if not rsn:
        if fs >= RECOMMENDED_MIN_SCORE and (not sa or sr >= RECOMMENDED_MIN_SKILL_RATIO) and (not ta or tr >= RECOMMENDED_MIN_ROLE_RELEVANCE) and efit in {"in_range", "not_specified"}:
            st, rsn = "recommended", ["Strong overall fit across the available job requirements."]
        elif fs >= REVIEW_MIN_SCORE and ((not sa or sr >= REVIEW_MIN_SKILL_RATIO) or (not ta or tr >= REVIEW_MIN_ROLE_RELEVANCE)):
            st, rsn = "review", ["The candidate shows relevant job-fit signals, but the overall profile should be reviewed manually."]
        else:
            st, rsn = "not recommended", ["Overall fit is below the minimum threshold required for manual review."]
    elif st != "not recommended" and fs < REVIEW_MIN_SCORE:
        st = "not recommended"
        rsn.append("Overall fit score is too low.")

    return {
        "final_score": fs,
        "recommendation_status": st,
        "recommendation_reason": rsn,
        "score_breakdown": bd,
        "debug_details": {"required_skills": req, "experience_relevance": exp, "role_responsibilities": cats["role_responsibilities"], "keywords_ats": cats["keywords_ats"], "education_certifications": cats["education_certifications"], "work_preferences": cats["work_preferences"]},
    }

def score_candidates(jd: dict[str, Any], candidates: list[dict[str, Any]], debug: bool = False) -> list[dict[str, Any]]:
    results = []
    for cv in candidates:
        if not isinstance(cv, dict): continue
        loc = calculate_score(jd, cv)
        ai_res = {"used": False, "status": None, "reason": "AI adjudication was not required for this candidate."}
        if should_adjudicate(loc): ai_res = adjudicate_candidate(jd=jd, cv=cv, local_result=loc)
        ds = "openai_adjudication" if ai_res.get("used") else "deterministic"
        bd = dict(loc["score_breakdown"])
        bd["decision_audit"] = {"decision_source": ds, "local_status": loc["recommendation_status"], "local_reason": loc["recommendation_reason"], "ai_used": bool(ai_res.get("used")), "ai_status": ai_res.get("status"), "ai_reason": ai_res.get("reason"), "ai_skill_findings": ai_res.get("skill_findings") or []}
        res = {
            "candidate_id": cv.get("id"),
            "candidate_name": cv.get("fullname") or cv.get("name"),
            "final_score": loc["final_score"],
            "recommendation_status": ai_res["status"] if ai_res.get("used") else loc["recommendation_status"],
            "recommendation_reason": ai_res["reason"] if ai_res.get("used") else loc["recommendation_reason"],
            "decision_source": ds,
            "local_recommendation_status": loc["recommendation_status"],
            "local_recommendation_reason": loc["recommendation_reason"],
            "ai_adjudication": ai_res,
            "score_breakdown": bd,
        }
        if debug: res["debug_details"] = loc["debug_details"]
        results.append(res)
    results.sort(key=lambda x: float(x.get("final_score") or 0.0), reverse=True)
    return results