import re
from app.schemas.cv import JobProfile

ROLE_PATTERNS={
    "data_science": ["data scientist","machine learning scientist","applied scientist","data science"],
    "data_analytics": ["data analyst","business analyst","analytics analyst","product analyst"],
    "machine_learning": ["machine learning engineer","ml engineer","ai engineer","machine learning"],
    "data_engineering": ["data engineer","analytics engineer","data platform engineer"],
    "software": ["software engineer","backend engineer","full stack","frontend engineer","developer"],
    "finance": ["financial analyst","risk analyst","quantitative analyst","credit risk","finance"],
    "product": ["product manager","product analyst","product operations"],
    "marketing": ["marketing analyst","growth analyst","marketing"],
}
SENIORITY={"intern":["intern","internship"],"entry":["entry level","entry-level","junior","graduate","fresher","0-2 years"],"mid":["mid-level","mid level","2-5 years"],"senior":["senior","5+ years","6+ years","lead"],"staff":["staff","principal","director"]}
SKILLS=["python","sql","r","java","c++","javascript","typescript","aws","azure","gcp","docker","kubernetes","spark","hadoop","airflow","dbt","snowflake","databricks","pandas","numpy","scikit-learn","tensorflow","pytorch","xgboost","tableau","power bi","excel","statistics","machine learning","deep learning","nlp","llm","rag","langchain","postgresql","mysql","fastapi","react","git","github","terraform","mlflow","kafka","redis","sagemaker","vertex ai","openai"]

def classify(text: str, title: str):
    t=(title+" "+text).lower()
    role=max(ROLE_PATTERNS, key=lambda k: sum(x in t for x in ROLE_PATTERNS[k]))
    role=role if sum(x in t for x in ROLE_PATTERNS[role]) else "general"
    seniority="entry"
    for s, pats in SENIORITY.items():
        if any(p in t for p in pats): seniority=s; break
    domain="general"
    for d, pats in {"fintech":["banking","fintech","credit risk","capital"],"healthcare":["healthcare","clinical","medical"],"retail":["ecommerce","retail","customer"],"energy":["energy","oil","gas","shell"],"consulting":["consulting","client-facing"]}.items():
        if any(p in t for p in pats): domain=d; break
    return role, seniority, domain

def analyze_jd(text: str) -> JobProfile:
    text=text.strip(); lines=[x.strip() for x in text.splitlines() if x.strip()]
    title=lines[0] if lines else "Target Role"
    role,seniority,domain=classify(text,title)
    low=text.lower()
    found=[s for s in SKILLS if re.search(r"(?<!\w)"+re.escape(s)+r"(?!\w)", low)]
    must=[]; preferred=[]
    for skill in found:
        window=low[max(0,low.find(skill)-140):low.find(skill)+len(skill)+140]
        (must if any(w in window for w in ["required","must","minimum","need","strong"] ) else preferred).append(skill)
    keywords=list(dict.fromkeys(re.findall(r"\b[A-Za-z][A-Za-z0-9+#.-]{2,}\b", text)))[:120]
    return JobProfile(title=title,role_family=role,seniority=seniority,domain=domain,must_have_skills=must,preferred_skills=preferred,keywords=keywords,raw_text=text)
