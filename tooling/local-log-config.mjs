import { clashProxyOrigin } from '/Users/matthewanderson/GolandProjects/clashking_schemas/cli/src/workspace.mjs';

export const localTrackingScripts = Object.freeze([
  'availability', 'trackedclans', 'trackedplayers', 'capital', 'discord-delivery',
  'giveaways',
]);

export function localProxyOrigin(workspace) {
  return clashProxyOrigin(workspace);
}
