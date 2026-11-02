import fs from 'node:fs';
import { execFileSync } from 'node:child_process';
import Ajv from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
const path='src/shared/api/generated.ts';const old=fs.readFileSync(path,'utf8');
const bin='node_modules/openapi-typescript/bin/cli.js';
execFileSync(process.execPath,[bin,'schema/openapi.yaml','-o',path],{stdio:'pipe'});
if(fs.readFileSync(path,'utf8')!==old){fs.writeFileSync(path,old);throw Error('API types drifted. Run pnpm api:generate and review the diff.');}
const spec=JSON.parse(fs.readFileSync('schema/openapi.yaml','utf8'));
const settings=JSON.parse(fs.readFileSync('schema/settings.schema.json','utf8'));
for(const [key,meta] of Object.entries(settings.properties)){
 const field=spec.components.schemas.SettingsDraft.properties[key];
 if(!field||field.type!==meta.type||meta.type==='string'&&JSON.stringify(field.enum??null)!==JSON.stringify(meta.enum??null)||field.minimum!==meta.minimum||field.maximum!==meta.maximum||field.multipleOf!==meta.multipleOf)throw Error('Settings schema drift: '+key);
 for(const required of ['key','type','min','max','step','default','enum','group','label_i18n','help_i18n','risk_level','apply','risk_direction','mt5_only'])if(!(required in meta))throw Error(key+' missing '+required);
}
const ajv=new Ajv({strict:false,multipleOfPrecision:8});addFormats(ajv);ajv.addSchema({...spec,$id:'openapi.yaml'});
const validateSettings=ajv.compile(settings);if(!validateSettings(JSON.parse(fs.readFileSync('fixtures/SettingsData.json','utf8')).data.values))throw Error(ajv.errorsText(validateSettings.errors));
for(const f of fs.readdirSync('fixtures')){const name=f.replace('.json','');const schema={$ref:`openapi.yaml#/components/schemas/${name}Envelope`};const validate=ajv.compile(schema);if(!validate(JSON.parse(fs.readFileSync('fixtures/'+f,'utf8'))))throw Error(f+': '+ajv.errorsText(validate.errors));}
const events=JSON.parse(fs.readFileSync('schema/events.json','utf8'));delete events.$id;const validateEvent=ajv.compile(events);
const payloads={ea_state:'EaState',position:'Positions',signal:'Signals',risk_mode:'DailyRisk',log:'Logs',command_ack:'Ack',config_ack:'Ack',heartbeat:'Status'};
for(const [type,name] of Object.entries(payloads)){let payload=JSON.parse(fs.readFileSync(`fixtures/${name}.json`,'utf8')).data;if(type==='signal'||type==='log')payload=payload.items[0];if(!validateEvent({type,seq:1,server_time_utc:'2026-11-02T10:00:00Z',payload}))throw Error(ajv.errorsText(validateEvent.errors));}
console.log('Generated API types, response fixtures and all eight events match contract 1.0.0.');
