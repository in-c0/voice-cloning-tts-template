import { useEffect, useMemo, useRef, useState } from 'react'
import { Play, Upload, Wand2, Cpu, Settings2, Rocket, Volume2 } from 'lucide-react'
import { synthesize, engines } from './lib/api'

type Engine = 'xtts' | 'dia'

export default function App() {
  const [engine, setEngine] = useState<Engine>('xtts')
  const [text, setText] = useState('This is my podcast intro. Thanks for listening!')
  const [reference, setReference] = useState<File | null>(null)
  const [language, setLanguage] = useState('en')
  const [seed, setSeed] = useState<number | ''>('')
  const [speed, setSpeed] = useState<number>(1.0)
  const [maxChars, setMaxChars] = useState<number>(280)
  const [pauseMs, setPauseMs] = useState<number>(120)
  const [splitStrategy, setSplitStrategy] = useState<'punct'|'none'>('punct')
  const [transcript, setTranscript] = useState('')
  const [consent, setConsent] = useState(false)

  const [loading, setLoading] = useState(false)
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const audioRef = useRef<HTMLAudioElement>(null)

  useEffect(() => {
    engines().then(console.log).catch(console.warn)
  }, [])

  const estimatedChunks = useMemo(() => {
    if (splitStrategy === 'none') return 1
    return Math.ceil(text.length / Math.max(50, maxChars))
  }, [text, splitStrategy, maxChars])

  async function onSubmit() {
    setLoading(true)
    setBlobUrl(null)
    try {
      const form = new FormData()
      form.append('engine', engine)
      form.append('text', text)
      form.append('language', language)
      if (seed !== '') form.append('seed', String(seed))
      form.append('speed', String(speed))
      form.append('max_chars', String(maxChars))
      form.append('pause_ms', String(pauseMs))
      form.append('split_strategy', splitStrategy)
      if (transcript) form.append('transcript', transcript)
      form.append('consent', String(consent))
      if (reference) form.append('reference', reference)

      const wav = await synthesize(form)
      const url = URL.createObjectURL(wav)
      setBlobUrl(url)
      setTimeout(() => audioRef.current?.play(), 200)
    } catch (e: any) {
      alert(e.message || 'Synthesis failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen">
      <header className="max-w-5xl mx-auto px-6 py-8 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="badge"><Cpu size={16}/> Voice SaaS Template</div>
          <div className="hidden md:block text-sm text-white/60">XTTS‑v2 + Dia (optional)</div>
        </div>
        <a href="https://github.com" target="_blank" className="text-sm text-white/60 hover:text-white">Star the repo</a>
      </header>

      <main className="max-w-5xl mx-auto px-6 grid md:grid-cols-2 gap-6">
        <section className="card space-y-4">
          <div>
            <div className="label">Engine</div>
            <div className="flex gap-2">
              <button className={`btn ${engine==='xtts'?'':'opacity-60'}`} onClick={()=>setEngine('xtts')}><Wand2 className="mr-2" size={16}/> XTTS‑v2</button>
              <button className={`btn ${engine==='dia'?'':'opacity-60'}`} onClick={()=>setEngine('dia')}><Rocket className="mr-2" size={16}/> Dia (exp.)</button>
            </div>
          </div>

          <div>
            <div className="label">Your script</div>
            <textarea className="input h-40" value={text} onChange={(e)=>setText(e.target.value)} />
            <div className="text-xs text-white/50 mt-1">Estimated chunks: {estimatedChunks}</div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <div className="label">Reference (5–10s, WAV/MP3)</div>
              <input className="input" type="file" accept="audio/*" onChange={e=>setReference(e.target.files?.[0]||null)} />
            </div>
            <div>
              <div className="label">Language</div>
              <select className="input" value={language} onChange={e=>setLanguage(e.target.value)}>
                <option value="en">English</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <div className="label">Seed</div>
              <input className="input" type="number" placeholder="optional" value={seed} onChange={e=>setSeed(e.target.value===''? '': Number(e.target.value))} />
            </div>
            <div>
              <div className="label">Speed</div>
              <input className="input" type="number" step="0.05" min="0.5" max="1.5" value={speed} onChange={e=>setSpeed(Number(e.target.value))} />
            </div>
            <div>
              <div className="label">Pause (ms)</div>
              <input className="input" type="number" min="0" max="2000" value={pauseMs} onChange={e=>setPauseMs(Number(e.target.value))} />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <div className="label">Chunk strategy</div>
              <select className="input" value={splitStrategy} onChange={e=>setSplitStrategy(e.target.value as any)}>
                <option value="punct">By punctuation (~{maxChars} chars)</option>
                <option value="none">No chunking</option>
              </select>
            </div>
            <div>
              <div className="label">Max chars / chunk</div>
              <input className="input" type="number" min="120" max="1200" value={maxChars} onChange={e=>setMaxChars(Number(e.target.value))} />
            </div>
          </div>

          <div>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={consent} onChange={e=>setConsent(e.target.checked)} />
              I confirm this is my voice or I have consent to use it.
            </label>
          </div>

          <button disabled={loading || !consent} className="btn w-full py-3" onClick={onSubmit}>
            {loading ? 'Synthesizing…' : <><Play className="mr-2" size={16}/> Synthesize</>}
          </button>
        </section>

        <section className="card space-y-4">
          <div className="flex items-center justify-between">
            <div className="text-white/80 font-medium">Output</div>
            <div className="badge"><Settings2 size={14}/> Chunking + seed control</div>
          </div>
          <div className="rounded-xl bg-black/30 p-4 min-h-[200px] flex items-center justify-center">
            {blobUrl ? (
              <div className="w-full">
                <audio ref={audioRef} controls className="w-full" src={blobUrl}></audio>
                <div className="mt-3 flex gap-2">
                  <a className="btn" href={blobUrl} download="speech.wav"><Volume2 className="mr-2" size={16}/> Download WAV</a>
                </div>
              </div>
            ) : (
              <div className="text-white/50">Run synthesis to preview audio here.</div>
            )}
          </div>

          <div>
            <div className="label">Optional: Transcript for voice prompt (Dia)</div>
            <textarea className="input h-24" placeholder="[S1] <transcript of your 5–10s audio> ..." value={transcript} onChange={e=>setTranscript(e.target.value)} />
            <p className="text-xs text-white/50 mt-1">
              For Dia cloning, prepend the transcript before your script. For single speaker, always tag with [S1].
            </p>
          </div>

          <div className="text-xs text-white/40">
            Tip: For long scripts, keep chunk size 200–400 chars for stable prosody. Increase pause if joins feel abrupt.
          </div>
        </section>
      </main>

      <footer className="max-w-5xl mx-auto px-6 py-10 text-center text-sm text-white/50">
        Built for the 25‑Weekly‑SaaS challenge • MIT
      </footer>
    </div>
  )
}
