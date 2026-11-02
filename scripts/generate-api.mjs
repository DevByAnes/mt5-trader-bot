import {execFileSync} from 'node:child_process';
for(const [schema,output] of [
 ['schema/openapi.yaml','src/shared/api/generated.ts'],
 ['schema/session.openapi.yaml','src/shared/api/session-generated.ts'],
 ['schema/settings.v2.openapi.yaml','src/shared/api/settings-generated.ts'],
]) execFileSync(process.execPath,['node_modules/openapi-typescript/bin/cli.js',schema,'-o',output],{stdio:'inherit'});
