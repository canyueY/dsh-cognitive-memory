"""Regenerate distributable manifest/schema after changing the runtime source."""
import json
import sys
from pathlib import Path

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/"src"))
from cognitive_memory.onboarding import manifest
from cognitive_memory.onboarding_contract import BootstrapManifest

payload=BootstrapManifest.model_validate(manifest()).model_dump()
for folder in (root/"manifest",root/"src/cognitive_memory/resources"):
    folder.mkdir(parents=True,exist_ok=True)
    (folder/"mnemosyne.manifest.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (folder/"schema.json").write_text(json.dumps(BootstrapManifest.model_json_schema(),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("Exported and validated bootstrap manifest + JSON Schema.")
