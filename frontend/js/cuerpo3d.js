import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {organos} from './config.js';
import {colores} from './estado.js';
import {comprobarOrganos} from './modelos.js';

// El visor solo conoce nombres de órganos y estados, nunca endpoints.
export function crearVisor(container,onSelect,onFailure){
 const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(38,1,0.1,100);
 const renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});
 renderer.setPixelRatio(Math.min(devicePixelRatio,2));container.append(renderer.domElement);
 const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.minDistance=3;controls.maxDistance=10;controls.enablePan=false;
 function reset(){camera.position.set(0,1.4,6.4);controls.target.set(0,0.35,0);controls.update();}reset();
 scene.add(new THREE.HemisphereLight(0xd8f4ff,0x243046,2.5));
 const light=new THREE.DirectionalLight(0xffffff,3);light.position.set(3,4,5);scene.add(light);
 let root=new THREE.Group(),selected=null,estado={},visible=true;
 scene.add(root);
 const mapped=new Map(),hearts=[];
 function index(){
  mapped.clear();hearts.length=0;
  root.traverse(object=>{
   if(!object.isMesh)return;
   let parent=object,id=null;
   while(parent&&parent!==root.parent){if(Object.hasOwn(organos,parent.name)){id=parent.name;break;}parent=parent.parent;}
   if(!id)return;
   object.userData.organo=id;
   object.material=Array.isArray(object.material)?object.material.map(m=>m.clone()):object.material.clone();
   if(!mapped.has(id))mapped.set(id,[]);mapped.get(id).push(object);
  });
  // Animate the named heart node once, avoiding compounded scales in child meshes.
  root.traverse(object=>{if(object.name==='corazon'&&!hasHeartAncestor(object)){hearts.push({object,scale:object.scale.clone()});}});
 }
 function hasHeartAncestor(object){let p=object.parent;while(p&&p!==root){if(p.name==='corazon')return true;p=p.parent;}return false;}
 function sphere(name,position,scale,color){
  const mesh=new THREE.Mesh(new THREE.SphereGeometry(1,32,24),new THREE.MeshStandardMaterial({color,roughness:.48,metalness:.12}));
  mesh.name=name;mesh.position.set(...position);mesh.scale.set(...scale);root.add(mesh);return mesh;
 }
 sphere('cuerpo',[0,.3,0],[.56,.87,.25],0x426079);
 sphere('cuerpo',[0,1.48,0],[.29,.35,.26],0x426079);
 for(const side of [-1,1]){
  sphere('cuerpo',[side*.75,.25,0],[.16,.83,.16],0x426079).rotation.z=side*.15;
  sphere('cuerpo',[side*.26,-1.02,0],[.21,.78,.2],0x426079);
 }
 sphere('cerebro',[0,1.57,.2],[.23,.19,.13],0x55d8af);
 sphere('ojos',[-.11,1.43,.255],[.06,.055,.04],0x8d9caf);
 sphere('ojos',[.11,1.43,.255],[.06,.055,.04],0x8d9caf);
 sphere('pulmones',[-.24,.66,.24],[.19,.3,.1],0x55d8af);
 sphere('pulmones',[.24,.66,.24],[.19,.3,.1],0x55d8af);
 sphere('corazon',[.10,.55,.37],[.13,.17,.10],0xf2c76b).rotation.z=-.2;
 sphere('sangre',[0,.05,.28],[.10,.17,.06],0x55d8af);
 sphere('piel',[-.77,.3,.17],[.1,.17,.06],0x55d8af);
 sphere('huesos',[.26,-1,.21],[.075,.48,.06],0x8d9caf);
 index();
 const floor=new THREE.Mesh(new THREE.RingGeometry(.7,1.1,64),new THREE.MeshBasicMaterial({color:0x31546b,transparent:true,opacity:.45,side:THREE.DoubleSide}));
 floor.rotation.x=-Math.PI/2;floor.position.y=-1.85;scene.add(floor);
 function paint(){
  for(const [id,meshes] of mapped){
   const color=colores[estado[id]?.color]||colores.sin_datos;
   for(const mesh of meshes)for(const material of Array.isArray(mesh.material)?mesh.material:[mesh.material]){
    if(material.color)material.color.set(id==='cuerpo'?0x426079:color);
    if(material.emissive){material.emissive.set(id===selected?color:0x000000);material.emissiveIntensity=id===selected ? 0.35 : 0;}
   }
  }
 }
 const ray=new THREE.Raycaster(),pointer=new THREE.Vector2();let down=null;
 renderer.domElement.addEventListener('pointerdown',event=>{down={x:event.clientX,y:event.clientY};});
 renderer.domElement.addEventListener('pointerup',event=>{
  if(!down||Math.hypot(event.clientX-down.x,event.clientY-down.y)>5){down=null;return;}down=null;
  const rect=renderer.domElement.getBoundingClientRect();pointer.set((event.clientX-rect.left)/rect.width*2-1,-(event.clientY-rect.top)/rect.height*2+1);
  ray.setFromCamera(pointer,camera);const hit=ray.intersectObject(root,true).find(h=>h.object.userData.organo);
  if(hit)onSelect(hit.object.userData.organo);
 });
 renderer.domElement.addEventListener('webglcontextlost',event=>{event.preventDefault();visible=false;onFailure('Se perdió el contexto 3D. El visor 2D sigue disponible.');});
 const observer=new ResizeObserver(()=>{const w=container.clientWidth,h=container.clientHeight;if(!w||!h)return;camera.aspect=w/h;camera.updateProjectionMatrix();renderer.setSize(w,h);});observer.observe(container);
 const reduced=matchMedia('(prefers-reduced-motion: reduce)');
 let last=performance.now(),phase=0;
 renderer.setAnimationLoop(()=>{
  const now=performance.now(),dt=Math.min((now-last)/1000,.1);last=now;
  if(!visible||document.hidden)return;
  const bpm=estado.corazon?.pulso;
  phase+=(bpm||0)/60*dt*Math.PI*2;
  const scale=bpm&&!reduced.matches?1+.07*Math.pow(Math.max(0,Math.sin(phase)),4):1;
  for(const heart of hearts)heart.object.scale.copy(heart.scale).multiplyScalar(scale);
  controls.update();renderer.render(scene,camera);
 });
 function dispose(group){group.traverse(o=>{if(o.isMesh){o.geometry.dispose();for(const m of Array.isArray(o.material)?o.material:[o.material]){for(const value of Object.values(m))if(value?.isTexture)value.dispose();m.dispose();}}});}
 async function cargarModelo(url){
  const gltf=await new GLTFLoader().loadAsync(url),next=gltf.scene;
  const box=new THREE.Box3().setFromObject(next),size=box.getSize(new THREE.Vector3());
  if(!Number.isFinite(size.y)||size.y<=0){dispose(next);throw new Error('El modelo no tiene geometría visible.');}
  let faltantes;
  try{faltantes=comprobarOrganos(next);}catch(error){dispose(next);throw error;}
  const wrapper=new THREE.Group();wrapper.add(next);next.position.sub(box.getCenter(new THREE.Vector3()));wrapper.scale.setScalar(3.5/Math.max(size.x,size.y,size.z));
  const old=root;scene.remove(old);root=wrapper;scene.add(root);index();paint();dispose(old);reset();
  return faltantes;
 }
 return {actualizar(data){estado=data;paint();},seleccionar(id){selected=id;paint();},reset,setVisible(value){visible=value;},cargarModelo};
}

