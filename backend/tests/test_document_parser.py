from app.services.document_parser import extract_text, parse_candidate


def test_parse_latex_cv_extracts_project_links():
    latex = r"""
    \section{Selected Data Science Projects}
    \textbf{Fraud Graph Intelligence} \href{https://github.com/user/fraud-graph}{GitHub}
    \href{https://fraud-demo.streamlit.app}{Live Demo}
    \begin{itemize}
    \item Built a graph-based fraud detection pipeline.
    \item Trained an XGBoost classifier and evaluated precision-recall.
    \end{itemize}
    """

    candidate = parse_candidate(latex, "resume.tex")

    assert candidate.projects
    project = candidate.projects[0]
    assert project.name == "Fraud Graph Intelligence"
    urls = {link.url for link in project.links}
    assert "https://github.com/user/fraud-graph" in urls
    assert "https://fraud-demo.streamlit.app" in urls


def test_extract_text_accepts_latex():
    source = r"Name \\textbf{Candidate} \\section{Projects}"
    text = extract_text(source.encode(), "resume.tex")
    assert "section" in text.lower()


def test_project_repository_not_promoted_to_profile_github():
    latex = r"""
    Candidate Name
    https://github.com/user/project-one

    \section{Projects}
    \textbf{Project One}
    \href{https://github.com/user/project-one}{GitHub}
    """
    candidate = parse_candidate(latex, "resume.tex")

    assert candidate.contact.github == ""
    assert candidate.projects
    assert candidate.projects[0].links
    assert candidate.projects[0].links[0].url == "https://github.com/user/project-one"
