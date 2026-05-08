# activities_meta

Offline build tools que extraem schema de atividades dos packages NuGet UiPath
instalados localmente e geram artefatos consumidos pela engine.

## Por que existe

Engine de regras precisa de **verdade autoritativa** sobre cada activity:
quais args existem, quais são required, OverloadGroups, tipos. Regex e heurística
não bastam para regras M-* (ver `rules.yaml`).

Schema é extraído via **Mono.Cecil reflection** sobre as DLLs em
`~/.nuget/packages/uipath.*` — independente de versão Studio (netfx/net6/net8),
sem requerer .NET SDK instalado.

## Quando regenerar

- Adicionou package novo ao Studio.
- Atualizou versão de package existente.
- Suspeita de divergência entre schema commitado e Studio real.
- Onboarding em máquina nova.

Não é tarefa de CI nem hook — depende do cache nuget local.

## Como rodar

Pré-requisitos:
- Windows + PowerShell 5.1+ (ou pwsh).
- UiPath Studio instalado (qualquer versão 2023+; script auto-detecta).
- Packages alvo já abertos pelo menos uma vez no Studio (popula `~/.nuget/packages/`).

```powershell
cd .uipath-rules\scripts\activities_meta

# 1. extrai metadata bruta de todos packages uipath.* instalados
.\batch-extract.ps1

# 2. compacta para LLM-ready + markdown human-readable
.\build-schema.ps1
```

Saídas:
- `.uipath-rules/.tmp/activities_dump/` — raw dumps por DLL + `activities-all.json` (descartável).
- `.uipath-rules/assets/activities/activities-compact.json` — schema compacto (commit, ~600 KB).
- `.uipath-rules/assets/activities/INDEX.md` — índice human-readable.
- `.uipath-rules/assets/activities/uipath.<package>.md` — referência por package.

## Override de paths

Todos scripts aceitam params:

```powershell
.\batch-extract.ps1 -StudioDir "D:\Custom\Studio" -NugetCache "D:\nuget"
.\extract-cecil.ps1 -ActivityDll "D:\caminho\X.dll" -OutJson "out.json"
.\build-schema.ps1 -Source "alt.json" -OutDir "alt-out"
```

## Estrutura

| Script | Função |
|---|---|
| `extract-cecil.ps1` | Single-DLL extractor (núcleo). Cecil reflection, JSON output. |
| `batch-extract.ps1` | Sweep `~/.nuget/packages/uipath.*`, escolhe TFM preferido, chama extract-cecil em loop, consolida. |
| `build-schema.ps1` | Lê dump consolidado, gera `activities-compact.json` + markdowns. |

## Integração com engine

`scripts/rule_engine/heuristics/activity_meta.py` carrega
`assets/activities/activities-compact.json` em singleton, indexa por FQN +
`(xmlns, local_name)`, expõe checks consumidos pelo detector
`activity_signature` (regras M-*).

Arquivo regenerado é commit-ready (filesystem; OneDrive sync compatível).
Tamanho ~600 KB.

## Troubleshooting

- "Mono.Cecil.dll not found" → Studio não instalado ou dir errado. Passa
  `-StudioDir` explícito.
- "0 activities" para package conhecido → DLL é stub/runtime sem activities;
  ignorar (loop tenta múltiplas DLLs por package).
- "Já foi adicionado um item com a mesma chave" → bug de serialização PS 5.1
  com hashtables case-sensitive. Já fix no extractor; reportar se recorrer.

## Versionamento

Schema dump não é fonte primária — é gerado. Mudança em `activities-compact.json`
sem commit equivalente em scripts/packages = stale. Documentar versão Studio +
data no commit message ao regenerar.
