# Lookup Patterns

Use toolchain queries instead of loading large corpora into prompt context.

Rules:

```powershell
rg -n "id: N-3B|N-3B" rules.yaml
python -m uip_engine.cli list --by-category
```

Findings:

```powershell
python -m uip_engine.cli review <project> --format json
python -m uip_engine.cli review <project> --format text
```

Activity schema and examples:

```powershell
python tools/activities_meta/lookup.py --activity WriteRange --json
python tools/xaml_example.py --activity LogMessage
```

Large XAML navigation:

```powershell
python tools/xaml_summary.py <file.xaml>
python tools/xaml_find.py <file.xaml> --activity "<display-or-type>"
python tools/xaml_find.py <file.xaml> --line 120 --context 20
```
