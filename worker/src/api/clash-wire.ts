import { Api } from '@clashking/clash-contract/http';
import { ClientErrorResponse } from '@clashking/clash-contract/effect';
import { Schema } from 'effect';

// Derive the bot's validation inventory from the published HTTP contract. A new
// proxy command cannot silently introduce a second, unchecked response model.
export class ClashContractError extends Error {
  constructor(readonly operation:string,readonly kind:'missing_contract'|'error_envelope'|'invalid_body') {
    super('Clash response contract failure for '+operation);this.name='ClashContractError';
  }
}
const routes = Object.values(Api.groups).flatMap(group => Object.values(group.endpoints).map(endpoint => ({
  endpoint,
  match: new RegExp('^'+endpoint.path.split('/').map((part:string) => part.startsWith(':') ? '[^/]+' : part.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')).join('/')+'$'),
})));
export function validateClashBody(path:string,method:string,body:unknown):unknown {
  const wirePath=path.replace(/^\/v2\/bot\/clash/,'');
  const route=routes.find(row=>row.endpoint.method===method&&row.match.test(wirePath));
  if(!route)throw new ClashContractError(method+' Clash proxy','missing_contract');
  if(Schema.is(ClientErrorResponse)(body))throw new ClashContractError(route.endpoint.path,'error_envelope');
  // All published successful operations use the shared WithHeaders wrapper.
  const success=[...route.endpoint.success][0] as unknown as {schema:Schema.Codec<unknown>};
  if(!success?.schema)throw new ClashContractError(route.endpoint.path,'missing_contract');
  try{return Schema.decodeUnknownSync(success.schema)(body);}
  catch{throw new ClashContractError(route.endpoint.path,'invalid_body');}
}
