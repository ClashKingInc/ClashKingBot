import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
import { basename, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

// Use actual compiled WASM/data modules, just as Wrangler does. Substituting a
// mock renderer here would hide Worker-only failures and invalid PNG output.
export async function bundleWorker() {
  const root=fileURLToPath(new URL('../../',import.meta.url));
  const require=createRequire(new URL('../../worker/package.json',import.meta.url));
  const {build}=require('esbuild'),assets=new Map();
  const result=await build({entryPoints:[resolve(root,'worker/src/index.ts')],bundle:true,write:false,format:'esm',platform:'browser',target:'es2022',plugins:[{
    name:'worker-asset-modules',setup(build){build.onResolve({filter:/\.(wasm|ttf|png)$/},args=>{
      const source=args.path.startsWith('@')?require.resolve(args.path):resolve(args.resolveDir,args.path);
      const name=`poster-${basename(source)}`;
      if(!assets.has(name))assets.set(name,{type:source.endsWith('.wasm')?'CompiledWasm':'Data',path:`/${name}`,contents:readFileSync(source)});
      return {path:`./${name}`,external:true};
    });},
  }]});
  return {modulesRoot:'/',modules:[{type:'ESModule',path:'/worker.mjs',contents:result.outputFiles[0].text},...assets.values()]};
}
