import * as THREE from 'three';
import { PointerLockControls } from 'three/addons/controls/PointerLockControls.js';

const el = (id) => document.getElementById(id);
const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clamp = (v,a,b) => Math.max(a,Math.min(b,v));

const ui = {
  state:null, selectedId:null, detail:null, following:false, entered:false,
  keys:new Set(), lastFrame:performance.now(), lastEventHead:null,
};

const worldNode = el('world');
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x10221b);
scene.fog = new THREE.FogExp2(0x10221b, 0.012);
const camera = new THREE.PerspectiveCamera(65, innerWidth/innerHeight, .05, 500);
camera.position.set(0, 10, 26);
camera.lookAt(0, 4, 0);
const renderer = new THREE.WebGLRenderer({antialias:true, powerPreference:'high-performance'});
renderer.setPixelRatio(Math.min(devicePixelRatio, 1.75));
renderer.setSize(innerWidth, innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;
worldNode.appendChild(renderer.domElement);

const controls = new PointerLockControls(camera, renderer.domElement);
const hemi = new THREE.HemisphereLight(0xbfe8ff, 0x29402d, 1.45); scene.add(hemi);
const sun = new THREE.DirectionalLight(0xfff1c8, 2.2); sun.position.set(-35,55,-25); sun.castShadow=true; sun.shadow.mapSize.set(2048,2048); scene.add(sun);
const lampLight = new THREE.PointLight(0xffd678, 0, 34, 1.5); lampLight.position.set(0,11,-39); scene.add(lampLight);

const ground = new THREE.Mesh(new THREE.PlaneGeometry(130,130), new THREE.MeshStandardMaterial({color:0x23402e, roughness:.95}));
ground.rotation.x = -Math.PI/2; ground.receiveShadow=true; scene.add(ground);
const grid = new THREE.GridHelper(120,60,0x4c6958,0x30493a); grid.position.y=.012; grid.material.opacity=.22; grid.material.transparent=true; scene.add(grid);

function seeded(n){ const x=Math.sin(n*127.1+311.7)*43758.5453; return x-Math.floor(x); }
function box(x,y,z,w,h,d,color,rough=.85){
  const m=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),new THREE.MeshStandardMaterial({color,roughness:rough,metalness:.04}));
  m.position.set(x,y+h/2,z); m.castShadow=true; m.receiveShadow=true; scene.add(m); return m;
}
function road(x,z,w,d){ const r=box(x,.018,z,w,.035,d,0x141c1a,1); r.receiveShadow=true; return r; }
for(const v of [-24,0,24]){ road(v,0,7,120); road(0,v,120,7); }

const buildingColors=[0x263a32,0x2e4439,0x334c3f,0x3b4c43,0x27362f];
let bi=0;
for(let gx=-48;gx<=48;gx+=16){
  for(let gz=-48;gz<=48;gz+=16){
    if(Math.abs(gx)<7 || Math.abs(gz)<7 || Math.abs(gx-32)<10 && Math.abs(gz+24)<12 || Math.abs(gx+40)<12 && Math.abs(gz+32)<12) continue;
    if(Math.abs(gx+32)<10 && Math.abs(gz-32)<10 || Math.abs(gx-32)<10 && Math.abs(gz-32)<10) continue;
    const r1=seeded(++bi), r2=seeded(++bi), r3=seeded(++bi);
    const w=7+r1*5,d=7+r2*5,h=5+r3*14;
    box(gx+(r1-.5)*2,0,gz+(r2-.5)*2,w,h,d,buildingColors[bi%buildingColors.length]);
  }
}

function cylinder(x,y,z,r,h,color){ const m=new THREE.Mesh(new THREE.CylinderGeometry(r,r,h,14),new THREE.MeshStandardMaterial({color,roughness:.8}));m.position.set(x,y+h/2,z);m.castShadow=true;m.receiveShadow=true;scene.add(m);return m; }
function sphere(x,y,z,r,color,emissive=0x000000){ const m=new THREE.Mesh(new THREE.SphereGeometry(r,16,12),new THREE.MeshStandardMaterial({color,emissive,emissiveIntensity:.7,roughness:.75}));m.position.set(x,y,z);m.castShadow=true;scene.add(m);return m; }
function textSprite(text,color='#d9ffe5'){
  const canvas=document.createElement('canvas'); canvas.width=512;canvas.height=96;const c=canvas.getContext('2d');
  c.fillStyle='rgba(5,14,10,.78)';c.fillRect(0,0,512,96);c.strokeStyle='rgba(105,244,220,.45)';c.strokeRect(1,1,510,94);
  c.font='600 32px ui-monospace, monospace';c.fillStyle=color;c.textAlign='center';c.textBaseline='middle';c.fillText(text,256,48);
  const tex=new THREE.CanvasTexture(canvas);tex.colorSpace=THREE.SRGBColorSpace;const s=new THREE.Sprite(new THREE.SpriteMaterial({map:tex,transparent:true,depthTest:false}));s.scale.set(10,1.9,1);return s;
}
function landmarkLabel(name,x,y,z){ const s=textSprite(name.toUpperCase());s.position.set(x,y,z);scene.add(s); }
for(let i=0;i<10;i++){ const a=i/10*Math.PI*2; const x=-38+Math.cos(a)*(4+seeded(i)*3),z=-28+Math.sin(a)*(4+seeded(i+12)*3);cylinder(x,0,z,.28,2.2,0x5d3c28);sphere(x,2.8,z,1.45,0x355f36);sphere(x+.6,2.9,z,.18,0xd7b84d); }
landmarkLabel('ORCHARD / FOOD',-38,6,-28);
for(let i=0;i<3;i++){box(31+i*4,0,-22,3.2,2.2,3.2,0x5b3f30);box(31+i*4,2.2,-22,3.8,.18,3.8,i%2?0xb75d50:0xcfa64d);sphere(31+i*4,2.5,-22,.35,0xd6b34e);}
landmarkLabel('MARKET / FOOD',35,6,-22);
cylinder(0,0,5,3,.35,0x637a75);cylinder(0,.35,5,1.7,.7,0x7d918c);sphere(0,1.25,5,.28,0x91d9e5,0x215e6a); landmarkLabel('FOUNTAIN / WATER',0,4.2,5);
sphere(-30,2.2,34,3.5,0x8a743a);box(-30,0,34,7,.2,7,0x594d2e);landmarkLabel('HIVE / REST',-30,6.4,34);
box(29,0,31,11,8,11,0x30443d);box(29,8,31,8,.7,8,0x56685f);landmarkLabel('ROOFTOP / REST',29,12,31);
cylinder(0,0,-39,.22,10,0x424c48);sphere(0,10.2,-39,.7,0xffd66e,0xffb72e);landmarkLabel('LAMP',0,13,-39);
for(let i=0;i<7;i++)box(1+(i%3)*2,0,39+Math.floor(i/3)*2,1.7,1+seeded(90+i),1.7,0x654a31);landmarkLabel('ALLEY',4,5,42);

const flyGeo={
  thorax:new THREE.SphereGeometry(.34,10,8), abdomen:new THREE.SphereGeometry(.32,10,8), head:new THREE.SphereGeometry(.27,10,8),
  eye:new THREE.SphereGeometry(.115,8,6), wing:new THREE.PlaneGeometry(.62,.26),
};
const eyeMat=new THREE.MeshStandardMaterial({color:0x351414,roughness:.45,metalness:.1});
const wingMat=new THREE.MeshStandardMaterial({color:0xd9f7ef,transparent:true,opacity:.34,side:THREE.DoubleSide,depthWrite:false});
const legMat=new THREE.LineBasicMaterial({color:0x1a1410});
const flies=new Map();
const selectable=[];
const raycaster=new THREE.Raycaster(); raycaster.far=28;
const center=new THREE.Vector2(0,0);
let selectionRing=null;

function makeFlyModel(fly){
  const g=new THREE.Group();g.userData.flyId=fly.id;
  const bodyColor=new THREE.Color().setHSL((fly.hue%360)/360,.44,.28);
  const abdomenColor=new THREE.Color().setHSL((fly.hue%360)/360,.52,.22);
  const bodyMat=new THREE.MeshStandardMaterial({color:bodyColor,roughness:.55,metalness:.06});
  const abdomenMat=new THREE.MeshStandardMaterial({color:abdomenColor,roughness:.58});
  const abdomen=new THREE.Mesh(flyGeo.abdomen,abdomenMat);abdomen.scale.set(1,0.92,1.55);abdomen.position.z=.34;
  const thorax=new THREE.Mesh(flyGeo.thorax,bodyMat);thorax.scale.set(1.05,.95,1.08);
  const head=new THREE.Mesh(flyGeo.head,bodyMat);head.position.z=-.43;
  const eyeL=new THREE.Mesh(flyGeo.eye,eyeMat),eyeR=new THREE.Mesh(flyGeo.eye,eyeMat);eyeL.position.set(-.19,.04,-.59);eyeR.position.set(.19,.04,-.59);
  const wL=new THREE.Mesh(flyGeo.wing,wingMat),wR=new THREE.Mesh(flyGeo.wing,wingMat);wL.position.set(-.38,.16,.08);wR.position.set(.38,.16,.08);wL.rotation.set(-.25,.12,.28);wR.rotation.set(-.25,-.12,-.28);
  const pts=[];for(const side of [-1,1])for(const z of [-.24,.02,.28]){pts.push(side*.22,-.12,z,side*.55,-.42,z+(z<0?-.18:.18));}
  pts.push(-.1,.1,-.52,-.22,.25,-.78,.1,.1,-.52,.22,.25,-.78);
  const lg=new THREE.BufferGeometry();lg.setAttribute('position',new THREE.Float32BufferAttribute(pts,3));const legs=new THREE.LineSegments(lg,legMat);
  for(const m of [abdomen,thorax,head,eyeL,eyeR,wL,wR,legs]){m.userData.flyId=fly.id;g.add(m);selectable.push(m);if(m.isMesh)m.castShadow=true;}
  g.userData.wings=[wL,wR];g.userData.target=new THREE.Vector3(fly.x,fly.y,fly.z);g.userData.last=new THREE.Vector3(fly.x,fly.y,fly.z);
  g.position.copy(g.userData.target);g.scale.setScalar(.72*fly.size);scene.add(g);flies.set(fly.id,g);return g;
}

function updateFlyMeshes(snapshot){
  const living=new Set();
  for(const fly of snapshot.flies){
    living.add(fly.id);let mesh=flies.get(fly.id);if(!mesh)mesh=makeFlyModel(fly);
    mesh.userData.target.set(fly.x,fly.y,fly.z);mesh.userData.data=fly;
  }
  for(const [id,mesh] of flies){
    if(!living.has(id)){
      mesh.traverse(obj=>{const i=selectable.indexOf(obj);if(i>=0)selectable.splice(i,1)});
      scene.remove(mesh);flies.delete(id);
    }
  }
}

function updateLighting(snapshot){
  const t=(snapshot.minute_of_day||0)/1440;const daylight=clamp(Math.sin((t-.23)*Math.PI*2)*.8+.35,.08,1);
  hemi.intensity=.45+daylight*1.35;sun.intensity=.15+daylight*2.2;lampLight.intensity=(1-daylight)*18;
  const night=new THREE.Color(0x07100d),day=new THREE.Color(0x7aa58f);scene.background=night.clone().lerp(day,daylight*.45);scene.fog.color.copy(scene.background);
}

let ws=null,pollTimer=null;
function connect(){
  const proto=location.protocol==='https:'?'wss:':'ws:';ws=new WebSocket(`${proto}//${location.host}/ws`);
  ws.addEventListener('open',()=>setConnected(true));
  ws.addEventListener('message',(event)=>{try{consume(JSON.parse(event.data));}catch(e){console.warn(e)}});
  ws.addEventListener('close',()=>{setConnected(false);setTimeout(connect,1800);startPolling();});
  ws.addEventListener('error',()=>ws.close());
}
function startPolling(){if(pollTimer)return;pollTimer=setInterval(async()=>{try{const r=await fetch('/api/state',{cache:'no-store'});if(r.ok)consume(await r.json());}catch{}},2500)}
function setConnected(ok){el('socket-dot').classList.toggle('live',ok);el('connection-label').textContent=ok?'CITY LIVE':'RECONNECTING';if(ok&&pollTimer){clearInterval(pollTimer);pollTimer=null}}
function consume(snapshot){
  ui.state=snapshot;updateFlyMeshes(snapshot);updateLighting(snapshot);renderHUD(snapshot);renderEvents(snapshot.events||[]);renderResidents();
  if(ui.selectedId)refreshDetail();
}

function renderHUD(s){
  el('population').textContent=s.population;el('day').textContent=String(s.day).padStart(3,'0');el('world-time').textContent=s.time_label;
  const pill=el('model-pill');pill.textContent=s.model_live?`MIND / ${String(s.decision_model).toUpperCase()}`:'MIND / LOCAL FALLBACK';pill.title=s.decision_model;
}
function eventTime(ev){const m=Math.floor(ev.world_minute%1440);return `D${String(ev.day).padStart(3,'0')} ${String(Math.floor(m/60)).padStart(2,'0')}:${String(m%60).padStart(2,'0')}`}
function renderEvents(events){
  el('event-count').textContent=`${events.length} RECENT`;
  const head=events[0]?.id;if(head===ui.lastEventHead)return;ui.lastEventHead=head;
  el('events').innerHTML=events.length?events.map(ev=>`<article class="event ${escapeHtml(ev.kind)}"><small><span>${escapeHtml(eventTime(ev))}</span><span>${escapeHtml(ev.kind.toUpperCase())}</span></small><p>${escapeHtml(ev.text)}</p></article>`).join(''):'<p class="muted">The city is quiet.</p>';
}
function renderResidents(){
  if(!ui.state)return;const q=el('fly-search').value.trim().toLowerCase();
  const rows=ui.state.flies.filter(f=>!q||`${f.handle} ${f.name} ${f.action}`.toLowerCase().includes(q)).sort((a,b)=>a.id-b.id);
  el('resident-count').textContent=rows.length;
  el('residents').innerHTML=rows.map(f=>`<button class="resident ${ui.selectedId===f.id?'selected':''}" type="button" data-fly="${f.id}"><span class="swatch" style="background:hsl(${f.hue} 65% 55%);color:hsl(${f.hue} 65% 55%)"></span><span><b>${escapeHtml(f.name)}</b><small>@${escapeHtml(f.handle)} · ${escapeHtml(f.action)}</small></span><em>${Math.round(f.health)}%</em></button>`).join('');
}
async function selectFly(id){
  ui.selectedId=Number(id);ui.detail=null;el('empty-inspector').classList.add('hidden');el('fly-detail').classList.remove('hidden');renderResidents();
  await refreshDetail(true);markSelection();toast(`TAGGED FLY ${String(id).padStart(3,'0')}`);
}
async function refreshDetail(force=false){
  if(!ui.selectedId)return;const summary=ui.state?.flies.find(f=>f.id===ui.selectedId);if(!summary&&!force){clearSelection();return}
  try{const r=await fetch(`/api/flies/${ui.selectedId}`,{cache:'no-store'});if(!r.ok)return;ui.detail=await r.json();renderDetail(ui.detail);}catch{}
}
function needRow(label,value,badHigh=false,badLow=false){const danger=(badHigh&&value>70)||(badLow&&value<30);return `<div class="need-row"><span>${label}</span><div class="bar ${danger?'danger':''}"><i style="width:${clamp(value,0,100)}%"></i></div><b>${Math.round(value)}</b></div>`}
function renderDetail(f){
  el('fly-id').textContent=`FLY / ${String(f.id).padStart(3,'0')}`;el('fly-name').textContent=f.name;el('fly-handle').textContent=`@${f.handle}`;el('fly-swatch').style.background=`hsl(${f.hue} 65% 55%)`;el('fly-swatch').style.color=`hsl(${f.hue} 65% 55%)`;
  el('fly-action').textContent=String(f.action).toUpperCase();el('fly-goal').textContent=f.goal||'—';el('fly-thought').textContent=f.thought||'—';el('fly-speech').textContent=f.speech||'—';el('decision-source').textContent=`decision / ${f.decision_by}`;
  el('needs').innerHTML=needRow('HUNGER',f.hunger,true)+needRow('THIRST',f.thirst,true)+needRow('ENERGY',f.energy,false,true)+needRow('SOCIAL',f.loneliness,true)+needRow('HEALTH',f.health,false,true);
  el('fly-age').textContent=`${f.age_days.toFixed(1)}d`;el('fly-gen').textContent=f.generation;el('fly-sex').textContent=f.sex;el('fly-children').textContent=f.children?.length||0;
  el('memories').innerHTML=(f.memories?.length?f.memories.map(m=>`<div class="mini-item">${escapeHtml(m.text)}<small>DAY ${escapeHtml(m.day)} · importance ${escapeHtml(m.importance)}</small></div>`).join(''):'<div class="mini-item">No durable memories yet.</div>');
  const rels=(f.relationships||[]).map(r=>{const other=ui.state?.flies.find(x=>x.id===r.fly_id);return `<div class="mini-item">${escapeHtml(other?`@${other.handle}`:`fly #${r.fly_id}`)}<small>relationship ${r.score>0?'+':''}${r.score}</small></div>`});el('relationships').innerHTML=rels.length?rels.join(''):'<div class="mini-item">No strong relationships yet.</div>';
  el('follow-button').textContent=ui.following?'RELEASE FOLLOW  F':'FOLLOW FLY  F';el('follow-name').textContent=`@${f.handle}`;
}
function clearSelection(){ui.selectedId=null;ui.detail=null;ui.following=false;el('empty-inspector').classList.remove('hidden');el('fly-detail').classList.add('hidden');el('follow-badge').classList.add('hidden');if(selectionRing){scene.remove(selectionRing);selectionRing=null}renderResidents()}
function markSelection(){if(selectionRing){scene.remove(selectionRing);selectionRing=null}const mesh=flies.get(ui.selectedId);if(!mesh)return;selectionRing=new THREE.Mesh(new THREE.TorusGeometry(.8,.035,8,32),new THREE.MeshBasicMaterial({color:0xc9ff67,transparent:true,opacity:.9}));selectionRing.rotation.x=Math.PI/2;selectionRing.userData.followTarget=mesh;scene.add(selectionRing)}
function toggleFollow(){if(!ui.selectedId){tagCrosshair();return}ui.following=!ui.following;if(ui.following){controls.unlock();el('follow-badge').classList.remove('hidden')}else el('follow-badge').classList.add('hidden');if(ui.detail)renderDetail(ui.detail)}
function tagCrosshair(){raycaster.setFromCamera(center,camera);const hits=raycaster.intersectObjects(selectable,false);if(hits.length){selectFly(hits[0].object.userData.flyId)}else toast('NO FLY IN CROSSHAIR')}
let toastTimer;function toast(text){const t=el('toast');t.textContent=text;t.classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>t.classList.remove('show'),1300)}

document.querySelectorAll('.tab').forEach(btn=>btn.addEventListener('click',()=>{document.querySelectorAll('.tab').forEach(b=>b.classList.toggle('active',b===btn));document.querySelectorAll('.tab-panel').forEach(p=>p.classList.remove('active'));el(`${btn.dataset.tab}-tab`).classList.add('active')}));
el('fly-search').addEventListener('input',renderResidents);
el('residents').addEventListener('click',e=>{const b=e.target.closest('[data-fly]');if(b)selectFly(b.dataset.fly)});
el('follow-button').addEventListener('click',toggleFollow);el('clear-button').addEventListener('click',clearSelection);
el('enter-button').addEventListener('click',()=>{ui.entered=true;el('enter-card').classList.add('hidden');controls.lock()});
renderer.domElement.addEventListener('click',()=>{if(ui.entered&&!ui.following&&!controls.isLocked)controls.lock()});
window.addEventListener('keydown',e=>{if(e.target.matches('input,textarea'))return;ui.keys.add(e.code);if(e.code==='KeyE')tagCrosshair();if(e.code==='KeyF')toggleFollow()});
window.addEventListener('keyup',e=>ui.keys.delete(e.code));
window.addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight)});

function animate(now){
  requestAnimationFrame(animate);const dt=Math.min(.05,(now-ui.lastFrame)/1000);ui.lastFrame=now;
  for(const mesh of flies.values()){
    mesh.position.lerp(mesh.userData.target,Math.min(1,dt*3.2));const delta=mesh.userData.target.clone().sub(mesh.position);if(delta.lengthSq()>.001){const yaw=Math.atan2(delta.x,delta.z)+Math.PI;mesh.rotation.y=THREE.MathUtils.lerp(mesh.rotation.y,yaw,.08)}
    const [wl,wr]=mesh.userData.wings||[];if(wl&&wr){const flap=Math.sin(now*.055)*.58;wl.rotation.z=.30+flap;wr.rotation.z=-.30-flap}
  }
  if(selectionRing?.userData.followTarget){const p=selectionRing.userData.followTarget.position;selectionRing.position.set(p.x,p.y-.55,p.z);selectionRing.rotation.z+=dt*.7}
  if(ui.following&&ui.selectedId&&flies.has(ui.selectedId)){
    const target=flies.get(ui.selectedId).position;const desired=target.clone().add(new THREE.Vector3(5.2,3.2,6.2));camera.position.lerp(desired,Math.min(1,dt*3));camera.lookAt(target);
  }else if(controls.isLocked){
    const speed=14*dt;if(ui.keys.has('KeyW'))controls.moveForward(speed);if(ui.keys.has('KeyS'))controls.moveForward(-speed);if(ui.keys.has('KeyA'))controls.moveRight(-speed);if(ui.keys.has('KeyD'))controls.moveRight(speed);if(ui.keys.has('Space'))camera.position.y+=speed;if(ui.keys.has('ShiftLeft')||ui.keys.has('ShiftRight'))camera.position.y-=speed;camera.position.x=clamp(camera.position.x,-62,62);camera.position.z=clamp(camera.position.z,-62,62);camera.position.y=clamp(camera.position.y,.7,35);
  }
  renderer.render(scene,camera);
}

connect();fetch('/api/state',{cache:'no-store'}).then(r=>r.json()).then(consume).catch(()=>{});requestAnimationFrame(animate);
