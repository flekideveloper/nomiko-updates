"""Local home dashboard widgets. All HTML is escaped, no external JS/CDNs."""
from __future__ import annotations

from datetime import datetime
from calendar import monthcalendar, month_name
from html import escape
from urllib.parse import quote_plus

WIDGETS = {
    'clock': ('Clock', 'Local time and date'),
    'timer': ('Timer', 'Countdown with an alert'),
    'stopwatch': ('Stopwatch', 'Time intervals'),
    'focus': ('Focus', '25-minute focus sessions'),
    'notes': ('Quick notes', 'A note saved on this device'),
    'tasks': ('To-do list', 'Local tasks and checklists'),
    'calendar': ('Calendar', 'This month at a glance'),
    'weather': ('Weather', 'On-demand forecast by city'),
    'audio': ('Audio studio · Beta', 'Local player, volume, microphone recording'),
    'calculator': ('Calculator', 'Quick calculations'),
    'links': ('Quick links', 'Your latest bookmarks'),
}
# Fresh NOMIKO profiles start with a clean, widget-free new tab.
# Existing user choices are preserved by Store, even when non-empty.
DEFAULT_WIDGETS = []


def normalize_widgets(order, enabled):
    order = order if isinstance(order, list) else list(WIDGETS)
    enabled = enabled if isinstance(enabled, list) else DEFAULT_WIDGETS
    order = list(dict.fromkeys(x for x in order if x in WIDGETS))
    order += [x for x in WIDGETS if x not in order]
    enabled = [x for x in enabled if x in WIDGETS]
    return order, enabled


def _e(value):
    return escape(str(value), quote=True)


def _widget(key, body):
    return f'<article class="widget" data-widget="{key}"><header><span>{_e(WIDGETS[key][0])}</span></header><div class="widget-body">{body}</div></article>'


def render_widgets(order, enabled, data=None, bookmarks=None, weather=None, density='comfortable', columns='auto'):
    order, enabled = normalize_widgets(order, enabled)
    # Common path: a clean new tab. Avoid computing widget markup entirely.
    if not enabled:
        return ''
    data = data if isinstance(data, dict) else {}
    bookmarks = bookmarks if isinstance(bookmarks, list) else []
    weather = weather if isinstance(weather, dict) else {}
    now = datetime.now().astimezone()
    blocks = {}
    blocks['clock'] = _widget('clock', '<div id="w-clock" class="bigclock">--:--:--</div><p id="w-date" class="quiet">Local time</p>')
    blocks['timer'] = _widget('timer', '''<div class="bigclock" id="w-timer">05:00</div>
      <div class="widget-line"><label>Minutes <input id="w-timermin" type="number" min="1" max="240" value="5"/></label>
      <button type="button" id="w-timerstart">Start / Pause</button><button type="button" id="w-timerreset">Reset</button></div>''')
    blocks['stopwatch'] = _widget('stopwatch', '''<div class="bigclock" id="w-stopwatch">00:00.0</div>
      <div class="widget-line"><button type="button" id="w-stopstart">Start / Pause</button><button type="button" id="w-stopreset">Reset</button></div>''')
    blocks['focus'] = _widget('focus', '''<p class="quiet">25 minutes of focus · 5 minutes of rest</p><div class="bigclock" id="w-focus">25:00</div>
      <div class="widget-line"><button type="button" id="w-focusstart">Start / Pause</button><button type="button" id="w-focusreset">Reset</button></div>''')
    note = _e(str(data.get('note', ''))[:4000])
    blocks['notes'] = _widget('notes', f'''<form method="GET" action="https://nomiko.invalid/widget">
      <input type="hidden" name="action" value="note"/><textarea name="text" maxlength="4000" placeholder="Your thoughts stay on this device…">{note}</textarea>
      <div class="widget-line"><button type="submit">Save note</button><small class="quiet">Stored locally</small></div></form>''')
    tasks = data.get('tasks', [])
    tasks = tasks if isinstance(tasks, list) else []
    task_html = ''.join(
        '<div class="task"><form method="GET" action="https://nomiko.invalid/widget"><input type="hidden" name="action" value="task-remove"/>'
        f'<input type="hidden" name="idx" value="{i}"/><button type="submit" title="Complete / remove">✓</button></form>'
        f'<span>{_e(t[:120])}</span></div>' for i, t in enumerate(tasks[:40]) if isinstance(t, str)
    )
    blocks['tasks'] = _widget('tasks', f'''<div class="tasks">{task_html or '<p class="quiet">No tasks yet.</p>'}</div>
      <form class="widget-line" action="https://nomiko.invalid/widget" method="GET"><input type="hidden" name="action" value="task-add"/>
      <input name="text" maxlength="120" placeholder="Add a task…" required/><button type="submit">Add</button></form>''')
    cal = monthcalendar(now.year, now.month)
    days = ''.join(f'<span class="weekhead">{x}</span>' for x in ('M', 'T', 'W', 'T', 'F', 'S', 'S'))
    for week in cal:
        for day in week:
            days += f'<span class="{"today" if day == now.day else ""}">{day if day else ""}</span>'
    blocks['calendar'] = _widget('calendar', f'<p class="quiet">{month_name[now.month]} {now.year}</p><div class="calendar">{days}</div>')
    city = _e(data.get('weather_city', ''))
    weather_detail = ('<p class="quiet">Enter a city, then choose Check. NOMIKO requests the forecast only when you ask.</p>'
                      if not weather else f'<div class="weather-temp">{_e(weather.get("temp", "—"))}°C</div>'
                      f'<p class="quiet">{_e(weather.get("city", city))} · {_e(weather.get("summary", "Current conditions"))}'
                      f' · Wind {_e(weather.get("wind", "—"))} km/h</p>')
    if weather.get('error'):
        weather_detail = f'<p class="quiet">{_e(weather["error"])}</p>'
    blocks['weather'] = _widget('weather', f'''<form class="widget-line" method="GET" action="https://nomiko.invalid/widget">
      <input type="hidden" name="action" value="weather"/><input name="city" maxlength="80" value="{city}" placeholder="City name" required/>
      <button type="submit">Check</button></form>{weather_detail}<small class="quiet">Source: Open-Meteo · Network request only on Check</small>''')
    blocks['audio'] = _widget('audio', '''<p class="quiet">Local audio player · file never uploads to NOMIKO</p>
      <input type="file" id="w-audiofile" accept="audio/*" aria-label="Choose audio"/>
      <audio id="w-player" controls preload="none" style="width:100%;max-width:100%;margin:9px 0"></audio>
      <div class="widget-line"><label>Volume <input id="w-volume" type="range" min="0" max="100" value="60"/></label>
      <label>Bass <input id="w-bass" type="range" min="-12" max="12" value="0"/></label>
      <label>Treble <input id="w-treble" type="range" min="-12" max="12" value="0"/></label></div>
      <div class="widget-line"><button type="button" id="w-record">Record microphone</button><a hidden id="w-recorddownload" download="nomiko-recording.webm">Save recording</a></div>
      <small class="quiet" id="w-recstatus">Recording is experimental and depends on microphone permission.</small>''')
    blocks['calculator'] = _widget('calculator', '''<div class="widget-line"><input type="text" id="w-calcinput" maxlength="100" placeholder="e.g. (15+20)/5"/>
      <button type="button" id="w-calcrun">=</button></div><div id="w-calcresult" class="bigclock">0</div>
      <p class="quiet">Numbers and + − × ÷ ( ) only</p>''')
    b_links = ''.join(f'<a class="quick-link" href="{_e(b.get("url", ""))}">{_e(str(b.get("title", b.get("url", "")))[:42])}</a>'
                      for b in bookmarks[-6:] if isinstance(b, dict) and str(b.get('url', '')).startswith(('http://', 'https://')))
    blocks['links'] = _widget('links', f'<div class="quicklinks">{b_links or "<p class=quiet>Your saved bookmarks appear here.</p>"}</div>')
    enabled_html = ''.join(blocks[key] for key in order if key in enabled)
    if not enabled_html:
        return ''  # Clean home page: no empty-state card when widgets are disabled.
    columns = columns if columns in ('auto', '2', '3') else 'auto'
    density = density if density in ('comfortable', 'compact') else 'comfortable'
    return f'<div class="widget-grid widgets-{_e(density)} columns-{_e(columns)}">{enabled_html}</div>'


WIDGET_STYLE = '''
.widget-grid{width:100%;display:grid;grid-template-columns:repeat(auto-fit,minmax(min(260px,100%),1fr));gap:13px;margin-top:28px;align-items:start;text-align:left}
.widget-grid.columns-2{grid-template-columns:repeat(2,minmax(0,1fr))}
.widget-grid.columns-3{grid-template-columns:repeat(3,minmax(0,1fr))}
.widget{min-width:0;overflow:hidden;background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px;box-shadow:0 9px 24px #00000012}
.widget header{font-size:13px;font-weight:750;letter-spacing:.2px;display:flex;justify-content:space-between;gap:8px;margin-bottom:12px;overflow-wrap:anywhere}
.widget-body{min-width:0;overflow-wrap:anywhere}
.bigclock{font-size:30px;font-variant-numeric:tabular-nums;font-weight:750;letter-spacing:-1px}
.quiet{color:var(--quiet);font-size:11px;line-height:1.5;margin:5px 0}
.widget-line{display:flex;align-items:center;gap:7px;flex-wrap:wrap;margin:9px 0}
.widget-line input:not([type=range]){flex:1;min-width:80px;width:120px;max-width:100%;border-radius:8px;border:1px solid var(--line);padding:8px;background:var(--surface);color:var(--ink)}
.widget-line label{font-size:11px;color:var(--quiet)}
.widget-line input[type=number]{width:62px;max-width:62px}
.widget button{border:1px solid var(--line);border-radius:8px;padding:7px 10px;background:var(--surface2);color:var(--ink);font-size:12px;cursor:pointer}
.widget button:hover{border-color:var(--accent)}
.widget textarea{display:block;width:100%;height:86px;resize:vertical;max-width:100%;border-radius:9px;border:1px solid var(--line);padding:9px;background:var(--surface);color:var(--ink);font:13px Segoe UI,Arial,sans-serif;user-select:text;-webkit-user-select:text}
.widget input[type=file]{max-width:100%;font-size:11px;color:var(--quiet)}
.widget input[type=range]{width:100px;max-width:100%;vertical-align:middle}
.widget a{color:var(--ink);text-decoration:none}
.widget a:hover{color:var(--accent)}
.tasks{max-height:152px;overflow:auto}.task{display:flex;align-items:center;gap:7px;font-size:12px;padding:3px 0;overflow-wrap:anywhere}
.task form{flex:none}.task span{min-width:0;overflow-wrap:anywhere}
.calendar{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:3px;text-align:center;font-size:12px}
.calendar span{padding:6px 0;min-width:0}.calendar .weekhead{color:var(--quiet)}.calendar .today{color:var(--bg);background:var(--accent);border-radius:8px}
.weather-temp{font-size:34px;font-weight:800}.quicklinks{display:flex;flex-direction:column;gap:7px}.quick-link{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px}
.widgets-empty{color:var(--quiet);font-size:12px;text-align:center;margin:22px auto}
.widgets-compact{gap:8px;margin-top:14px}.widgets-compact .widget{padding:10px;border-radius:11px}
@media(max-width:650px){.widget-grid.columns-2,.widget-grid.columns-3{grid-template-columns:1fr}}
'''

WIDGET_SCRIPT = r'''
(function(){
  const byId=(id)=>document.getElementById(id);
  const fmt=(s)=>String(Math.floor(s/60)).padStart(2,'0')+':'+String(Math.floor(s%60)).padStart(2,'0');
  function timer(display,start,reset,minutes){
    let seconds=minutes(),running=false,last=0,tickTimer=null;
    function draw(){if(display()) display().textContent=fmt(Math.max(0,seconds));}
    function tick(){if(!running)return;const now=performance.now();seconds=Math.max(0,seconds-(now-last)/1000);last=now;draw();if(seconds<=0){running=false;clearInterval(tickTimer);tickTimer=null;alert('NOMIKO timer finished');}}
    if(start())start().addEventListener('click',()=>{if(seconds<=0)seconds=minutes();running=!running;last=performance.now();if(running)tickTimer=setInterval(tick,250);else{clearInterval(tickTimer);tickTimer=null;}draw();});
    if(reset())reset().addEventListener('click',()=>{running=false;clearInterval(tickTimer);tickTimer=null;seconds=minutes();draw();});
    draw();
  }
  if(byId('w-clock')){function clock(){if(document.hidden)return;const d=new Date();byId('w-clock').textContent=d.toLocaleTimeString();byId('w-date').textContent=d.toLocaleDateString(undefined,{weekday:'long',year:'numeric',month:'long',day:'numeric'});}clock();setInterval(clock,1000);document.addEventListener('visibilitychange',clock);}
  if(byId('w-timer'))timer(()=>byId('w-timer'),()=>byId('w-timerstart'),()=>byId('w-timerreset'),()=>Math.max(1,Math.min(240,Number(byId('w-timermin').value)||5))*60);
  if(byId('w-focus'))timer(()=>byId('w-focus'),()=>byId('w-focusstart'),()=>byId('w-focusreset'),()=>25*60);
  if(byId('w-stopwatch')){let elapsed=0,running=false,last=0,interval=null;const draw=()=>{const sec=Math.floor(elapsed/1000),d=Math.floor((elapsed%1000)/100);byId('w-stopwatch').textContent=fmt(sec)+'.'+d;};byId('w-stopstart').addEventListener('click',()=>{running=!running;last=performance.now();if(running){interval=setInterval(()=>{let now=performance.now();elapsed+=now-last;last=now;draw();},100);}else{clearInterval(interval);interval=null;draw();}});byId('w-stopreset').addEventListener('click',()=>{elapsed=0;running=false;clearInterval(interval);interval=null;draw();});}
  if(byId('w-calcrun')){byId('w-calcrun').addEventListener('click',()=>{
    const expression=byId('w-calcinput').value.replace(/\s/g,'');
    const resultNode=byId('w-calcresult');
    try{
      if(!expression||!/^[0-9.+\-*/()%]+$/.test(expression))throw Error('Bad characters');
      const tokens=expression.match(/(?:\d*\.\d+|\d+\.?\d*)|[()+*/%-]/g)||[];
      if(tokens.join('')!==expression)throw Error('Invalid expression');
      let i=0;
      function atom(){
        if(tokens[i]==='+'||tokens[i]==='-'){const sign=tokens[i++]==='-'?-1:1;return sign*atom();}
        if(tokens[i]==='('){i++;const x=add();if(tokens[i++]!==')')throw Error('Missing )');return x;}
        const x=Number(tokens[i++]);if(!Number.isFinite(x))throw Error('Invalid number');return x;
      }
      function multiply(){let x=atom();while(['*','/','%'].includes(tokens[i])){const op=tokens[i++],y=atom();x=op==='*'?x*y:op==='/'?x/y:x%y;}return x;}
      function add(){let x=multiply();while(['+','-'].includes(tokens[i])){const op=tokens[i++],y=multiply();x=op==='+'?x+y:x-y;}return x;}
      const result=add();if(i!==tokens.length||!Number.isFinite(result))throw Error('Invalid');
      resultNode.textContent=String(Number(result.toFixed(8)));
    }catch(e){resultNode.textContent='Invalid';}
  });}
  if(byId('w-player')){let current=null,player=byId('w-player');byId('w-audiofile').addEventListener('change',(e)=>{if(current)URL.revokeObjectURL(current);let file=e.target.files[0];if(file){current=URL.createObjectURL(file);player.src=current;}});player.volume=.6;byId('w-volume').addEventListener('input',e=>player.volume=Number(e.target.value)/100);
    let audioContext=null,bassFilter=null,trebleFilter=null;
    player.addEventListener('play',()=>{
      if(!audioContext){
        try{audioContext=new (window.AudioContext||window.webkitAudioContext)();
          const source=audioContext.createMediaElementSource(player);
          bassFilter=audioContext.createBiquadFilter();bassFilter.type='lowshelf';bassFilter.frequency.value=180;
          trebleFilter=audioContext.createBiquadFilter();trebleFilter.type='highshelf';trebleFilter.frequency.value=3800;
          source.connect(bassFilter).connect(trebleFilter).connect(audioContext.destination);
        }catch(err){byId('w-recstatus').textContent='Audio equalizer unavailable.';}
      }
      if(audioContext&&audioContext.state==='suspended')audioContext.resume();
    });
    byId('w-bass').addEventListener('input',(e)=>{if(bassFilter)bassFilter.gain.value=Number(e.target.value);});
    byId('w-treble').addEventListener('input',(e)=>{if(trebleFilter)trebleFilter.gain.value=Number(e.target.value);});
    let recorder=null,parts=[],stream=null;
    byId('w-record').addEventListener('click',async()=>{
      if(recorder && recorder.state==='recording'){recorder.stop();return;}
      if(!navigator.mediaDevices||!window.MediaRecorder){byId('w-recstatus').textContent='Microphone recording unavailable in this browser context.';return;}
      try{stream=await navigator.mediaDevices.getUserMedia({audio:true});parts=[];recorder=new MediaRecorder(stream);recorder.ondataavailable=e=>{if(e.data&&e.data.size)parts.push(e.data);};
      recorder.onstop=()=>{const blob=new Blob(parts,{type:recorder.mimeType||'audio/webm'});let link=byId('w-recorddownload');link.href=URL.createObjectURL(blob);link.hidden=false;link.textContent='Save recording';byId('w-record').textContent='Record microphone';stream.getTracks().forEach(t=>t.stop());byId('w-recstatus').textContent='Recording stored in memory until you save it.';};
      recorder.start();byId('w-record').textContent='Stop recording';byId('w-recstatus').textContent='Recording…';
      }catch(e){byId('w-recstatus').textContent='Could not access microphone: '+e.name;}
    });
  }
})();
'''
