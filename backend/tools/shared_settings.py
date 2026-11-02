"""Generate a native input table and TS schema wrapper from the full input catalog."""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def outputs() -> dict[Path, str]:
    schema = json.loads((ROOT / "schema/settings.v2.schema.json").read_text(encoding="utf-8"))
    properties = schema["properties"]
    wrapper = {
        "openapi": "3.1.0",
        "info": {"title": "Aurum shared EA inputs", "version": "2.0.0"},
        "paths": {},
        "components": {"schemas": {"EASettings": schema}},
    }
    lines = [
        "// Generated from schema/settings.v2.schema.json. Do not edit.",
        "#ifndef AURUM_GENERATED_INPUTS_MQH",
        "#define AURUM_GENERATED_INPUTS_MQH",
        "",
    ]
    group = ""
    validation = []
    serialization = []
    for name, meta in properties.items():
        if meta["group"] != group:
            group = meta["group"]
            lines.append('input group "' + group + '"')
        default = meta["default"]
        kind = meta["type"]
        choices = meta.get("enum")
        if choices:
            typename = "ENUM_AU_" + name
            members = [typename + "_" + value for value in choices]
            lines.append("enum " + typename + " { " + ", ".join(members) + " };")
            lines.append(f"input {typename} {name}={members[choices.index(default)]};")
            validation.append(
                f"   if((int){name}<0 || (int){name}>={len(choices)}) "
                f'{{reason="{name}: invalid enum"; return false;}}'
            )
            expression = "(" + " : ".join(
                f'{name}=={member} ? "\\"{choice}\\""'
                for member, choice in zip(members[:-1], choices[:-1], strict=True)
            )
            expression += ' : "\\"' + choices[-1] + '\\"")'
        else:
            native = {"boolean": "bool", "integer": "int", "number": "double", "string": "string"}[
                kind
            ]
            value = json.dumps(default, ensure_ascii=True)
            lines.append(f"input {native} {name}={value};")
            expression = (
                f"AurumJsonQuote({name})"
                if kind == "string"
                else (
                    f'({name}?"true":"false")'
                    if kind == "boolean"
                    else f"IntegerToString({name})"
                    if kind == "integer"
                    else f"DoubleToString({name},8)"
                )
            )
            if kind in {"number", "integer"}:
                low, high, step = meta["minimum"], meta["maximum"], meta["multipleOf"]
                validation.append(
                    f"   if(!MathIsValidNumber((double){name}) || {name}<{low} || "
                    f"{name}>{high} || MathAbs({name}/{float(step)}-"
                    f"MathRound({name}/{float(step)}))>1e-7) "
                    f'{{reason="{name}: range or step";return false;}}'
                )
            elif kind == "string":
                validation.append(
                    f"   if(StringLen({name})<1 || StringLen({name})>128) "
                    f'{{reason="{name}: length";return false;}}'
                )
        serialization.append(f'   result+="\\"{name}\\":"+{expression}+",";')
    lines += [
        "",
        "string AurumJsonQuote(string value)",
        "{",
        r'   string result="\"";',
        '   for(int i=0;i<StringLen(value);i++)',
        '   {',
        '      ushort code=StringGetCharacter(value,i);',
        r'      if(code==34) result+="\\\"";',
        r'      else if(code==92) result+="\\\\";',
        r'      else if(code<32) result+=StringFormat("\\u%04x",(uint)code);',
        '      else result+=ShortToString(code);',
        '   }',
        r'   return result+"\"";',
        "}",
        "",
        "bool AurumValidateInputs(string &reason)",
        "{",
        *validation,
        "   if(InpRetestMinBars>InpRetestMaxBars || InpMinStopAtr>InpMaxStopAtr) "
        '{reason="Inconsistent dependent ranges";return false;}',
        '   reason="";return true;',
        "}",
        "",
        "string AurumSettingsV2Json()",
        "{",
        '   string result="{";',
        *serialization,
        '   return StringSubstr(result,0,StringLen(result)-1)+"}";',
        "}",
        "#endif",
        "",
    ]
    return {
        ROOT / "schema/settings.v2.openapi.yaml": json.dumps(wrapper, indent=2, ensure_ascii=False)
        + "\n",
        ROOT / "mql5/Include/Aurum/GeneratedInputs.mqh": "\n".join(lines),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for path, content in outputs().items():
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                raise SystemExit("Shared input drift: " + path.name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
    print("Shared EA input outputs match schema" if args.check else "Generated shared EA inputs")


if __name__ == "__main__":
    main()
