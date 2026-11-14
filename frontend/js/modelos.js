import {organos} from './config.js';
// Solo cuentan nombres asociados a mallas, no grupos vacíos.
export function comprobarOrganos(root){
 const names=new Set();
 root.traverse(object=>{
  if(!object.isMesh)return;
  let node=object;
  while(node){if(Object.hasOwn(organos,node.name)){names.add(node.name);break;}node=node.parent;}
 });
 if(!names.size)throw new Error('El modelo no contiene mallas con nombres de órganos acordados.');
 return Object.keys(organos).filter(id=>!names.has(id));
}

