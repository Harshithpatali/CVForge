from app.services.jd_parser import analyze_jd, normalize_job_title


def test_long_opening_paragraph_does_not_become_job_title():
    jd = """The Data Scientist solves analytical and business problems using quantitative,
statistical, mathematical, and technical approaches. This role researches, develops,
and applies statistical and predictive modeling techniques to support business decisions,
improve processes, and deliver project-specific outcomes. The successful candidate will
work with Python, SQL, machine learning, and large datasets."""

    job = analyze_jd(jd)

    assert job.title == "Data Scientist"
    assert len(job.title) <= 255


def test_normalize_job_title_keeps_seniority():
    jd = "The Senior Data Scientist will develop predictive models and analytical solutions."

    assert normalize_job_title(jd.splitlines()[0], jd) == "Senior Data Scientist"
