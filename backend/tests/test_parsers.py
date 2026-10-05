from app.services.jd_parser import analyze_jd
from app.services.document_parser import parse_candidate

def test_jd_classifier():
    j=analyze_jd("Data Scientist\nRequired: Python, SQL, machine learning")
    assert j.role_family=="data_science"
    assert "python" in j.must_have_skills

def test_candidate_parse():
    c=parse_candidate("Jane Doe\njane@example.com\nSKILLS\nPython, SQL\nEDUCATION\nMIT", "x.txt")
    assert c.contact.email=="jane@example.com"
    assert "Python" in c.skills
