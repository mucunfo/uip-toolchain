# Reporte de regras da toolchain e impacto do `--apply-contextual`

Data da auditoria: 2026-06-07.

Fonte efetiva: `rules.yaml` carregado por `uip_engine.loader.load_rules`.

## Resumo executivo

O inventario efetivo validado pela CLI tem **303 regras**.

| Classe | Qtde | Como a toolchain trata hoje |
|---|---:|---|
| `deterministic` | 125 | Aplica no `ccs-uip <project_path>` via fixer mecanico e gates de rollback. |
| `contextual` | 171 | Nao bloqueia deploy por padrao; vira `PASS-WITH-NOTES`. So e aplicada em `ccs-uip <project_path> --apply-contextual` se o finding trouxer `fix_mechanical`. |
| `structural` | 7 | Nao e aplicada pelo `--apply-contextual`; fica para humano/IA com revisao. |

Conclusao direta: conectar uma LLM ao `--apply-contextual` nao substitui o motor mecanico. Ela adiciona uma nova camada para os findings contextuais que hoje nao geram patch. O caminho correto e: detector encontra finding, toolchain entrega regra + arquivo + trecho + instrucao, LLM gera patch pequeno, engine reaplica review/analyzer/pack gate e aceita ou rejeita.

## O que e mecanico

Mecanico e tudo que tem saida unica correta ou fixer deterministico: XML/XAML invalido, pins NuGet, referencias faltantes, casing conhecido, rename canonico, defaults conhecidos, limpeza de artefato do migrator, ajustes de `project.json` e readiness para pack oficial.

Impacto operacional:

- Ja deve rodar no primeiro `ccs-uip <project_path>`.
- Nao precisa LLM.
- Se uma regra mecanica falha, o problema deve ser corrigido no fixer/detector, nao por prompt.
- Os gates existentes continuam obrigatorios: XML well-formedness, VB ref/declaration, analyzer, restore, pack e activity compile.

## O que e contextual

Contextual e tudo que depende de significado: mensagem de log, escolha de valor, arquitetura do workflow, boundary entre navegacao/acao, escopo de credencial, retry correto, teste que precisa mockar sistema externo, decomposicao de workflow, decisao sobre API/OCR/PDF/Mail/SharePoint.

Estado atual apos hardening:

- 171 regras sao contextuais.
- 171/171 regras contextuais tem `fix.prose` explicito.
- 303/303 regras efetivas tem `fix.prose` explicito.
- Em YAML, apenas `N-5` declara `fix.mechanical` mesmo sendo contextual; outros casos so aplicam se o detector emitir `fix_mechanical` por finding.

Isso significa que `--apply-contextual` hoje e principalmente um opt-in para fixers contextuais ja preparados. Para virar loop LLM end-to-end, a LLM deve consumir o finding e o `fix.prose` da regra, gerar diff pequeno, e deixar a toolchain validar/aplicar.

## Regras estruturais

As 7 regras estruturais reorganizam workflow/projeto e nao devem entrar no mesmo fluxo automatico de patch local:

| Regra | Motivo |
|---|---|
| `CFG-BINDING-REDIRECT-IGNORED` | exige decisao de dependencia/config em .NET 6+. |
| `D-TRANSITIVE-CONFLICT` | exige resolver conflito transitive/downgrade. |
| `N-10` | exige reposicionar ou reescrever log antecipatorio. |
| `S-18` | exige preencher body de engine OCR/CV. |
| `S-19` | exige reconciliar publish/ignoredFiles/invokes produtivos. |
| `U-5` | exige consolidar aliases de variaveis. |
| `U-6` | exige hoisting de variavel para escopo correto. |

Recomendacao: manter fora de `--apply-contextual`; no maximo gerar plano e patch draft com aprovacao humana.

## Inventario por familia

| Familia | Deterministic | Contextual | Structural |
|---|---:|---:|---:|
| A | 2 | 21 | 0 |
| API | 1 | 5 | 0 |
| CCS | 1 | 0 | 0 |
| CFG | 0 | 0 | 1 |
| CRY | 1 | 5 | 0 |
| CX | 0 | 5 | 0 |
| D | 20 | 0 | 1 |
| DB | 2 | 5 | 0 |
| DULS | 0 | 6 | 0 |
| E | 0 | 2 | 0 |
| ENV | 4 | 0 | 0 |
| EXC | 0 | 7 | 0 |
| HY | 4 | 2 | 0 |
| I | 0 | 4 | 0 |
| IOCR | 2 | 6 | 0 |
| J | 9 | 3 | 0 |
| M | 4 | 4 | 0 |
| MAIL | 0 | 6 | 0 |
| N | 11 | 7 | 1 |
| O365 | 0 | 6 | 0 |
| OCR | 1 | 6 | 0 |
| P | 0 | 3 | 0 |
| PDF | 0 | 10 | 0 |
| RT | 1 | 1 | 0 |
| S | 17 | 4 | 2 |
| SP | 2 | 6 | 0 |
| SYS | 0 | 7 | 0 |
| T | 0 | 7 | 0 |
| TCC | 0 | 3 | 0 |
| TEST | 1 | 5 | 0 |
| U | 2 | 2 | 2 |
| UI | 1 | 6 | 0 |
| V | 3 | 1 | 0 |
| W | 34 | 10 | 0 |
| X | 2 | 0 | 0 |
| XML | 0 | 6 | 0 |

Categorias efetivas:

| Categoria | Qtde |
|---|---:|
| `architectural` | 150 |
| `breaking` | 122 |
| `testing` | 16 |
| `metadata` | 8 |
| `agent_behavior` | 7 |

## Contrato recomendado para LLM

Cada finding contextual deve virar uma tarefa isolada. Nao passar catalogo inteiro no prompt base.

Payload minimo por chamada:

```json
{
  "rule_id": "N-16",
  "severity": "WARN",
  "category": "architectural",
  "file": "Process/Example.xaml",
  "line": 120,
  "title": "LogMessage sem rastreabilidade semantica",
  "instruction": "Reescreva a mensagem do LogMessage para dizer objetivamente o que a activity anterior faz, usando dados do contexto quando existirem.",
  "allowed_files": ["Process/Example.xaml"],
  "forbidden": ["alterar regra de negocio", "inventar selector", "editar Framework/SetTransactionStatus.xaml"],
  "output_schema": "unified_diff"
}
```

Regras de execucao:

1. Um finding por chamada.
2. Uma pequena alteracao por resposta.
3. LLM retorna diff, nunca escreve direto.
4. Toolchain aplica patch em sandbox/snapshot.
5. Reexecuta `review` e gates.
6. Se o mesmo finding permanece 2 vezes, marca `PENDING_REVIEW` e para.
7. Nunca usar LLM para regras `deterministic`.
8. Nunca aplicar `structural` sem aprovacao humana.

## Instrucao padrao para cada rule contextual

Cada regra contextual deve usar `fix.prose` como instrucao primaria. Nao existe mais fallback aceitavel para regra sem prose: `python -m uip_engine.cli validate` agora falha se qualquer regra efetiva estiver sem `fix.prose`.

Para modelos frontier, o prompt por finding deve incluir:

- `rule_id`, `severity`, `category`, `title`.
- `fix.prose` completo.
- `description` e `examples` como contexto secundario.
- Trecho minimo do arquivo e referencias chamadas pelo finding.
- Lista fechada de arquivos editaveis.
- Saida obrigatoria em `unified_diff` ou JSON com diff.

## Modelos frontier

Nao usar runtime local neste fluxo. O runtime assumido e modelo de ponta, como Claude Opus ou Codex.

Mesmo com modelo frontier, a LLM continua sendo **patch proposer controlado**, nao executor livre. O valor do modelo de ponta entra em interpretacao semantica, mensagens de log, refatoracao pequena e julgamento de escopo; a autoridade continua sendo `rules.yaml` + gates da toolchain.

## Decisao recomendada

Antes de implementar `ccs-uip <project_path> --apply-contextual` com LLM:

1. Manter `fix.prose` obrigatorio para 100% das regras efetivas.
2. Criar adaptador frontier-model agnostico com schema fixo de diff.
3. Aplicar somente um finding por chamada.
4. Permitir escrita apenas nos arquivos apontados pelo finding.
5. Rodar gates depois de cada patch ou lote pequeno.
6. Comecar com allowlist: `N-16`, `N-9`, `N-15`, `E-1`, `E-2`, `TCC-*`, `CX-*`.
7. Manter denylist inicial para credenciais, selectors, Framework, publish/ignoredFiles, dependencia NuGet e structural.

Arquivos derivados gerados nesta auditoria:

- `.tmp/llm-rules-current.md`: 178 regras LLM-dependent (`contextual` + `structural`).
- `.tmp/all-rules-current.md`: 303 regras efetivas.
- `.tmp/contextual-rule-instructions-current.md`: 171 instrucoes contextuais efetivas.
