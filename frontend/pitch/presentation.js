const notes=[
'En el espacio, la distancia se mide en kilómetros. Cuando tu salud cambia, se mide en tiempo.',
'Los astronautas están entrenados y tienen monitoreo. Pero en una misión lejana, la respuesta médica desde Tierra puede demorarse. ¿Cómo mantenemos el cuidado durante esa espera?',
'Presentamos ORI, un copiloto de salud que funciona a bordo. Reúne mediciones y tendencias en un cuerpo interactivo. Puedes preguntarle por tus registros y consultar guías con fuentes. Su arquitectura local mantiene el historial y la orientación disponibles sin internet. La conversación utiliza un modelo local; si falla, quedan guías y respuestas predefinidas.',
'Nuestro prototipo usa recursos de NASA y datos de demostración. El siguiente paso es validar su orientación con profesionales y probarlo con usuarios. ORI: que la distancia no interrumpa el cuidado.'
];
const frames=[...document.querySelectorAll('.frame')];const $=s=>document.querySelector(s);
const boundaries=[0,10,23,47];let index=0,elapsed=0,running=false,startTime=0,tick=null;
function show(n){index=Math.max(0,Math.min(3,n));frames.forEach((s,i)=>{s.classList.toggle('active',i===index);s.hidden=i!==index;s.setAttribute('aria-hidden',String(i!==index))});$('#step').textContent=String(index+1).padStart(2,'0')+' / 04';$('#track i').style.width=(index+1)*25+'%';$('#previous').disabled=index===0;$('#next').disabled=index===3;$('#note-text').textContent=notes[index];$('#note-label').textContent='GUION · '+String(index+1).padStart(2,'0')+' / 04';history.replaceState(null,'','#'+(index+1))}
function paintClock(){const left=Math.max(0,60-Math.floor(elapsed));$('#clock').textContent=String(Math.floor(left/60)).padStart(2,'0')+':'+String(left%60).padStart(2,'0');document.body.classList.toggle('finished',left===0)}
function pause(){running=false;clearInterval(tick);$('#play').innerHTML='Continuar <span>60 s</span>'}
function reset(){pause();elapsed=0;show(0);paintClock();$('#play').innerHTML='Iniciar pitch <span>60 s</span>'}
function play(){if(running){pause();return}if(elapsed>=60)reset();running=true;startTime=performance.now()-elapsed*1000;$('#play').innerHTML='Pausar <span>Ⅱ</span>';tick=setInterval(()=>{elapsed=Math.min(60,(performance.now()-startTime)/1000);let target=0;for(let i=0;i<4;i++)if(elapsed>=boundaries[i])target=i;if(index!==target)show(target);paintClock();if(elapsed>=60){pause();$('#play').innerHTML='Repetir pitch <span>↺</span>'}},100)}
function manual(n){if(running)pause();show(n);elapsed=boundaries[index];paintClock()}
function toggleNotes(){const open=$('#notes').hidden;$('#notes').hidden=!open;$('#script').setAttribute('aria-pressed',String(open))}
$('#play').onclick=play;$('#restart').onclick=reset;$('#next').onclick=()=>manual(index+1);$('#previous').onclick=()=>manual(index-1);$('#script').onclick=toggleNotes;$('#close-script').onclick=toggleNotes;$('#full').onclick=()=>{if(!document.fullscreenElement)document.documentElement.requestFullscreen?.().catch(()=>{});else document.exitFullscreen?.()};
document.addEventListener('keydown',e=>{if(e.ctrlKey||e.metaKey||e.altKey)return;if(['ArrowRight','PageDown'].includes(e.key)){e.preventDefault();manual(index+1)}if(['ArrowLeft','PageUp'].includes(e.key)){e.preventDefault();manual(index-1)}if(e.key===' '){e.preventDefault();play()}if(e.key.toLowerCase()==='n')toggleNotes();if(e.key.toLowerCase()==='r')reset();if(e.key==='Home')manual(0)});
show((Number(location.hash.slice(1))||1)-1);paintClock();
