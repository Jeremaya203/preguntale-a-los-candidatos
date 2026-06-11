'use client';
import { useState, useRef, useEffect } from 'react';
import { parseTooltips } from '@/lib/parseTooltips';

type Screen    = 'welcome' | 'app';
type Tab       = 'chat' | 'analyze';
type Candidate = 'all' | 'ivan-cepeda' | 'abelardo';
type CharState = 'idle' | 'thinking' | 'responding';
interface Message { role:'user'|'assistant'; content:string; sources?: Source[]; }
interface Source  { title:string; tipo:string; candidato:string; lang:string; }

const CANDS = {
  'ivan-cepeda': { name:'Iván Cepeda Castro', alias:'El Jaguar', party:'Pacto Histórico',
    role:'Senador por Bogotá', slogan:'Me la juego por la vida',
    color:'#F0A020', colorBg:'rgba(240,160,32,0.08)', colorBorder:'rgba(240,160,32,0.25)',
    img:'/jaguar.png', char:'jaguar' as const },
  abelardo: { name:'Abelardo de la Espriella', alias:'El Tigre', party:'Colombia Renaciente',
    role:'Candidato presidencial', slogan:'Firme por la Patria',
    color:'#E05818', colorBg:'rgba(224,88,24,0.08)', colorBorder:'rgba(224,88,24,0.25)',
    img:'/tigre.png', char:'tigre' as const },
};

const DIMS = ['Educación','Salud','Economía','Paz y seguridad','Medio ambiente',
  'Empleo','Vivienda','Innovación','Agricultura','Justicia','Cultura','Infraestructura'];

const SUGGESTED = [
  '¿Cuáles son las propuestas de seguridad de Iván Cepeda?',
  '¿Qué propone Abelardo sobre la economía colombiana?',
  '¿Cómo aborda cada candidato el tema de la paz?',
  '¿Qué dicen sobre educación y ciencia?',
];

function useIsMobile(breakpoint = 768) {
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < breakpoint);
    check();
    window.addEventListener('resize', check);
    return () => window.removeEventListener('resize', check);
  }, [breakpoint]);
  return isMobile;
}

function parseSources(raw:string):{text:string;sources:Source[]}{
  const idx=raw.indexOf('<!--SOURCES:');
  if(idx===-1) return {text:raw,sources:[]};
  const text=raw.slice(0,idx).trim();
  const json=raw.slice(idx+12,raw.lastIndexOf('-->'));
  try{return{text,sources:JSON.parse(json)}}catch{return{text,sources:[]}}
}

// ─── CharPanel ──────────────────────────────────────────────────────────────
function CharPanel({char,state,active,color,maxSize=180}:{
  char:'jaguar'|'tigre'; state:CharState; active:boolean; color:string; maxSize?:number;
}){
  return(
    <div style={{flex:1,display:'flex',flexDirection:'column',alignItems:'center',gap:8,
      opacity:active?1:0.3,transition:'opacity 0.4s'}}>
      <div style={{position:'relative',width:'100%',maxWidth:maxSize,aspectRatio:'1'}}>
        <div style={{position:'absolute',inset:-2,border:`2px solid ${active?color:'#2A2A42'}`,
          boxShadow:active?`0 0 16px ${color}44`:'none',transition:'all 0.4s',pointerEvents:'none',zIndex:1}}/>
        {(['idle','thinking','responding'] as CharState[]).map(s=>(
          <video key={`${char}-${s}`} autoPlay loop muted playsInline
            src={`/${char}-${s}.mp4`}
            style={{position:s==='idle'?'relative':'absolute',inset:0,
              width:'100%',height:'100%',imageRendering:'pixelated',
              opacity:state===s?1:0,transition:'opacity 0.3s',display:'block'}}/>
        ))}
        {active&&state!=='idle'&&maxSize>=120&&(
          <div style={{position:'absolute',bottom:-22,left:'50%',transform:'translateX(-50%)',
            fontFamily:'var(--pixel)',fontSize:'5px',color,whiteSpace:'nowrap',letterSpacing:'0.05em'}}>
            {state==='thinking'?'● PENSANDO...':'● RESPONDIENDO...'}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── SourcesPanel ──────────────────────────────────────────────────────────
function SourcesPanel({sources}:{sources:Source[]}){
  const [open,setOpen]=useState(false);
  if(!sources.length) return null;
  return(
    <div style={{marginTop:8}}>
      <button onClick={()=>setOpen(!open)} style={{
        display:'flex',alignItems:'center',gap:6,fontSize:'11px',
        color:'#5A5A72',background:'none',border:'none',cursor:'pointer',padding:'4px 0'}}>
        <span style={{fontFamily:'var(--pixel)',fontSize:'6px'}}>
          {open?'▾':'▸'} {sources.length} FUENTE{sources.length>1?'S':''}
        </span>
      </button>
      {open&&(
        <div style={{marginTop:6,display:'flex',flexDirection:'column',gap:4}}>
          {sources.map((s,i)=>{
            const isCand=s.tipo==='candidato';
            const isFc=s.tipo==='fact-checking';
            const cInfo=s.candidato?CANDS[s.candidato as keyof typeof CANDS]:null;
            const accent=isFc?'#F59E0B':(cInfo?cInfo.color:'#5A5A72');
            const badgeLabel=isFc?'FACT-CHECK':(isCand?(cInfo?.alias||s.candidato):'REF');
            const badgeBg=isFc?'rgba(245,158,11,0.1)':(cInfo?cInfo.colorBg:'#2A2A42');
            const badgeBorder=isFc?'rgba(245,158,11,0.35)':(cInfo?cInfo.colorBorder:'#3A3A52');
            return(
              <div key={i} style={{display:'flex',alignItems:'center',gap:8,padding:'6px 10px',
                background:'#1A1A2E',border:`1px solid #2A2A42`,fontSize:'11px'}}>
                <span style={{color:accent,fontSize:'9px'}}>{isFc?'🛡':(isCand?'◈':'◉')}</span>
                <span style={{color:'#C8C8D4',flex:1,overflow:'hidden',
                  textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{s.title}</span>
                <span style={{fontFamily:'var(--pixel)',fontSize:'5px',padding:'2px 6px',
                  background:badgeBg,
                  color:accent,border:`1px solid ${badgeBorder}`,whiteSpace:'nowrap'}}>
                  {badgeLabel}
                </span>
                {s.lang==='en'&&(
                  <span style={{fontFamily:'var(--pixel)',fontSize:'5px',padding:'2px 6px',
                    background:'#1E2A3A',color:'#4A9EE0',border:'1px solid #2A4060'}}>EN</span>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ─── WelcomeScreen ─────────────────────────────────────────────────────────
function WelcomeScreen({onEnter}:{onEnter:()=>void}){
  const isMobile = useIsMobile();
  return(
    <div style={{minHeight:'100vh',background:'#0E0E1A',display:'flex',flexDirection:'column',
      overflowY:'auto',alignItems:'center',justifyContent:'center',
      padding: isMobile ? '20px 16px' : '24px 16px',
      gap: isMobile ? 20 : 28}}>

      {/* Logo */}
      <div style={{display:'flex',alignItems:'center',gap:10}}>
        <img src="/gazzzeta.png" alt="Gazzzeta" style={{width:isMobile?32:40,height:isMobile?32:40,borderRadius:'50%',imageRendering:'auto'}}/>
        <div>
          <div style={{fontFamily:'var(--pixel)',fontSize: isMobile?'7px':'8px',color:'#CC2222',letterSpacing:'0.1em'}}>GAZZZETA</div>
          <div style={{fontSize:'10px',color:'#5A5A72'}}>Difusión · Fabián López</div>
        </div>
      </div>

      {/* Título */}
      <div style={{textAlign:'center',padding:'0 8px'}}>
        <h1 style={{fontFamily:'var(--pixel)',
          fontSize: isMobile ? 'clamp(8px,3.5vw,12px)' : 'clamp(10px,2.5vw,16px)',
          color:'#F0A020',lineHeight:2.4,letterSpacing:'0.05em'}}>
          ⚡ PREGÚNTALE A LOS CANDIDATOS ⚡
        </h1>
        <p style={{fontFamily:'var(--pixel)',fontSize:'7px',color:'#5A5A72',
          marginTop:8,letterSpacing:'0.15em'}}>COLOMBIA · ELECCIONES 2026</p>
      </div>

      {/* Personajes */}
      <div style={{display:'flex',gap: isMobile?12:32,justifyContent:'center',
        alignItems:'flex-end',width:'100%',maxWidth: isMobile?360:500}}>
        {Object.entries(CANDS).map(([key,c])=>(
          <div key={key} style={{flex:1,display:'flex',flexDirection:'column',alignItems:'center',gap:isMobile?6:8}}>
            <div style={{width:'100%',maxWidth: isMobile?140:180,aspectRatio:'1',position:'relative',
              border:`2px solid ${c.colorBorder}`,boxShadow:`0 0 20px ${c.color}22`}}>
              <video autoPlay loop muted playsInline src={`/${c.char}-idle.mp4`}
                style={{width:'100%',height:'100%',imageRendering:'pixelated',display:'block'}}/>
            </div>
            <div style={{textAlign:'center'}}>
              <div style={{fontFamily:'var(--pixel)',fontSize: isMobile?'7px':'7px',color:c.color,marginBottom:3}}>
                {c.alias.toUpperCase()}
              </div>
              <div style={{fontSize: isMobile?'10px':'11px',color:'#8888A0',lineHeight:1.3}}>{c.name}</div>
              {isMobile&&<div style={{fontSize:'9px',color:'#5A5A52',marginTop:2}}>{c.party}</div>}
            </div>
          </div>
        ))}
      </div>

      {/* Descripción */}
      <div style={{maxWidth:480,textAlign:'center',padding:'0 8px'}}>
        <p style={{fontSize: isMobile?'13px':'13px',color:'#8888A0',lineHeight:1.8}}>
          Compara las propuestas electorales de los candidatos colombianos contra documentos académicos e institucionales sobre las necesidades reales del país.
        </p>
      </div>

      {/* Cómo funciona */}
      <div style={{display:'grid',
        gridTemplateColumns: isMobile?'1fr 1fr':'1fr 1fr 1fr',
        gap:10,maxWidth:560,width:'100%',padding:'0 8px'}}>
        {[
          {n:'01',t:'Elige candidato',d:'Consulta a uno o ambos'},
          {n:'02',t:'Haz tu pregunta',d:'En lenguaje natural'},
          {n:'03',t:'Recibe análisis',d:'Basado en documentos oficiales'},
        ].map((s,i)=>(
          <div key={s.n} style={{padding:'12px',
            background:'#151525',border:'1px solid #2A2A42',textAlign:'center',
            gridColumn: isMobile&&i===2?'1 / -1':undefined}}>
            <div style={{fontFamily:'var(--pixel)',fontSize:'12px',color:'#F0A020',marginBottom:8}}>{s.n}</div>
            <div style={{fontFamily:'var(--pixel)',fontSize:'6px',color:'#C8C8D4',marginBottom:6,lineHeight:1.8}}>{s.t.toUpperCase()}</div>
            <div style={{fontSize:'11px',color:'#5A5A72',lineHeight:1.6}}>{s.d}</div>
          </div>
        ))}
      </div>

      {/* Botón entrar */}
      <button onClick={onEnter} style={{
        fontFamily:'var(--pixel)',fontSize: isMobile?'9px':'10px',
        padding: isMobile?'16px 32px':'14px 40px',
        background:'#F0A020',color:'#0E0E1A',border:'none',cursor:'pointer',
        letterSpacing:'0.1em',transition:'all 0.2s',
        boxShadow:'0 0 20px rgba(240,160,32,0.3)'}}>
        ENTRAR →
      </button>

      {/* Footer */}
      <p style={{fontFamily:'var(--pixel)',fontSize:'5px',color:'#2A2A42',
        letterSpacing:'0.1em',textAlign:'center',padding:'0 8px'}}>
        CÓDIGO ABIERTO · SIN FINES ELECTORALES DIRECTOS · DATOS PÚBLICOS
      </p>
    </div>
  );
}

// ─── AnalysisContent ───────────────────────────────────────────────────────
function AnalysisContent({text}:{text:string}){
  return(
    <div style={{fontSize:'13px',lineHeight:1.8,color:'#B0B0C4'}}>
      {text.split('\n').map((line,i)=>{
        if(line.startsWith('## '))
          return<div key={i} style={{fontFamily:'var(--pixel)',fontSize:'7px',color:'#F0A020',
            marginTop:20,marginBottom:8,lineHeight:1.8}}>{line.slice(3)}</div>;
        if(line.startsWith('# '))
          return<div key={i} style={{fontFamily:'var(--pixel)',fontSize:'9px',color:'#F0A020',
            marginTop:16,marginBottom:8,lineHeight:1.8}}>{line.slice(2)}</div>;
        if(line.startsWith('- ')||line.startsWith('* '))
          return<div key={i} style={{paddingLeft:14,marginBottom:3,color:'#C8C8D4'}}>▸ {parseTooltips(line.slice(2))}</div>;
        if(line==='') return<br key={i}/>;
        return<p key={i} style={{marginBottom:3,color:'#C8C8D4'}}>{parseTooltips(line)}</p>;
      })}
    </div>
  );
}

// ─── Sidebar ───────────────────────────────────────────────────────────────
function Sidebar({
  isMobile, open, onClose, candidate, setCandidate, bubbleColor,
}:{
  isMobile:boolean; open:boolean; onClose:()=>void;
  candidate:Candidate; setCandidate:(c:Candidate)=>void; bubbleColor:string;
}){
  const sidebarStyle: React.CSSProperties = isMobile
    ? { position:'fixed', top:0, left:0, bottom:0, zIndex:50, width:280,
        transform: open ? 'translateX(0)' : 'translateX(-100%)',
        transition:'transform 0.3s ease',
        background:'#0E0E1A', overflowY:'auto', display:'flex', flexDirection:'column' }
    : { width:240, flexShrink:0, borderRight:'1px solid #2A2A42',
        background:'#0E0E1A', overflowY:'auto', display:'flex', flexDirection:'column' };

  if(!open && !isMobile) return null;

  return(
    <>
      {/* Backdrop móvil */}
      {isMobile&&open&&(
        <div onClick={onClose}
          style={{position:'fixed',inset:0,background:'rgba(0,0,0,0.7)',zIndex:40}}/>
      )}

      <aside style={sidebarStyle}>
        {/* Cerrar en móvil */}
        {isMobile&&(
          <div style={{display:'flex',justifyContent:'flex-end',padding:'12px 14px',
            borderBottom:'1px solid #2A2A42',flexShrink:0}}>
            <button onClick={onClose} style={{fontFamily:'var(--pixel)',fontSize:'8px',
              color:'#5A5A72',background:'none',border:'1px solid #2A2A42',
              padding:'6px 10px',cursor:'pointer'}}>✕</button>
          </div>
        )}

        {/* Candidate cards */}
        {Object.entries(CANDS).map(([key,c])=>{
          const isSelected=candidate===key;
          return(
            <div key={key} onClick={()=>{ setCandidate(candidate===key?'all':key as Candidate); if(isMobile) onClose(); }}
              style={{padding:'16px 14px',borderBottom:'1px solid #2A2A42',cursor:'pointer',
                background:isSelected?c.colorBg:'transparent',
                borderLeft:isSelected?`3px solid ${c.color}`:'3px solid transparent',
                transition:'all 0.2s'}}>
              <div style={{display:'flex',gap:10,alignItems:'flex-start'}}>
                <img src={c.img} alt={c.alias} style={{width:52,height:52,
                  imageRendering:'pixelated',flexShrink:0,
                  border:`2px solid ${isSelected?c.color:'#2A2A42'}`}}/>
                <div>
                  <div style={{fontFamily:'var(--pixel)',fontSize:'6px',color:c.color,marginBottom:4}}>{c.alias.toUpperCase()}</div>
                  <div style={{fontSize:'11px',color:'#C8C8D4',fontWeight:500,marginBottom:3}}>{c.name}</div>
                  <div style={{fontSize:'10px',color:'#5A5A72',marginBottom:2}}>{c.party}</div>
                  <div style={{fontSize:'10px',color:'#4A4A62'}}>{c.role}</div>
                </div>
              </div>
              <div style={{marginTop:8,padding:'6px 8px',background:'#1A1A2E',
                borderLeft:`2px solid ${c.colorBorder}`,fontSize:'10px',
                color:'#6A6A82',fontStyle:'italic'}}>
                "{c.slogan}"
              </div>
            </div>
          );
        })}

        {/* Nota de cobertura documental */}
        <div style={{padding:'12px 14px',borderTop:'1px solid #1E1E32',background:'#0A0A14',marginTop:'auto'}}>
          <div style={{fontFamily:'var(--pixel)',fontSize:'5px',color:'#3A3A52',marginBottom:6,letterSpacing:'0.1em'}}>ℹ COBERTURA DOCUMENTAL</div>
          <p style={{fontSize:'9px',color:'#3A3A52',lineHeight:1.6}}>
            La diferencia de cobertura entre candidatos refleja la disponibilidad pública de sus documentos programáticos, no un criterio editorial de esta plataforma.
          </p>
        </div>

        {/* Fuentes de referencia */}
        <div style={{padding:'14px',borderTop:'1px solid #1E1E32'}}>
          <div style={{fontFamily:'var(--pixel)',fontSize:'5px',color:'#3A3A52',marginBottom:8,letterSpacing:'0.1em'}}>FUENTES DE REFERENCIA</div>
          {['Plan Nal. de Desarrollo 2022-2026','Misión de Sabios 2019','OECD Economic Survey Colombia 2024'].map((f,i)=>(
            <div key={i} style={{fontSize:'9px',color:'#4A4A62',padding:'3px 0',
              borderBottom:'1px solid #1E1E32',lineHeight:1.5}}>◉ {f}</div>
          ))}
        </div>
      </aside>
    </>
  );
}

// ─── Main App ──────────────────────────────────────────────────────────────
function MainApp(){
  const isMobile = useIsMobile();
  const [tab,setTab]=useState<Tab>('chat');
  const [candidate,setCandidate]=useState<Candidate>('all');
  const [messages,setMessages]=useState<Message[]>([]);
  const [input,setInput]=useState('');
  const [loading,setLoading]=useState(false);
  const [jagState,setJagState]=useState<CharState>('idle');
  const [tigState,setTigState]=useState<CharState>('idle');
  const [dimension,setDimension]=useState('');
  const [analysis,setAnalysis]=useState('');
  const [analyzing,setAnalyzing]=useState(false);
  const [sidebarOpen,setSidebarOpen]=useState(true);
  const bottomRef=useRef<HTMLDivElement>(null);

  // Cerrar sidebar por defecto en móvil
  useEffect(()=>{ if(isMobile) setSidebarOpen(false); else setSidebarOpen(true); },[isMobile]);

  useEffect(()=>{bottomRef.current?.scrollIntoView({behavior:'smooth'})},[messages,analysis]);

  function activateChars(s:CharState){
    if(candidate==='all'||candidate==='ivan-cepeda') setJagState(s);
    if(candidate==='all'||candidate==='abelardo')   setTigState(s);
  }

  async function sendMessage(text:string){
    if(!text.trim()||loading) return;
    const userMsg:Message={role:'user',content:text};
    setMessages(prev=>[...prev,userMsg,{role:'assistant',content:''}]);
    setInput(''); setLoading(true); activateChars('thinking');
    try{
      const res=await fetch('/api/chat',{method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({
          messages:[...messages,userMsg].map(m=>({role:m.role,content:m.content})),
          candidato:candidate==='all'?null:candidate})});
      if(!res.body) throw new Error();
      const reader=res.body.getReader();
      const decoder=new TextDecoder();
      let full='';
      activateChars('responding');
      while(true){
        const{done,value}=await reader.read();
        if(done) break;
        full+=decoder.decode(value,{stream:true});
        setMessages(prev=>{const u=[...prev];u[u.length-1]={role:'assistant',content:full};return u;});
      }
      const{text:clean,sources}=parseSources(full);
      setMessages(prev=>{const u=[...prev];u[u.length-1]={role:'assistant',content:clean,sources};return u;});
    }catch{
      setMessages(prev=>{const u=[...prev];u[u.length-1]={role:'assistant',content:'Error al conectar con el servidor.'};return u;});
    }finally{setLoading(false);setJagState('idle');setTigState('idle');}
  }

  async function runAnalysis(dim:string){
    if(analyzing) return;
    setDimension(dim);setAnalysis('');setAnalyzing(true);
    setJagState('thinking');setTigState('thinking');
    try{
      const res=await fetch('/api/analyze',{method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({dimension:dim,candidatos:['ivan-cepeda','abelardo']})});
      if(!res.body) throw new Error();
      const reader=res.body.getReader();
      const decoder=new TextDecoder();
      setJagState('responding');setTigState('responding');
      while(true){
        const{done,value}=await reader.read();
        if(done) break;
        setAnalysis(prev=>prev+decoder.decode(value,{stream:true}));
      }
    }catch{setAnalysis('Error al generar el análisis.');}
    finally{setAnalyzing(false);setJagState('idle');setTigState('idle');}
  }

  const jagActive=candidate==='all'||candidate==='ivan-cepeda';
  const tigActive=candidate==='all'||candidate==='abelardo';
  const bubbleColor = candidate==='ivan-cepeda'?CANDS['ivan-cepeda'].color
    : candidate==='abelardo'?CANDS['abelardo'].color:'#F0A020';
  const bubbleBorder = candidate==='ivan-cepeda'?CANDS['ivan-cepeda'].colorBorder
    : candidate==='abelardo'?CANDS['abelardo'].colorBorder:'rgba(240,160,32,0.25)';

  const charSize = isMobile ? 75 : 180;

  return(
    <div style={{height:'100dvh',background:'#0E0E1A',display:'flex',flexDirection:'column',overflow:'hidden'}}>

      {/* ── Header ── */}
      <header style={{display:'flex',alignItems:'center',justifyContent:'space-between',
        padding: isMobile?'10px 12px':'10px 16px',
        borderBottom:'1px solid #2A2A42',background:'#0E0E1A',flexShrink:0}}>
        <div style={{display:'flex',alignItems:'center',gap:isMobile?8:10}}>
          <button onClick={()=>setSidebarOpen(!sidebarOpen)}
            style={{fontFamily:'var(--pixel)',fontSize:'8px',color:'#5A5A72',background:'none',
              border:'1px solid #2A2A42',padding: isMobile?'8px':'4px 8px',
              cursor:'pointer',minWidth:isMobile?36:undefined,minHeight:isMobile?36:undefined}}>
            {sidebarOpen&&!isMobile?'◀':'▶'}
          </button>
          <h1 style={{fontFamily:'var(--pixel)',
            fontSize: isMobile?'clamp(6px,2.5vw,8px)':'8px',
            color:'#F0A020',letterSpacing:'0.05em',lineHeight:1.6}}>
            {isMobile ? 'CANDIDATOS COL 2026' : 'PREGÚNTALE A LOS CANDIDATOS'}
          </h1>
          {!isMobile&&<span style={{fontFamily:'var(--pixel)',fontSize:'5px',color:'#3A3A52'}}>COL 2026</span>}
        </div>
        <div style={{display:'flex',alignItems:'center',gap:8}}>
          {!isMobile&&<span style={{fontSize:'10px',color:'#5A5A72'}}>Gazzzeta · Fabián López</span>}
          <img src="/gazzzeta.png" alt="Gazzzeta"
            style={{width:isMobile?22:26,height:isMobile?22:26,borderRadius:'50%',imageRendering:'auto'}}/>
        </div>
      </header>

      <div style={{flex:1,display:'flex',overflow:'hidden',position:'relative'}}>

        {/* ── Sidebar ── */}
        <Sidebar
          isMobile={isMobile}
          open={sidebarOpen}
          onClose={()=>setSidebarOpen(false)}
          candidate={candidate}
          setCandidate={setCandidate}
          bubbleColor={bubbleColor}
        />

        {/* ── Main content ── */}
        <main style={{flex:1,display:'flex',flexDirection:'column',overflow:'hidden',minWidth:0}}>

          {/* Characters + filtro */}
          <div style={{padding: isMobile?'8px 12px':'16px 16px 10px',
            borderBottom:'1px solid #2A2A42',background:'#0A0A14',flexShrink:0}}>

            {/* Desktop: character panels + filtro de texto */}
            {!isMobile&&(
              <>
                <div style={{display:'flex',gap:20,justifyContent:'center',maxWidth:500,margin:'0 auto'}}>
                  <CharPanel char="jaguar" state={jagState} active={jagActive}
                    color={CANDS['ivan-cepeda'].color} maxSize={charSize}/>
                  <div style={{display:'flex',alignItems:'center',padding:'0 2px'}}>
                    <span style={{fontFamily:'var(--pixel)',fontSize:'8px',color:'#2A2A42'}}>VS</span>
                  </div>
                  <CharPanel char="tigre" state={tigState} active={tigActive}
                    color={CANDS['abelardo'].color} maxSize={charSize}/>
                </div>
                <div style={{display:'flex',gap:8,justifyContent:'center',marginTop:14,flexWrap:'wrap'}}>
                  {([
                    {key:'all',label:'AMBOS',color:'#5A5A72',border:'#3A3A52'},
                    {key:'ivan-cepeda',label:'EL JAGUAR',color:CANDS['ivan-cepeda'].color,border:CANDS['ivan-cepeda'].colorBorder},
                    {key:'abelardo',label:'EL TIGRE',color:CANDS['abelardo'].color,border:CANDS['abelardo'].colorBorder},
                  ] as const).map(o=>(
                    <button key={o.key} onClick={()=>setCandidate(o.key)} style={{
                      fontFamily:'var(--pixel)',fontSize:'6px',padding:'7px 14px',
                      background:candidate===o.key?o.color:'transparent',
                      color:candidate===o.key?'#0E0E1A':o.color,
                      border:`2px solid ${o.border}`,cursor:'pointer',transition:'all 0.15s'}}>
                      {o.label}
                    </button>
                  ))}
                </div>
              </>
            )}

            {/* Móvil: tarjetas visuales con imagen PNG + texto legible */}
            {isMobile&&(
              <div style={{display:'flex',gap:8,width:'100%'}}>
                {/* Botón AMBOS */}
                <button onClick={()=>setCandidate('all')} style={{
                  flexShrink:0,display:'flex',flexDirection:'column',alignItems:'center',
                  justifyContent:'center',gap:3,padding:'8px',width:60,
                  background:candidate==='all'?'rgba(240,160,32,0.15)':'#151525',
                  border:`2px solid ${candidate==='all'?'#F0A020':'#2A2A42'}`,
                  cursor:'pointer',transition:'all 0.15s'}}>
                  <span style={{fontSize:'16px',lineHeight:1}}>⚡</span>
                  <span style={{fontFamily:'var(--pixel)',fontSize:'5px',
                    color:candidate==='all'?'#F0A020':'#5A5A72',lineHeight:1.4}}>AMBOS</span>
                </button>
                {/* Tarjetas de candidatos */}
                {(Object.entries(CANDS) as [keyof typeof CANDS, typeof CANDS[keyof typeof CANDS]][]).map(([key,c])=>{
                  const isActive=candidate===key;
                  const isResponding=key==='ivan-cepeda'?jagState!=='idle':tigState!=='idle';
                  return(
                    <button key={key} onClick={()=>setCandidate(candidate===key?'all':key)}
                      style={{flex:1,display:'flex',alignItems:'center',gap:10,padding:'8px 10px',
                        background:isActive?c.colorBg:'#151525',
                        border:`2px solid ${isActive?c.color:'#2A2A42'}`,
                        cursor:'pointer',transition:'all 0.15s',textAlign:'left',minHeight:60}}>
                      <div style={{position:'relative',flexShrink:0}}>
                        <img src={c.img} alt={c.alias}
                          style={{width:44,height:44,imageRendering:'pixelated',display:'block',
                            border:`2px solid ${isActive?c.color:'#2A2A42'}`}}/>
                        {isResponding&&(
                          <div style={{position:'absolute',bottom:-2,right:-2,width:8,height:8,
                            borderRadius:'50%',background:c.color,
                            boxShadow:`0 0 6px ${c.color}`}}/>
                        )}
                      </div>
                      <div style={{minWidth:0}}>
                        <div style={{fontFamily:'var(--pixel)',fontSize:'6px',color:c.color,
                          marginBottom:2,letterSpacing:'0.05em'}}>{c.alias.toUpperCase()}</div>
                        <div style={{fontSize:'11px',color:isActive?'#C8C8D4':'#6A6A82',
                          lineHeight:1.3,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>
                          {c.name}
                        </div>
                        <div style={{fontSize:'9px',color:isActive?c.color:'#3A3A52',marginTop:1}}>
                          {c.party}
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Tabs */}
          <div style={{display:'flex',borderBottom:'1px solid #2A2A42',flexShrink:0}}>
            {([{key:'chat',label:'💬  CHAT'},{key:'analyze',label:'📊  ANÁLISIS'}] as const).map(t=>(
              <button key={t.key} onClick={()=>setTab(t.key)} style={{
                flex:1,padding: isMobile?'14px':'12px',
                fontFamily:'var(--pixel)',fontSize:'7px',
                background:tab===t.key?'#151525':'transparent',
                color:tab===t.key?bubbleColor:'#3A3A52',border:'none',
                borderBottom:tab===t.key?`2px solid ${bubbleColor}`:'2px solid transparent',
                cursor:'pointer',transition:'all 0.15s',
                minHeight: isMobile?48:undefined}}>
                {t.label}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div style={{flex:1,overflow:'hidden',display:'flex',flexDirection:'column'}}>

            {/* CHAT */}
            {tab==='chat'&&(<>
              <div style={{flex:1,overflowY:'auto',
                padding: isMobile?'12px':'16px',
                display:'flex',flexDirection:'column',gap:12}}>
                {messages.length===0&&(
                  <div style={{display:'flex',flexDirection:'column',gap:isMobile?10:8}}>
                    <p style={{fontFamily:'var(--pixel)',fontSize:'5px',color:'#2A2A42',
                      textAlign:'center',marginBottom:8,letterSpacing:'0.1em'}}>PREGUNTAS SUGERIDAS</p>
                    {SUGGESTED.map((q,i)=>(
                      <button key={i} onClick={()=>sendMessage(q)} style={{
                        textAlign:'left',padding: isMobile?'12px 14px':'10px 14px',
                        background:'#151525',border:'1px solid #2A2A42',
                        color:'#6A6A82',fontSize: isMobile?'13px':'12px',
                        cursor:'pointer',transition:'all 0.2s',lineHeight:1.6,
                        minHeight: isMobile?48:undefined}}
                        onMouseEnter={e=>{e.currentTarget.style.borderColor=bubbleColor;e.currentTarget.style.color='#C8C8D4';}}
                        onMouseLeave={e=>{e.currentTarget.style.borderColor='#2A2A42';e.currentTarget.style.color='#6A6A82';}}>
                        {q}
                      </button>
                    ))}
                  </div>
                )}

                {messages.map((msg,i)=>(
                  <div key={i} className="fade-up" style={{display:'flex',
                    justifyContent:msg.role==='user'?'flex-end':'flex-start'}}>
                    <div style={{maxWidth:'92%',display:'flex',flexDirection:'column',gap:4}}>
                      <div style={{
                        padding: isMobile?'12px 14px':'10px 14px',
                        fontSize: isMobile?'14px':'13px',lineHeight:1.8,
                        whiteSpace:'pre-wrap',wordBreak:'break-word',
                        background:msg.role==='user'?'transparent':'#151525',
                        border:`1px solid ${msg.role==='user'?bubbleColor:'#2A2A42'}`,
                        borderLeft:msg.role==='assistant'?`3px solid ${bubbleBorder}`:`1px solid ${bubbleColor}`,
                        color:'#C8C8D4'}}>
                        {msg.content?parseTooltips(msg.content):(loading&&i===messages.length-1?(
                          <span style={{fontFamily:'var(--pixel)',fontSize:'6px',color:bubbleColor}}>
                            procesando<span className="cursor">▋</span>
                          </span>
                        ):null)}
                      </div>
                      {msg.role==='assistant'&&msg.sources&&<SourcesPanel sources={msg.sources}/>}
                    </div>
                  </div>
                ))}
                <div ref={bottomRef}/>
              </div>

              {/* Input */}
              <div style={{
                padding: isMobile?'10px 12px':'12px',
                paddingBottom: isMobile?'calc(10px + env(safe-area-inset-bottom))':'12px',
                borderTop:'1px solid #2A2A42',display:'flex',gap:8,flexShrink:0}}>
                <input value={input} onChange={e=>setInput(e.target.value)}
                  onKeyDown={e=>e.key==='Enter'&&!e.shiftKey&&sendMessage(input)}
                  placeholder="Escribe tu pregunta aquí..." disabled={loading}
                  style={{flex:1,background:'#151525',border:'1px solid #2A2A42',
                    color:'#C8C8D4',
                    padding: isMobile?'14px':'10px 14px',
                    fontSize: isMobile?'16px':'13px',
                    transition:'border-color 0.2s'}}
                  onFocus={e=>e.currentTarget.style.borderColor=bubbleColor}
                  onBlur={e=>e.currentTarget.style.borderColor='#2A2A42'}/>
                <button onClick={()=>sendMessage(input)} disabled={loading||!input.trim()}
                  style={{fontFamily:'var(--pixel)',fontSize:'6px',
                    padding: isMobile?'14px 16px':'10px 16px',
                    minWidth: isMobile?60:undefined,
                    background:!loading&&input.trim()?bubbleColor:'#1A1A2E',
                    color:!loading&&input.trim()?'#0E0E1A':'#3A3A52',
                    border:`1px solid ${bubbleColor}`,
                    cursor:!loading&&input.trim()?'pointer':'default',
                    transition:'all 0.15s'}}>
                  {isMobile?'▶':'ENVIAR>'}
                </button>
              </div>
            </>)}

            {/* ANÁLISIS */}
            {tab==='analyze'&&(
              <div style={{flex:1,overflowY:'auto',
                padding: isMobile?'12px':'16px',
                display:'flex',flexDirection:'column',gap:14}}>
                <p style={{fontFamily:'var(--pixel)',fontSize:'5px',color:'#3A3A52',
                  textAlign:'center',letterSpacing:'0.1em'}}>
                  SELECCIONA UNA DIMENSIÓN PARA ANALIZAR
                </p>
                <div style={{background:'#0E0E1A',border:'1px solid #3A2A1A',padding:'10px 14px',
                  display:'flex',gap:10,alignItems:'flex-start'}}>
                  <span style={{color:'#C07020',fontSize:'11px',flexShrink:0,lineHeight:1}}>⚠</span>
                  <p style={{fontFamily:'var(--pixel)',fontSize:'5px',color:'#7A5A3A',
                    lineHeight:1.8,letterSpacing:'0.04em',margin:0}}>
                    NOTA METODOLÓGICA: Iván Cepeda tiene un programa de 400+ páginas con visión integral —
                    sus propuestas están entretejidas en una narrativa más amplia.
                    Abelardo tiene ~15 páginas en formato de bullet points.
                    Mayor especificidad aparente no equivale a mejor propuesta.
                  </p>
                </div>
                <div style={{display:'flex',flexWrap:'wrap',gap: isMobile?6:8,justifyContent:'center'}}>
                  {DIMS.map(dim=>(
                    <button key={dim} onClick={()=>runAnalysis(dim)} disabled={analyzing} style={{
                      fontFamily:'var(--pixel)',fontSize:'5px',
                      padding: isMobile?'10px 12px':'8px 12px',
                      minHeight: isMobile?40:undefined,
                      background:dimension===dim?bubbleColor:'#151525',
                      color:dimension===dim?'#0E0E1A':'#5A5A72',
                      border:`1px solid ${dimension===dim?bubbleColor:'#2A2A42'}`,
                      cursor:analyzing?'default':'pointer',transition:'all 0.15s'}}
                      onMouseEnter={e=>{if(!analyzing){e.currentTarget.style.borderColor=bubbleColor;e.currentTarget.style.color=bubbleColor;}}}
                      onMouseLeave={e=>{if(dimension!==dim){e.currentTarget.style.borderColor='#2A2A42';e.currentTarget.style.color='#5A5A72';}}}>
                      {dim.toUpperCase()}
                    </button>
                  ))}
                </div>

                {analyzing&&!analysis&&(
                  <div style={{textAlign:'center',padding:30,fontFamily:'var(--pixel)',
                    fontSize:'7px',color:bubbleColor}}>
                    GENERANDO ANÁLISIS<span className="cursor">▋</span>
                  </div>
                )}

                {analysis&&(
                  <div style={{background:'#151525',border:'1px solid #2A2A42',padding: isMobile?14:20}}>
                    <div style={{fontFamily:'var(--pixel)',fontSize:'6px',color:bubbleColor,
                      marginBottom:16,letterSpacing:'0.05em'}}>
                      ▸ {dimension.toUpperCase()}
                    </div>
                    <AnalysisContent text={analysis}/>
                    {analyzing&&<span style={{fontFamily:'var(--pixel)',fontSize:'7px',color:bubbleColor}} className="cursor"> ▋</span>}
                  </div>
                )}
                <div ref={bottomRef}/>
              </div>
            )}
          </div>

          {/* Footer */}
          <footer style={{padding: isMobile?'6px 12px':'8px 16px',
            borderTop:'1px solid #1E1E32',
            display:'flex',alignItems:'center',justifyContent:'space-between',flexShrink:0}}>
            <p style={{fontFamily:'var(--pixel)',fontSize:'5px',color:'#2A2A42',letterSpacing:'0.08em'}}>
              CÓDIGO ABIERTO · DATOS PÚBLICOS
            </p>
            <div style={{display:'flex',alignItems:'center',gap:6}}>
              {!isMobile&&<span style={{fontSize:'9px',color:'#2A2A42'}}>Gazzzeta · Fabián López</span>}
              <img src="/gazzzeta.png" alt="Gazzzeta"
                style={{width:18,height:18,borderRadius:'50%',imageRendering:'auto',opacity:0.5}}/>
            </div>
          </footer>
        </main>
      </div>
    </div>
  );
}

// ─── Page ──────────────────────────────────────────────────────────────────
export default function Home(){
  const [screen,setScreen]=useState<Screen>('welcome');
  if(screen==='welcome') return <WelcomeScreen onEnter={()=>setScreen('app')}/>;
  return <MainApp/>;
}
