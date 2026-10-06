import { useEffect, useMemo, useState } from 'react'
import { ArrowRight, CheckCircle2, FileText, Gauge, Github, Loader2, Sparkles, Target, Upload } from 'lucide-react'
import { analyzeAndGenerate, health } from './api'

const SAMPLE_JD = `Data Scientist — Customer Analytics

We are looking for a Data Scientist to build predictive models, analyze customer behavior, and work with product teams.

Requirements:
- Python and SQL
- pandas, scikit-learn
- Machine learning and statistics
- Experimentation / A/B testing
- Strong communication and business problem solving
- Experience working with large datasets and building production-ready analytics`

function scoreTone(score) {
  if (score >= 80) return 'excellent'
  if (score >= 65) return 'good'
  return 'needs-work'
}

export default function App() {
  const [jobDescription, setJobDescription] = useState('')
  const [cvText, setCvText] = useState('')
  const [cvFile, setCvFile] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [apiUp, setApiUp] = useState(false)

  useEffect(() => {
    health().then(() => setApiUp(true)).catch(() => setApiUp(false))
  }, [])

  async function submit(event) {
    event.preventDefault()
    setError('')
    if (!jobDescription.trim()) return setError('Paste the target job description first.')
    if (!cvText.trim() && !cvFile) return setError('Paste your CV text or upload a CV file.')

    setLoading(true)
    try {
      const data = await analyzeAndGenerate({ jobDescription, cvText, cvFile })
      setResult(data)
      window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })
    } catch (err) {
      setError(err.message || 'CV generation failed.')
    } finally {
      setLoading(false)
    }
  }

  const score = Number(result?.ats?.score ?? 0)
  const tone = useMemo(() => scoreTone(score), [score])

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <div className="logo"><Sparkles size={18} /></div>
          <div><b>CVForge</b><small>Evidence-first career tailoring</small></div>
        </div>
        <div className="status">
          <i className={apiUp ? 'online' : ''} />
          {apiUp ? 'Backend connected' : 'Checking backend'}
        </div>
      </header>

      <main>
        <section className="hero">
          <div className="eyebrow"><Target size={15} /> Truthful resume tailoring</div>
          <h1>Build a CV for the job you actually want.</h1>
          <p>CVForge reads the role, preserves your evidence, generates a targeted resume, and independently evaluates the result for ATS and job-match strength.</p>
        </section>

        <form onSubmit={submit} className="workspace">
          <section className="panel">
            <div className="panel-top">
              <div><span className="step">01</span><h2>Target job</h2></div>
              <button type="button" className="ghost" onClick={() => setJobDescription(SAMPLE_JD)}>Load sample</button>
            </div>
            <textarea value={jobDescription} onChange={e => setJobDescription(e.target.value)} placeholder="Paste the full job description here..." />
            <div className="meta"><span>{jobDescription.length.toLocaleString()} characters</span><span>Used for skill, keyword and responsibility analysis</span></div>
          </section>

          <section className="panel">
            <div className="panel-top">
              <div><span className="step">02</span><h2>Candidate evidence</h2></div>
              <label className="upload"><Upload size={15}/> Upload CV<input hidden type="file" accept=".pdf,.doc,.docx,.txt,.md" onChange={e => setCvFile(e.target.files?.[0] || null)} /></label>
            </div>
            {cvFile && <div className="file"><FileText size={14}/> {cvFile.name}</div>}
            <textarea value={cvText} onChange={e => setCvText(e.target.value)} placeholder="Or paste your current CV text. Pasted text takes precedence." />
            <div className="meta"><span>{cvText.length.toLocaleString()} characters</span><span>Unsupported claims are never invented</span></div>
          </section>

          {error && <div className="error">{error}</div>}

          <button className="primary" disabled={loading}>
            {loading ? <><Loader2 className="spin" size={18}/> Running CVForge...</> : <>Generate tailored CV <ArrowRight size={18}/></>}
          </button>
        </form>

        {loading && <div className="progress"><b><Loader2 className="spin" size={17}/> Pipeline running</b><div><span>Parse</span><span>Analyze</span><span>Generate</span><span>Evaluate</span></div></div>}

        {result && <section className="results">
          <div className="section-head"><div><div className="eyebrow"><CheckCircle2 size={15}/> Ready</div><h2>Your CVForge report</h2></div></div>
          <div className="score-grid">
            <div className="score-card"><Gauge size={20}/><strong className={tone}>{Math.round(score)}</strong><small>ATS / job match</small></div>
            <Metric label="Keyword coverage" value={result.ats?.keyword_coverage}/>
            <Metric label="Required skills" value={result.ats?.required_skill_coverage}/>
            <Metric label="Title alignment" value={result.ats?.title_alignment}/>
          </div>

          <div className="result-grid">
            <div className="result-panel"><span className="step">CV</span><h3>Generated resume</h3><ResumePreview resume={result.resume}/></div>
            <div className="result-panel"><span className="step">ATS</span><h3>Evaluation</h3><List title="Strengths" items={result.ats?.strengths}/><List title="Gaps" items={result.ats?.gaps}/><List title="Missing keywords" items={result.ats?.missing_keywords}/><List title="Recommendations" items={result.ats?.recommendations}/></div>
          </div>
        </section>}
      </main>

      <footer><span>CVForge · Cloudflare-ready React frontend</span><a href="https://github.com/Harshithpatali/CVForge" target="_blank" rel="noreferrer"><Github size={14}/> GitHub</a></footer>
    </div>
  )
}

function Metric({label, value}) {
  return <div className="metric"><small>{label}</small><strong>{Math.round(Number(value || 0))}%</strong></div>
}

function List({title, items}) {
  if (!items?.length) return null
  return <div className="list"><h4>{title}</h4>{items.slice(0,8).map((x,i)=><div key={i}>{x}</div>)}</div>
}

function ResumePreview({resume}) {
  if (!resume) return null
  return <div className="resume">
    <h3>{resume.name || 'Tailored Resume'}</h3>
    {resume.contact && <p className="muted">{resume.contact}</p>}
    {resume.summary && <><h5>SUMMARY</h5><p>{resume.summary}</p></>}
    {resume.skills?.length ? <><h5>SKILLS</h5><p>{Array.isArray(resume.skills) ? resume.skills.join(' · ') : resume.skills}</p></> : null}
    {resume.experience?.length ? <><h5>EXPERIENCE</h5>{resume.experience.slice(0,5).map((x,i)=><article key={i}><b>{x.title}</b><small>{x.company} {x.dates ? '· '+x.dates : ''}</small>{x.bullets?.slice(0,4).map((b,j)=><p key={j}>• {b}</p>)}</article>)}</> : null}
    {resume.projects?.length ? <><h5>PROJECTS</h5>{resume.projects.slice(0,5).map((x,i)=><article key={i}><b>{x.name}</b>{x.bullets?.slice(0,2).map((b,j)=><p key={j}>• {b}</p>)}</article>)}</> : null}
  </div>
}
