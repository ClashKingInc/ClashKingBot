// Keep command fixtures protocol-valid while each scenario owns its meaningful
// game values. Supply only missing required fields, never optional metadata.
import {parse} from '@clashking/clash-contract';
import spec from '@clashking/clash-contract/openapi.json' with {type:'json'};
const resolve=s=>s?.$ref?resolve(spec.components.schemas[s.$ref.split('/').at(-1)]):s??{};
function complete(schema,value){
 schema=resolve(schema);
 if(schema.anyOf||schema.oneOf){
  const choices=(schema.anyOf??schema.oneOf).map(resolve);
  const matching=choices.find(s=>s.properties?.state&&(s.properties.state.const===value?.state||s.properties.state.enum?.includes(value?.state)))??choices.find(s=>s.type===(value===null?'null':Array.isArray(value)?'array':typeof value))??choices[0];
  return complete(matching,value);
 }
 if(schema.allOf)return schema.allOf.reduce((v,s)=>complete({...schema,allOf:undefined,...resolve(s)},v),value);
 if(value===undefined){if(schema.type==='array')value=[];else if(schema.type==='object'||schema.properties)value={};else if(schema.type==='boolean')return false;else if(schema.type==='number'||schema.type==='integer')return Math.max(0,schema.minimum??(schema.exclusiveMinimum!==undefined?schema.exclusiveMinimum+1:0));else return schema.const??schema.enum?.[0]??'';}
 if(Array.isArray(value))return value.map(item=>complete(schema.items,item));
 if(value&&typeof value==='object'){
  const result={...value};for(const [key,s]of Object.entries(schema.properties??{}))if(key in result||schema.required?.includes(key))result[key]=complete(s,result[key]);return result;
 }
 return value;
}
const routes=Object.entries(spec.paths).map(([path,methods])=>({match:new RegExp('^'+path.replace(/\{[^}]+\}/g,'[^/]+')+'$'),methods}));
export function validClashFixture(path,method,body){
 const schema=routes.find(r=>r.match.test(path.replace(/^\/v1/,'')))?.methods[method.toLowerCase()]?.responses?.['200']?.content?.['application/json']?.schema;
 const completed=schema?complete(schema,body):body;
 if(schema?.$ref){const name=schema.$ref.split('/').at(-1);try{parse(name,completed);}catch(error){console.error('Invalid synthetic Clash fixture',path,String(error));}}
 return completed;
}
